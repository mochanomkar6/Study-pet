# Simple unit tests for the pet's screen-context detection.
# Run:  venv\Scripts\python.exe test_categorize.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pet import categorize_window


def test_typing_wins():
    assert categorize_window("main.py - Visual Studio Code", "Code.exe") == "typing"
    assert categorize_window("Untitled - Notepad++", "notepad++.exe") == "typing"


def test_browser_video_is_movie():          # the regression this update fixes
    assert categorize_window("Big Buck Bunny - YouTube", "chrome.exe") == "movie"
    assert categorize_window("Squid Game | Netflix", "brave.exe") == "movie"
    assert categorize_window("clip.mp4 - Chrome", "firefox.exe") == "movie"
    assert categorize_window("movie.mkv", "msedge.exe") == "movie"


def test_standalone_player_is_movie():
    assert categorize_window("Big Buck Bunny.mkv", "vlc.exe") == "movie"
    assert categorize_window("show.mov", "potplayermini64.exe") == "movie"


def test_browser_course_is_study():
    assert categorize_window("SQL Course - Udemy", "chrome.exe") == "study"
    assert categorize_window("DBMS Lecture 5", "msedge.exe") == "study"


def test_study_app_is_study():
    assert categorize_window("", "notion.exe") == "study"
    assert categorize_window("", "sumatrapdf.exe") == "study"


def test_distraction():
    assert categorize_window("WhatsApp", "WhatsApp.exe") == "distraction"
    assert categorize_window("", "discord.exe") == "distraction"


def test_other():
    assert categorize_window("Random folder", "explorer.exe") == "other"


def test_case_insensitive():
    assert categorize_window("C++ Tutorial", "CHROME.EXE") == "study"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
            passed += 1
    print(f"All {passed} tests passed!")
