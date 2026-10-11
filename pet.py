import sys
import os
import re
import json
import math
import time
import random
import datetime
import psutil
import threading

from PyQt6.QtWidgets import (
    QApplication, QLabel, QWidget, QFrame, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QScrollArea, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, QThread, pyqtSignal
from PyQt6.QtGui import QMovie, QCursor, QTransform, QFont, QColor, QPen, QPainter

# ---------------- CONFIG ----------------
PET_SIZE = 90
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")

# --- screen context: what the user is doing (see categorize_window) ---
# coding / typing (pet plays with the keyboard)
# studying (pet cheers you on)
STUDY_APPS = {"notion.exe", "onenote.exe", "sumatrapdf.exe", "epubreader.exe",
              "adobeacrobat.exe", "wps.exe", "foxitpdfreader.exe", "anki.exe", "chrome.exe", "firefox.exe", "brave.exe", "edge.exe", "msedge.exe"}
STUDY_TITLE_KEYWORDS = (
    "lecture", "course", "tutorial", "lesson", "udemy", "coursera",
    "khan academy", "dbms", "sql", "aptitude", "reasoning", "quant",
    "current affairs", "english grammar", "cgl", "sebi", "upsc", "ncert",
    "geeksforgeeks", "leetcode", "stackoverflow", "stack overflow",
    "class", "practice", "mock test", "syllabus", "exam",
    "operating system", "computer network", "networking", "data structure",
    "algorithms", "dsa", "programming", "python", "java", "c++", "react",
    "flutter", "dart", "docker", "sql joins", "gate")
# watching a movie / show (pet joins and eats popcorn)
MOVIE_APPS = {"vlc.exe", "mpc-hc.exe", "mpv.exe", "potplayer.exe",
              "potplayermini64.exe", "wmplayer.exe", "plex.exe", "steam.exe"}
MOVIE_TITLE_SIGNALS = (".mp4", ".mkv", ".avi", ".mov", ".webm", "netflix",
                       "prime video", "hotstar", "disney+", "hulu", "youtube")
# distractions (pet gets warning -> angry)
DISTRACTION_APPS = {"whatsapp.exe", "spotify.exe", "discord.exe",
                    "telegram.exe", "instagram.exe", "twitter.exe",
                    "facebook.exe", "tiktok.exe", "snapchat.exe"}
DISTRACTION_TITLE_SIGNALS = ("whatsapp", "instagram", "facebook", "twitter",
                             "x.com", "reddit", "discord", "tiktok", "snapchat")

# --- pet "needs": energy that drains and needs sleep to refill ---
ENERGY_START       = 80
ENERGY_DRAIN_IDLE  = 0.10   # per second, just sitting
ENERGY_DRAIN_MOVE  = 0.30   # per second, walking / running
ENERGY_DRAIN_PLAY  = 0.45   # per second, playing with the keyboard
ENERGY_REGEN_SLEEP = 1.20   # per second while sleeping
SLEEPY_AT          = 30     # energy <= this -> gets sleepy and sleeps
SLEEP_UNTIL        = 90     # wakes once energy is restored to this

# --- idle / attention: no mouse or keyboard for a while -> pet wants you ---
IDLE_SEEK_AFTER_S  = 120    # 2 min  -> pet comes over to you
IDLE_GRUMPY_S      = 240    # 4 min  -> grumpy (warning gif)
IDLE_ANGRY_S       = 360    # 6 min  -> angry
AGGRO_TYPING_S     = 600    # 10 min typing -> keyboard play gets aggressive

# --- behavior cooldowns + speech bubbles ---
MOVIE_MOOD_S       = 6      # seconds eating popcorn in a row
MOVIE_COOLDOWN_S   = 40     # before the next popcorn snack
TYPING_TYPE_S      = 25     # seconds the pet types in a row...
TYPING_PAUSE_S     = 5      # ...then a short paw-stretch pause (while you keep typing)
TYPING_IDLE_S      = 10     # treated as "typing" for this long after your last key
STUDY_CHEER_S      = 1200   # every 20 min of study -> an encouragement bubble

# --- the pet's own keyboard (it types along when you do) ---
KB_WIDTH  = 210             # px
KB_HEIGHT = 78              # px

POPCORN_LINES = ("this looks good! 🍿", "I'm ready for the snacks!",
                 "who's the bad guy? 👀", "*munch munch*")
PLAY_LINES = ("whatcha typing? 🐾", "let me help! *paw*", "keyboard! keyboard!",
              "*paws at your keys*", "can I press a key too?")
AGGRO_PLAY_LINES = ("ok THAT'S enough typing!", "*swats the keyboard*",
                    "pay attention to me!! 😼")
ENCOURAGE_LINES = ("You're on a streak! 📈", "Nice going! 💪",
                   "Keep it up, you've got this!", "One more, you're doing great!",
                   "Look at you go! 🌟")
STUDY_START_LINES = ("Ooh, study time! Let's go! 📚", "I'm your study buddy! 🙌",
                     "Nice, revising is the way! 💪", "Let's do this together! ✨")
DISTRACTION_LINES = ("Hey! That's not study time 😠", "Shouldn't you be revising?",
                     "That app is a trap! 🙀")

# animation states -> gif files (run make_gifs.py to create placeholders)
GIF_MAP = {
    "idle":    "CAT_idle_1.gif",
    "walk":    "CAT_walk_1.gif",
    "run":     "CAT_run_1.gif",
    "rest":    "CAT_asleep_1.gif",
    "cheer":   "CAT_win_cheer_1.gif",
    "warning": "warning.gif",
    "angry":   "CAT_dead_1.gif",
    "popcorn": "popcorn.gif",
    "sleep":   "CAT_asleep_1.gif",
    "play":    "CAT_ducking_move_1.gif",
    "happy":   "CAT_ducking_idle_1.gif",
}

STUDY_TARGET_MS = 2 * 60 * 60 * 1000   # cheer after 2 hours of focus
WARN_TIMEOUT_MS = 2 * 60 * 1000        # angry after 2 min ignoring a distraction

# --- "living cat" movement tuning ---
CHASE_RADIUS    = 260   # px: cursor this close -> chase it
CHASE_GAP       = 60    # px: how close it gets to the cursor
CHASE_SPEED     = 9     # px/frame chasing (fast/excited)
WANDER_SPEED    = 3     # px/frame strolling (slow/relaxed)
WANDER_CHANCE   = 0.25  # chance per decision to stroll somewhere
ATTENTION_TICKS = 15    # decisions of being ignored before it seeks you
DECIDE_MS       = 800   # behavior "brain" tick
MOVE_MS         = 33    # ~30 fps movement

# --- rest cycle: pet must NOT move continuously ---
ACTIVE_SECS = (30, 60)  # roam this many seconds...
REST_SECS   = (15, 20)  # ...then rest this many seconds

# --- Google Gemini AI (free tier) ---
GEMINI_MODEL = "gemini-3.6-flash"

# --- chat window + reminder toast look ---
CHAT_THEME          = "cozy"   # "cozy" | "dark" | "playful"
TOAST_AUTODISMISS_S = 8        # seconds a reminder toast stays up
TOAST_OPENS_CHAT    = False    # True -> a reminder also pops the chat window open


# ==================================================================
#  Config helpers (stores the Gemini API key locally)
# ==================================================================
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Could not save config:", e)


# ==================================================================
#  Active-window scanning (Windows) — gives the pet screen context
# ==================================================================
def active_window_title():
    try:
        import ctypes
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        n = u.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(h, buf, n + 1)
        return buf.value or ""
    except Exception:
        return ""


def active_window_info():
    """Return (title, process_name) of the foreground window."""
    title = active_window_title()
    proc = ""
    try:
        import ctypes
        u = ctypes.windll.user32
        h = u.GetForegroundWindow()
        pid = ctypes.c_ulong()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        proc = psutil.Process(pid.value).name()
    except Exception:
        pass
    return title, proc


def idle_seconds():
    """Seconds since the last keyboard/mouse input (Win32 GetLastInputInfo)."""
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        u = ctypes.windll.user32
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        if not u.GetLastInputInfo(ctypes.byref(lii)):
            return 0.0
        return (u.GetTickCount() - lii.dwTime) / 1000.0
    except Exception:
        return 0.0


# ==================================================================
#  Global keyboard hook — knows when you're typing in ANY app
# ==================================================================
KEYSTROKE_LAST = [0.0]              # time.monotonic() of the last key press
_KEYHOOK_TID = [0]                  # thread id of the hook's message loop
_KEYHOOK_PROC = [None]              # keeps the callback alive (GC safety)


def keyboard_typing_now():
    """True if a key was pressed within the last TYPING_IDLE_S seconds."""
    return time.monotonic() - KEYSTROKE_LAST[0] < TYPING_IDLE_S


def start_keyboard_hook():
    """Install a low-level keyboard hook in a background thread so the pet can
    tell when you type, no matter which app is focused. Non-intrusive: it only
    reads key-downs and forwards them on. Falls back silently on failure (the
    app-based TYPING_APPS detection still works as before)."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    # wintypes.WPARAM/LPARAM are 32-bit even on 64-bit Windows — use the
    # pointer-sized variants so the hook's wParam/lParam arrive intact.
    WPARAM = ctypes.c_size_t
    LPARAM = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, WPARAM, LPARAM)

    @HOOKPROC
    def proc(nCode, wParam, lParam):
        if nCode >= 0 and wParam == WM_KEYDOWN:
            KEYSTROKE_LAST[0] = time.monotonic()
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    # explicit 64-bit-safe signatures so no pointer is truncated or overflows
    user32.CallNextHookEx.argtypes = [
        wintypes.HHOOK, ctypes.c_int, WPARAM, LPARAM]
    user32.CallNextHookEx.restype = ctypes.c_long
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, ctypes.c_ulong]
    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG), wintypes.HWND,
        wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int

    _KEYHOOK_PROC[0] = proc         # must outlive this function
    installed = [False]

    def _pump():
        # install + pump in the SAME thread (required for low-level hooks).
        # hmod=NULL works for WH_KEYBOARD_LL and avoids ERROR_MOD_NOT_FOUND.
        hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, proc, None, 0)
        if not hhook:
            return
        installed[0] = True
        _KEYHOOK_TID[0] = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(hhook)

    threading.Thread(target=_pump, daemon=True).start()
    time.sleep(0.05)                # let the thread install before we report
    return installed[0]


def stop_keyboard_hook():
    """Politely ask the hook thread to exit (posts WM_QUIT to its loop)."""
    try:
        tid = _KEYHOOK_TID[0]
        if tid:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(tid, 0x0012, 0, 0)
    except Exception:
        pass


def categorize_window(title, proc):
    """What is the user doing?  -> 'typing' | 'movie' | 'study' | 'distraction' | 'other'
    Order matters: typing wins, then any movie signal (a video app, or a video
    page open in a browser), then study apps/keywords, then distractions."""
    tl = (title or "").lower()
    pn = (proc or "").lower()
    if pn in TYPING_APPS:
        return "typing"
    if pn in MOVIE_APPS or any(k in tl for k in MOVIE_TITLE_SIGNALS):
        return "movie"
    if any(k in tl for k in STUDY_TITLE_KEYWORDS) or pn in STUDY_APPS:
        return "study"
    if pn in DISTRACTION_APPS or any(k in tl for k in DISTRACTION_TITLE_SIGNALS):
        return "distraction"
    return "other"


# ==================================================================
#  Gemini AI worker (runs the API call off the UI thread)
# ==================================================================
class AIWorker(QThread):
    reply = pyqtSignal(str)

    def __init__(self, api_key, system, messages):
        super().__init__()
        self.api_key = api_key
        self.system = system
        self.messages = messages

    def run(self):
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            self.reply.emit(
                "(!) Gemini SDK not installed.\n"
                "Run:  pip install google-genai"
            )
            return

        client = genai.Client(api_key=self.api_key)
        # full conversation history in the new SDK's format
        contents = []
        for m in self.messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        cfg = types.GenerateContentConfig(
            system_instruction=self.system,
            max_output_tokens=1024,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )

        # try once; on a rate-limit (429) wait the suggested delay and retry once
        for attempt in range(2):
            try:
                resp = client.models.generate_content(
                    model=GEMINI_MODEL, contents=contents, config=cfg,
                )
                text = (getattr(resp, "text", None) or "").strip()
                self.reply.emit(text or "(no reply)")
                return
            except Exception as e:
                msg = str(e)
                is_rate = "429" in msg or "RESOURCE_EXHAUSTED" in msg
                if is_rate and attempt == 0:
                    delay = self._retry_delay(msg)
                    self.reply.emit(
                        f"(busy) Free-tier limit hit — resting {delay}s, "
                        "then I'll try again automatically...")
                    self.sleep(delay)
                    continue
                if is_rate:
                    self.reply.emit(
                        "(!) Still rate-limited. The free tier allows only a "
                        "few messages per minute — give it a minute and retry.")
                else:
                    self.reply.emit(f"(!) Gemini error: {msg}")
                return

    @staticmethod
    def _retry_delay(msg):
        m = re.search(r"retryDelay'?:?\s*'?(\d+)", msg)
        return min(int(m.group(1)), 60) if m else 40


# ==================================================================
#  Chat window (type to Gemini / set reminders)
# ==================================================================
CHAT_THEMES = {
    # warm cream/peach pastel
    "cozy": {
        "root_bg": "#FFF6E9", "root_border": "#F0DFC4",
        "title_a": "#FFE7C2", "title_b": "#FFD9A0", "title_fg": "#6B4A2F",
        "pet_bg": "#FFFFFF", "pet_fg": "#4E3B2E", "pet_border": "#F2E2C8",
        "you_bg": "#FFA94D", "you_fg": "#FFFFFF",
        "sys_fg": "#B08968", "input_bg": "#FFFFFF", "input_fg": "#4E3B2E",
        "placeholder": "#B9A48B", "accent": "#FFA94D",
        "online": "#4CAF50", "scroll": "#E3CDAB", "avatar_bg": "#FFE7C2",
    },
    # dark sleek
    "dark": {
        "root_bg": "#1E1F2B", "root_border": "#3A3B4A",
        "title_a": "#2A2B3A", "title_b": "#232432", "title_fg": "#EDEFF7",
        "pet_bg": "#2E3040", "pet_fg": "#E8EAF2", "pet_border": "#44465A",
        "you_bg": "#7C5CFF", "you_fg": "#FFFFFF",
        "sys_fg": "#7C7F96", "input_bg": "#2E3040", "input_fg": "#E8EAF2",
        "placeholder": "#7C7F96", "accent": "#7C5CFF",
        "online": "#4ADE80", "scroll": "#4A4C60", "avatar_bg": "#3A3B4A",
    },
    # bright & playful
    "playful": {
        "root_bg": "#FFF7E6", "root_border": "#FFD9A0",
        "title_a": "#FF8FB1", "title_b": "#FFC2A1", "title_fg": "#FFFFFF",
        "pet_bg": "#FFFFFF", "pet_fg": "#4E3B2E", "pet_border": "#FFD9A0",
        "you_bg": "#5B8CFF", "you_fg": "#FFFFFF",
        "sys_fg": "#C9B79A", "input_bg": "#FFFFFF", "input_fg": "#4E3B2E",
        "placeholder": "#C9B79A", "accent": "#FF8FB1",
        "online": "#FF5252", "scroll": "#FFD9A0", "avatar_bg": "#FFE7C2",
    },
}


def build_chat_qss(theme="cozy"):
    """Build the chat window stylesheet from a palette in CHAT_THEMES."""
    p = CHAT_THEMES.get(theme, CHAT_THEMES["cozy"])
    return f"""
    QWidget#root {{ background:{p['root_bg']}; border:1px solid {p['root_border']};
        border-radius:16px; }}
    QFrame#title {{ background:qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p['title_a']}, stop:1 {p['title_b']});
        border-top-left-radius:15px; border-top-right-radius:15px;
        border-bottom:1px solid {p['root_border']}; }}
    QLabel#titleText {{ color:{p['title_fg']}; font-size:14px; font-weight:bold; }}
    QLabel#subtitle {{ color:{p['title_fg']}; font-size:10px; margin-left:2px; }}
    QLabel#statusPill {{ color:{p['online']}; background:rgba(255,255,255,80);
        border-radius:9px; padding:2px 8px; font-size:10px; }}
    QPushButton#closeBtn {{ background:transparent; color:{p['title_fg']};
        border:none; font-size:15px; border-radius:13px; }}
    QPushButton#closeBtn:hover {{ background:rgba(255,255,255,90); }}
    QLineEdit#input {{ background:{p['input_bg']}; color:{p['input_fg']};
        border:1px solid {p['root_border']}; border-radius:14px;
        padding:9px 14px; font-size:13px;
        placeholder-text-color:{p['placeholder']}; }}
    QLineEdit#input:focus {{ border:1px solid {p['accent']}; }}
    QPushButton#sendBtn {{ background:{p['accent']}; color:#FFFFFF; border:none;
        border-radius:18px; font-size:15px; }}
    QPushButton#sendBtn:hover {{ background:rgba(255,255,255,60); }}
    QScrollArea {{ background:transparent; border:none; }}
    QScrollBar:vertical {{ background:transparent; width:8px; margin:2px; }}
    QScrollBar::handle:vertical {{ background:{p['scroll']}; border-radius:4px;
        min-height:30px; }}
    QScrollBar::handle:vertical:hover {{ background:{p['you_bg']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
    """


class ChatWindow(QWidget):
    """A cute, frameless chat popup: rounded card, drag-anywhere header,
    message bubbles, and a styled input bar."""

    submitted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(380, 520)
        self._drag_off = QPoint()
        self._dragging = False

        self.setStyleSheet(build_chat_qss(CHAT_THEME))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.root = QFrame(self)
        self.root.setObjectName("root")
        outer.addWidget(self.root)

        root_lay = QVBoxLayout(self.root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ---- draggable header ----
        self.title = QFrame(self.root)
        self.title.setObjectName("title")
        self.title.setFixedHeight(46)
        h = QHBoxLayout(self.title)
        h.setContentsMargins(14, 0, 8, 0)
        t = QLabel("🐱 Study Buddy")
        t.setObjectName("titleText")
        sub = QLabel("your focus buddy")
        sub.setObjectName("subtitle")
        status = QLabel("● online")
        status.setObjectName("statusPill")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        h.addWidget(t)
        h.addWidget(sub)
        h.addStretch(1)
        h.addWidget(status)
        h.addWidget(close_btn)
        root_lay.addWidget(self.title)

        # ---- message bubbles (scroll area) ----
        self.msg_box = QWidget()
        self.msg_box.setStyleSheet("background:transparent;")
        self.msg_box.setAutoFillBackground(False)
        self.msg_lay = QVBoxLayout(self.msg_box)
        self.msg_lay.setContentsMargins(12, 12, 12, 12)
        self.msg_lay.setSpacing(8)
        self.msg_lay.addStretch(1)          # keeps bubbles pinned to the top
        self.scroll = QScrollArea(self.root)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.msg_box)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)
        root_lay.addWidget(self.scroll, 1)

        # ---- input bar (entry + send button) ----
        self.entry = QLineEdit(self.root)
        self.entry.setObjectName("input")
        self.entry.setPlaceholderText(
            'Ask me anything… or "remind me at 5pm to revise DBMS"')
        self.entry.returnPressed.connect(self._send)
        send_btn = QPushButton("➤")
        send_btn.setObjectName("sendBtn")
        send_btn.setFixedSize(36, 36)
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setToolTip("Send")
        send_btn.clicked.connect(self._send)
        inp = QHBoxLayout()
        inp.setContentsMargins(12, 10, 12, 12)
        inp.setSpacing(8)
        inp.addWidget(self.entry, 1)
        inp.addWidget(send_btn)
        root_lay.addLayout(inp)

        self.add("pet", "Hi! I'm your study buddy 🐱 Ask me anything, set a "
                        'reminder like "remind me in 25 minutes to take a break", '
                        "or ask me to search the web!")

    # ---- helpers ----
    def _bubble_row(self, who, label):
        """Wrap a bubble in a row widget so avatars / alignment are easy."""
        p = CHAT_THEMES.get(CHAT_THEME, CHAT_THEMES["cozy"])
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        if who == "sys":                      # centered pill
            lay.addStretch(1)
            lay.addWidget(label)
            lay.addStretch(1)
            return row
        if who == "pet":                      # avatar + bubble, left aligned
            avatar = QLabel("🐱")
            avatar.setFixedSize(30, 30)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(
                f"background:{p['avatar_bg']}; border-radius:15px;"
                " font-size:16px;")
            lay.addWidget(avatar, 0, Qt.AlignmentFlag.AlignBottom)
            lay.addWidget(label)
            lay.addStretch(1)
        else:                                 # "you" bubble, right aligned
            lay.addStretch(1)
            lay.addWidget(label)
        return row

    def _bubble(self, who, text):
        p = CHAT_THEMES.get(CHAT_THEME, CHAT_THEMES["cozy"])
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setFont(QFont("Segoe UI", 10))
        if who == "you":
            label.setStyleSheet(
                f"QLabel {{ background:{p['you_bg']}; color:{p['you_fg']};"
                " border-radius:12px; border-bottom-right-radius:4px;"
                " padding:8px 12px; }}")
        elif who == "pet":
            label.setStyleSheet(
                f"QLabel {{ background:{p['pet_bg']}; color:{p['pet_fg']};"
                f" border:1px solid {p['pet_border']}; border-radius:12px;"
                " border-bottom-left-radius:4px; padding:8px 12px; }}")
        else:  # sys: a small centered note
            label.setStyleSheet(
                f"QLabel {{ color:{p['sys_fg']}; background:{p['root_border']};"
                " border-radius:10px; padding:4px 10px; font-size:11px; }}")
        label.setMaximumWidth(250)
        return label

    def add(self, who, text):
        bubble = self._bubble(who, text)
        row = self._bubble_row(who, bubble)
        self.msg_lay.insertWidget(self.msg_lay.count() - 1, row)
        QTimer.singleShot(0, self._scroll_bottom)

    def _scroll_bottom(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _send(self):
        text = self.entry.text().strip()
        if text:
            self.entry.clear()
            self.submitted.emit(text)

    def show_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.entry.setFocus()

    # ---- drag the window by its header ----
    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton
                and self.title.geometry().contains(event.position().toPoint())):
            self._drag_off = event.globalPosition().toPoint() \
                - self.frameGeometry().topLeft()
            self._dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_off)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False


# ==================================================================
#  Reminder toast (a cute notification that never steals focus)
# ==================================================================
class ReminderToast(QWidget):
    """A small frameless card that floats top-right with the reminder text.
    Stays on top, doesn't accept focus (so it never yanks your typing),
    and hides itself after TOAST_AUTODISMISS_S seconds."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        p = CHAT_THEMES.get(CHAT_THEME, CHAT_THEMES["cozy"])
        self.setStyleSheet(f"""
            QFrame#toastRoot {{
                background:{p['root_bg']}; border:1px solid {p['root_border']};
                border-radius:14px;
            }}
            QLabel#toastTitle {{ color:{p['accent']}; font-size:13px; font-weight:bold; }}
            QLabel#toastBody {{ color:{p['pet_fg']}; font-size:12px; }}
            QPushButton#toastClose {{ background:transparent; color:{p['sys_fg']};
                border:none; font-size:13px; border-radius:10px; }}
            QPushButton#toastClose:hover {{ background:{p['root_border']}; }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self)
        self.frame.setObjectName("toastRoot")
        outer.addWidget(self.frame)

        lay = QVBoxLayout(self.frame)
        lay.setContentsMargins(14, 10, 12, 12)
        lay.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        icon = QLabel("⏰")
        icon.setStyleSheet("font-size:16px;")
        title = QLabel("Reminder")
        title.setObjectName("toastTitle")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("toastClose")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        head.addWidget(icon)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(close_btn)
        lay.addLayout(head)

        self.body = QLabel()
        self.body.setObjectName("toastBody")
        self.body.setWordWrap(True)
        self.body.setMaximumWidth(260)
        lay.addWidget(self.body)

    def show_reminder(self, text):
        self.body.setText(text)
        self.adjustSize()
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.right() - self.width() - 24, geo.top() + 24)
        self.show()
        self.raise_()
        QTimer.singleShot(TOAST_AUTODISMISS_S * 1000, self.hide)


# ==================================================================
#  The pet's own keyboard (it types along when you do)
# ==================================================================
class PetKeyboard(QWidget):
    """A tiny keyboard that slides in right next to the pet. Keys flash while
    the pet is typing — it mirrors you typing on your real keyboard."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(KB_WIDTH, KB_HEIGHT)
        self._keys = self._build_keys()
        self._typing = False
        self._flash = -1
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._next_flash)
        self._flash_timer.start(150)

    def _build_keys(self):
        """Lay out 3 rows of keys; returns a list of QRectF key positions."""
        rows = [[1] * 10, [1] * 10, [1.5, 1, 1, 1, 1, 1, 1.5]]
        keys = []
        pad, gap, kh = 6, 4, 14
        y = pad
        for row in rows:
            n = len(row)
            kw = (KB_WIDTH - 2 * pad - gap * (n - 1)) / sum(row)
            x = pad
            for frac in row:
                w = kw * frac - gap / 2
                keys.append(QRectF(x, y, w, kh))
                x += w + gap
            y += kh + gap
        return keys

    def set_typing(self, on):
        self._typing = bool(on)
        if not on:
            self._flash = -1
        self.update()

    def _next_flash(self):
        if self._typing:
            self._flash = random.randrange(len(self._keys))
            self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#9a8f7a"), 2))          # base plate
        p.setBrush(QColor("#f7f1e3"))
        p.drawRoundedRect(QRectF(2, 2, KB_WIDTH - 4, KB_HEIGHT - 4), 12, 12)
        for i, r in enumerate(self._keys):
            if self._typing and i == self._flash:
                p.setBrush(QColor("#ffcf5c"))          # lit key while typing
            else:
                p.setBrush(QColor("#ffffff"))
            p.setPen(QPen(QColor("#ddd3bf"), 1))
            p.drawRoundedRect(r, 3, 3)
        p.end()


# ==================================================================
#  The pet
# ==================================================================
class DesktopPet(QWidget):
    def __init__(self, sim_mode=None):
        super().__init__()
        self.cfg = load_config()
        self.sim_mode = sim_mode or ""   # "--sim" demo mode, if any

        print("Working dir:", HERE)
        for path in GIF_MAP.values():
            full = os.path.join(HERE, path)
            print(f"  {path}: {'FOUND' if os.path.exists(full) else 'MISSING!'}")

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(PET_SIZE, PET_SIZE)

        self.label = QLabel(self)
        self.label.setGeometry(0, 0, PET_SIZE, PET_SIZE)

        # pre-load one QMovie per state, sharing one frame handler for flipping
        self.movies = {}
        for state, path in GIF_MAP.items():
            m = QMovie(os.path.join(HERE, path))
            m.setScaledSize(self.label.size())
            if not m.isValid():
                print(f"WARNING: '{path}' is not a valid GIF!")
            m.frameChanged.connect(self._on_frame)
            self.movies[state] = m

        self.screen_geo = QApplication.primaryScreen().availableGeometry()

        # movement state
        self.facing = 1
        self.dragging = False
        self._drag_off = QPoint()
        self.idle_ticks = 0

        sx = self.screen_geo.center().x() - PET_SIZE // 2
        sy = self.screen_geo.center().y() - PET_SIZE // 2
        self.pos_f = [float(sx), float(sy)]
        self.target = [float(sx), float(sy)]
        self.speed = 0.0
        self.move(sx, sy)

        # rest cycle
        self.resting = False
        self.phase_secs = random.randint(*ACTIVE_SECS)

        # emotion (productivity) + timers
        self.emotion = "calm"          # calm / cheering / warning / angry / sleeping
        self.warn_source = None        # where the anger came from: "distraction" / "idle"
        self.study_ms = 0
        self.warn_ms = 0
        self.cur_gif = None
        self._apply_gif("idle")

        # screen context + needs (real-pet layer)
        self.context = "other"         # typing / study / movie / distraction / other
        self.typing_since = time.monotonic()
        self.energy = ENERGY_START
        self.sleeping = False
        self.mood = None               # transient "fun" gif: popcorn / play / happy / cheer
        self.mood_until = 0.0
        self._typing_burst_until = 0.0   # end of the current typing burst
        self._typing_pause_until = 0.0   # end of the burst+pause cycle
        self._popcorn_cooldown = 0.0
        self._study_encourage_secs = 0

        # chat + AI
        self.chat = ChatWindow()
        self.chat.submitted.connect(self._on_chat)
        self.toast = ReminderToast()

        # pet's own keyboard — slides in next to the pet while you type
        self.kb = PetKeyboard()
        self.kb.hide()

        self.history = []              # Gemini conversation history
        self.worker = None

        # know when you type in ANY app (skipped in --sim so demos stay clean)
        if not self.sim_mode:
            start_keyboard_hook()
        QApplication.instance().aboutToQuit.connect(stop_keyboard_hook)

        # reminders: list of {"when": datetime, "task": str}
        self.reminders = []
        self.bubble = None

        # timers
        self._mk_timer(self._tick, 1000)
        self._mk_timer(self._scan, 5000)
        self._mk_timer(self._decide, DECIDE_MS)
        self._mk_timer(self._move_step, MOVE_MS)
        self._mk_timer(self._check_reminders, 15000)

        self.show()
        self.raise_()
        print("Pet shown at", self.pos())

    def _mk_timer(self, fn, ms):
        t = QTimer(self)
        t.timeout.connect(fn)
        t.start(ms)
        return t

    # ---------------- rendering ----------------
    def _on_frame(self):
        pm = self.movie.currentPixmap()
        if pm.isNull():
            return
        if self.facing == -1:
            pm = pm.transformed(QTransform().scale(-1, 1))
        self.label.setPixmap(pm)

    def _apply_gif(self, state):
        """Switch the visible animation (only if it changed)."""
        if self.cur_gif == state:
            return
        if self.cur_gif:
            self.movies[self.cur_gif].stop()
        self.cur_gif = state
        self.movie = self.movies[state]
        self.movie.start()

    def _update_anim(self):
        """Pick the gif from mood + emotion + movement (mood/anger win)."""
        if self.mood and time.monotonic() > self.mood_until:
            self.mood = None
        moving = (self.speed > 0 and not self.sleeping
                  and not (self.resting and not self._play_active()))
        if self.dragging:
            state = "run"
        elif self.sleeping:
            state = "sleep"
        elif self.emotion == "angry":
            state = "angry"
        elif self.emotion == "warning":
            state = "warning"
        elif self.mood == "popcorn":
            state = "popcorn"
        elif self.mood == "play":
            state = "play"
        elif self.mood == "happy":
            state = "happy"
        elif self.mood == "cheer" or self.emotion == "cheering":
            state = "cheer"
        elif self.resting:
            state = "rest"
        elif moving:
            state = "run" if self.speed >= 6 else "walk"
        else:
            state = "idle"
        self._apply_gif(state)

    # ---------------- productivity ----------------
    def _tick(self):
        # focus clock: only counts while actually studying / being productive
        if self.emotion in ("calm", "cheering") and self.context in ("study", "other"):
            self.study_ms += 1000
            if self.study_ms >= STUDY_TARGET_MS and self.emotion == "calm":
                self.emotion = "cheering"
                self._say("2 hours of focus — great work! Take a short break.")

        # warning -> angry escalation (covers both distraction and idle anger)
        if self.emotion == "warning":
            self.warn_ms += 1000
            if self.warn_ms >= WARN_TIMEOUT_MS:
                self.emotion = "angry"
                self._update_anim()

        # energy + sleep
        self._energy_tick()

        # rest cycle countdown (paused while sleeping AND during keyboard play,
        # so a play session is never interrupted mid-way by a rest flip)
        if not self.sleeping and not self._play_active():
            self.phase_secs -= 1
            if self.phase_secs <= 0:
                self.resting = not self.resting
                if self.resting:
                    self.speed = 0.0
                    self.phase_secs = random.randint(*REST_SECS)
                else:
                    self.phase_secs = random.randint(*ACTIVE_SECS)

        # periodic encouragement while studying
        self._study_encourage_tick()

        self._update_anim()

    # ---------------- energy / sleep (real-pet layer) ----------------
    def _energy_tick(self):
        if self.sleeping:
            self.energy = min(100.0, self.energy + ENERGY_REGEN_SLEEP)
            if self.energy >= SLEEP_UNTIL:
                self._wake_up()
            return
        drain = ENERGY_DRAIN_MOVE if self.speed > 0 else ENERGY_DRAIN_IDLE
        if self.mood == "play":
            drain = ENERGY_DRAIN_PLAY
        self.energy = max(0.0, self.energy - drain)
        if self.energy <= SLEEPY_AT and self.emotion not in ("warning", "angry"):
            self._go_to_sleep()

    def _go_to_sleep(self):
        self.sleeping = True
        self.emotion = "sleeping"
        self.mood = None
        self.speed = 0.0
        self._kb_hide()
        self._say("...so sleepy... 😴")
        self._update_anim()

    def _wake_up(self):
        if not self.sleeping:
            return
        self.sleeping = False
        self.emotion = "calm"
        self.warn_source = None
        self.energy = SLEEP_UNTIL
        self._say("*yawn* I'm up! 😺")
        self._update_anim()

    def _study_encourage_tick(self):
        if (self.context == "study" and self.emotion in ("calm", "cheering")
                and not self.sleeping):
            self._study_encourage_secs += 1
            if self._study_encourage_secs >= STUDY_CHEER_S:
                self._study_encourage_secs = 0
                self.mood = "cheer"
                self.mood_until = time.monotonic() + 4
                self._update_anim()
                self._say(random.choice(ENCOURAGE_LINES))

    def _set_context(self, ctx):
        """React to a (possibly new) screen context. Shared by real window
        scans and --sim demo mode so both run the exact same code path."""
        if ctx == self.context:
            return
        old = self.context
        self.context = ctx
        if old == "typing":            # user stopped typing -> put the keyboard away
            self._kb_hide()
            if self.mood == "play":
                self.mood = None
                self._update_anim()
        # in demo mode, leaving a distraction calms the pet so the cycle is clean
        if self.sim_mode and self.warn_source == "distraction" and ctx != "distraction":
            self.emotion = "calm"
            self.warn_source = None
            self.warn_ms = 0
        if ctx == "typing":
            self.typing_since = time.monotonic()
            self._typing_burst_until = 0.0
            self._typing_pause_until = 0.0
            self._kb_show()            # keyboard comes out the moment typing starts
        elif ctx == "study" and self.emotion == "calm" and not self.sleeping:
            # starting to study -> an immediate cheer so the pet visibly reacts
            self.mood = "cheer"
            self.mood_until = time.monotonic() + 4
            self._update_anim()
            self._say(random.choice(STUDY_START_LINES))

    def _scan(self):
        # already upset about a distraction -> must be petted to calm down
        # (demo mode ignores this so --sim cycle keeps moving)
        if not self.sim_mode and self.emotion in ("warning", "angry") \
                and self.warn_source == "distraction":
            return

        if self.sim_mode:
            if self.sim_mode == "cycle":
                ctx = ("typing", "study", "movie", "distraction")[
                    int(time.monotonic() // 20) % 4]
            else:
                ctx = self.sim_mode
        else:
            title, proc = active_window_info()
            ctx = categorize_window(title, proc)
            # you typed recently in ANY app -> that's typing (a movie keeps
            # priority so a stray key while watching doesn't kill the popcorn)
            if keyboard_typing_now() and ctx != "movie":
                ctx = "typing"

        self._set_context(ctx)
        if ctx == "distraction" and self.emotion not in ("warning", "angry"):
            self.warn_ms = 0
            self.emotion = "warning"
            self.warn_source = "distraction"
            self._update_anim()
            self._say(random.choice(DISTRACTION_LINES))

    # ---------------- behavior brain ----------------
    def _look_at_cursor(self):
        """Turn the cat to face the mouse cursor (reads as 'watching the mouse').
        Works with any GIF — the whole body flips toward the cursor."""
        cur = QCursor.pos()
        cx = self.pos_f[0] + PET_SIZE / 2
        self.facing = -1 if cur.x() < cx else 1

    def _center(self):
        return self.pos_f[0] + PET_SIZE / 2, self.pos_f[1] + PET_SIZE / 2

    def _set_target(self, x, y, speed):
        x = max(self.screen_geo.left(), min(x, self.screen_geo.right() - PET_SIZE))
        y = max(self.screen_geo.top(),  min(y, self.screen_geo.bottom() - PET_SIZE))
        self.target = [float(x), float(y)]
        self.speed = float(speed)

    def _play_active(self):
        """True while the user is typing — the pet is committed to its keyboard
        (rest cycle stays paused the whole time, like the popcorn mood)."""
        return self.context == "typing"

    def _kb_show(self):
        """Slide the pet's keyboard in, right next to it (just below)."""
        px, py = self.pos_f
        x = px + PET_SIZE // 2 - KB_WIDTH // 2
        y = py + PET_SIZE + 4
        x = max(self.screen_geo.left() + 2, min(x, self.screen_geo.right() - KB_WIDTH - 2))
        y = max(self.screen_geo.top() + 2,  min(y, self.screen_geo.bottom() - KB_HEIGHT - 2))
        self.kb.move(int(x), int(y))
        if not self.kb.isVisible():
            self.kb.show()
            self.kb.raise_()

    def _kb_hide(self):
        """Put the keyboard away and stop any key flashes."""
        if self.kb.isVisible():
            self.kb.hide()
            self.kb.set_typing(False)

    def _react(self):
        """Real-pet wants, driven by screen context + needs. Runs every _decide."""
        if self.dragging or self.sleeping:
            return
        ctx = self.context
        now = time.monotonic()

        # 1) you left the PC / stopped paying attention -> seek, grumpy, angry
        #    (skipped in --sim demo mode so a stale idle timeout can't hijack it)
        if not self.sim_mode:
            idle = idle_seconds()
            if idle >= IDLE_ANGRY_S and ctx != "movie" and ctx != "distraction":
                self.emotion = "angry"
                self.warn_source = "idle"
                self._update_anim()
                self._say("Hello?? Anyone there? 😾")
            elif idle >= IDLE_GRUMPY_S and ctx != "movie" and ctx != "distraction" \
                    and self.emotion not in ("warning", "angry"):
                self.emotion = "warning"
                self.warn_source = "idle"
                self.warn_ms = 0
                self._update_anim()
            elif IDLE_SEEK_AFTER_S <= idle < IDLE_GRUMPY_S:
                cur = QCursor.pos()
                self._set_target(cur.x() - PET_SIZE / 2, cur.y() - PET_SIZE / 2, WANDER_SPEED)
            elif idle < IDLE_SEEK_AFTER_S and self.emotion in ("warning", "angry") \
                    and self.warn_source == "idle":
                # you're back and active again -> calm down
                self.emotion = "calm"
                self.warn_source = None
                self.warn_ms = 0
                self._update_anim()

        # 2) movie -> sit and eat popcorn
        if ctx == "movie" and now > self._popcorn_cooldown:
            self.mood = "popcorn"
            self.mood_until = now + MOVIE_MOOD_S
            self._popcorn_cooldown = now + MOVIE_COOLDOWN_S
            self._update_anim()
            self._say(random.choice(POPCORN_LINES))

        # 3) typing/coding -> handled in _decide: the pet sits and types on its
        #    own keyboard, which slides in right next to it

    def _decide(self):
        if self.dragging or self.sleeping:
            return
        now = time.monotonic()
        self._look_at_cursor()          # always face the mouse when awake

        # expire any mood that has run its course
        if self.mood and now > self.mood_until:
            self.mood = None
            self._update_anim()

        self._react()
        if self.sleeping:
            return

        # you're typing -> the pet sits where it is and types on its own
        # keyboard (which slides in right next to it). Types for as long as you
        # do, with a short paw-stretch pause every TYPING_TYPE_S seconds.
        if self.context == "typing":
            self.speed = 0.0               # settle in place, don't wander off
            self._kb_show()                # keyboard follows the pet
            now = time.monotonic()
            if now > self._typing_pause_until:           # start a fresh burst
                self._typing_burst_until = now + TYPING_TYPE_S
                self._typing_pause_until = now + TYPING_TYPE_S + TYPING_PAUSE_S
            if now < self._typing_burst_until:           # in a typing burst
                if self.mood != "play":
                    self.mood = "play"
                    self.mood_until = self._typing_burst_until   # hold, no flicker
                    self._update_anim()
                self.kb.set_typing(True)                 # keys light up
                aggro = (now - self.typing_since) > AGGRO_TYPING_S
                lines = AGGRO_PLAY_LINES if aggro else PLAY_LINES
                if random.random() < 0.10 and not (self.bubble and self.bubble.isVisible()):
                    self._say(random.choice(lines))
            else:                                        # short paw-stretch pause
                if self.mood == "play":
                    self.mood = None
                    self._update_anim()
                self.kb.set_typing(False)
            return

        if self.resting:                       # resting = stay put
            return

        # movie: sit and watch (don't chase/wander while a film is on)
        if self.context == "movie":
            self.speed = 0.0
            return

        cur = QCursor.pos()
        cx, cy = self._center()
        d = math.hypot(cur.x() - cx, cur.y() - cy)

        if d < CHASE_RADIUS:                    # chase nearby cursor
            self.idle_ticks = 0
            if d > CHASE_GAP:
                ux, uy = (cur.x() - cx) / d, (cur.y() - cy) / d
                tx = cur.x() - ux * CHASE_GAP - PET_SIZE / 2
                ty = cur.y() - uy * CHASE_GAP - PET_SIZE / 2
                self._set_target(tx, ty, CHASE_SPEED)
            else:
                self.speed = 0.0
        else:
            self.idle_ticks += 1
            if self.idle_ticks >= ATTENTION_TICKS:          # ignored -> come over
                self.idle_ticks = 0
                self._set_target(cur.x() - PET_SIZE / 2,
                                 cur.y() - PET_SIZE / 2, WANDER_SPEED)
            elif random.random() < WANDER_CHANCE:           # stroll randomly
                tx = random.randint(self.screen_geo.left(),
                                    self.screen_geo.right() - PET_SIZE)
                ty = random.randint(self.screen_geo.top(),
                                    self.screen_geo.bottom() - PET_SIZE)
                self._set_target(tx, ty, WANDER_SPEED)

    def _move_step(self):
        if self.dragging or self.sleeping or self.speed <= 0:
            return
        if self.resting and not self._play_active():
            return
        x, y = self.pos_f
        dx, dy = self.target[0] - x, self.target[1] - y
        dist = math.hypot(dx, dy)
        if dist <= 1:
            self.speed = 0.0
            self._update_anim()
            return
        step = min(self.speed, dist)
        self.pos_f = [x + dx / dist * step, y + dy / dist * step]
        self.facing = -1 if dx < 0 else 1
        self.move(int(self.pos_f[0]), int(self.pos_f[1]))
        if self.bubble:                          # keep speech bubble attached
            self._place_bubble()

    # ---------------- chat + Gemini ----------------
    def _ensure_api_key(self):
        key = (
            self.cfg.get("api_key")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if key:
            return key
        key, ok = QInputDialog.getText(
            self.chat, "Google Gemini API key",
            "Paste your Gemini API key from aistudio.google.com/apikey\n"
            "(free, no card needed — stored locally in config.json):")
        key = (key or "").strip()
        if ok and key:
            self.cfg["api_key"] = key
            save_config(self.cfg)
            return key
        return None

    def _on_chat(self, text):
        self.chat.add("you", text)

        # 1) reminder command? handle locally, don't spend an API call
        if self._try_reminder(text):
            return

        # 2) otherwise ask Gemini
        key = self._ensure_api_key()
        if not key:
            self.chat.add("sys", "No API key set — can't reach Gemini.")
            return

        self.history.append({"role": "user", "content": text})
        system = self._system_prompt()
        self.chat.add("sys", "thinking...")
        self.worker = AIWorker(key, system, list(self.history))
        self.worker.reply.connect(self._on_reply)
        self.worker.start()

    def _on_reply(self, text):
        self.history.append({"role": "assistant", "content": text})
        self.chat.add("pet", text)
        self._say(text[:80] + ("..." if len(text) > 80 else ""))

    def _system_prompt(self):
        win = active_window_title()
        rem = "; ".join(f"{r['when'].strftime('%H:%M')} {r['task']}"
                        for r in self.reminders) or "none"
        return (
            "You are a friendly, motivating desktop study-pet for a final-year "
            "CS student preparing for competitive exams (SEBI Grade A IT, SSC "
            "CGL). Be warm, concise, and practical. Help with study questions, "
            "planning, and staying focused. Keep replies short unless asked to "
            "explain in depth.\n"
            f"Current active window on the user's screen: '{win}'.\n"
            f"Pending reminders: {rem}."
        )

    # ---------------- reminders ----------------
    def _try_reminder(self, text):
        low = text.lower()
        now = datetime.datetime.now()
        when = None
        task = None

        # "remind me in 25 minutes to take a break"
        m = re.search(r"remind me in\s+(\d+)\s*(min|mins|minute|minutes|hour|hours|hr|hrs)"
                      r"(?:\s+to)?\s*(.*)", low)
        if m:
            n = int(m.group(1))
            unit = m.group(2)
            delta = datetime.timedelta(hours=n) if unit.startswith(("hour", "hr")) \
                else datetime.timedelta(minutes=n)
            when = now + delta
            task = m.group(3).strip() or "your task"

        # "remind me at 17:30 to revise DBMS"  /  "at 5:30 pm ..."
        if when is None:
            m = re.search(r"remind me at\s+(\d{1,2}):(\d{2})\s*(am|pm)?"
                          r"(?:\s+to)?\s*(.*)", low)
            if m:
                hh, mm = int(m.group(1)), int(m.group(2))
                ap = m.group(3)
                if ap == "pm" and hh < 12:
                    hh += 12
                if ap == "am" and hh == 12:
                    hh = 0
                when = now.replace(hour=hh % 24, minute=mm, second=0, microsecond=0)
                if when <= now:
                    when += datetime.timedelta(days=1)   # already passed -> tomorrow
                task = m.group(4).strip() or "your task"

        if when is None:
            return False

        self.reminders.append({"when": when, "task": task})
        self.reminders.sort(key=lambda r: r["when"])
        self.chat.add("pet", f'Okay! I\'ll remind you at '
                             f'{when.strftime("%H:%M")} to "{task}".')
        return True

    def _check_reminders(self):
        now = datetime.datetime.now()
        due = [r for r in self.reminders if r["when"] <= now]
        for r in due:
            self.reminders.remove(r)
            self.emotion = "cheering"
            self._update_anim()
            msg = f'⏰ Reminder: {r["task"]}'
            self.chat.add("pet", msg)
            self._say(msg)
            self._show_toast(r["task"])
            if TOAST_OPENS_CHAT and not self.chat.isVisible():
                self.chat.show_focus()

    def _show_toast(self, task):
        """Show the reminder toast popup (does not steal focus)."""
        self.toast.show_reminder(task)

    # ---------------- speech bubble ----------------
    def _say(self, text):
        if self.bubble is None:
            self.bubble = QLabel(None)
            self.bubble.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.ToolTip)
            self.bubble.setStyleSheet(
                "background:#fffce8; border:1px solid #caa; border-radius:8px;"
                "padding:6px; color:#333;")
            self.bubble.setWordWrap(True)
            self.bubble.setMaximumWidth(240)
            self.bubble.setFont(QFont("Segoe UI", 9))
        self.bubble.setText(text)
        self.bubble.adjustSize()
        self._place_bubble()
        self.bubble.show()
        QTimer.singleShot(6000, self._hide_bubble)

    def _place_bubble(self):
        if self.bubble:
            self.bubble.move(int(self.pos_f[0]) - 60,
                             int(self.pos_f[1]) - self.bubble.height() - 4)

    def _hide_bubble(self):
        if self.bubble:
            self.bubble.hide()

    # ---------------- interaction ----------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self._drag_off = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            # petting soothes it, restarts the focus cycle, and wakes it up
            self.warn_ms = 0
            self.study_ms = 0
            self.warn_source = None
            self.emotion = "calm"
            if self.sleeping:
                self._wake_up()
            else:
                self.mood = "happy"
                self.mood_until = time.monotonic() + 2.5
            self._update_anim()   # -> shows the "run" gif while dragging

    def mouseMoveEvent(self, event):
        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            p = event.globalPosition().toPoint() - self._drag_off
            self.move(p)
            self.pos_f = [float(p.x()), float(p.y())]
            if self.bubble:
                self._place_bubble()

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.target = list(self.pos_f)
        self.speed = 0.0
        self._update_anim()

    def mouseDoubleClickEvent(self, event):
        self.chat.show_focus()

    def contextMenuEvent(self, event):
        menu = QMenu()
        act_chat = menu.addAction("Chat with pet")
        act_key = menu.addAction("Set / change API key")
        menu.addSeparator()
        act_quit = menu.addAction("Quit")
        chosen = menu.exec(event.globalPos())
        if chosen == act_chat:
            self.chat.show_focus()
        elif chosen == act_key:
            self.cfg.pop("api_key", None)
            save_config(self.cfg)
            self._ensure_api_key()
        elif chosen == act_quit:
            QApplication.quit()


if __name__ == "__main__":
    # optional demo mode:  pet.py --sim <typing|movie|study|distraction|cycle>
    sim_mode = None
    if "--sim" in sys.argv:
        i = sys.argv.index("--sim")
        sim_mode = sys.argv[i + 1] if i + 1 < len(sys.argv) else "cycle"
        del sys.argv[i:i + 2]          # keep Qt's argv clean

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # closing chat won't kill the pet
    pet = DesktopPet(sim_mode=sim_mode)
    sys.exit(app.exec())