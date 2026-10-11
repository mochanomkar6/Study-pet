"""
make_gifs.py  —  generates placeholder animated GIFs for the study pet.
Run once from the project root:  py make_gifs.py
"""
import math
from PIL import Image, ImageDraw

SIZE = 128
FRAMES = 12
DURATION = 80

STATES = [
    ("idle.gif",    (100, 180, 255), "breathe"),
    ("cheer.gif",   (120, 220, 120), "bounce"),
    ("warning.gif", (255, 200,  60), "shake"),
    ("angry.gif",   (230,  80,  80), "shake"),
    ("walk.gif",    (140, 200, 255), "walk"),
    ("run.gif",     (170, 120, 255), "run"),
    ("rest.gif",    (150, 160, 180), "rest"),
    ("popcorn.gif", (255, 180,  80), "popcorn"),
    ("sleep.gif",   (120, 140, 170), "sleep"),
    ("play.gif",    (150, 220, 120), "play"),
    ("happy.gif",   (255, 130, 170), "happy"),
]


def draw_blob(color, phase, motion):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = SIZE // 2, SIZE // 2
    r = 40
    dx = dy = squash = 0
    t = phase * 2 * math.pi

    if motion == "breathe":
        dy = int(3 * math.sin(t))
        squash = int(2 * math.sin(t))
    elif motion == "bounce":
        dy = int(-14 * abs(math.sin(t)))
        squash = int(6 * math.sin(t))
    elif motion == "shake":
        dx = int(5 * math.sin(t * 3))
        dy = int(2 * math.sin(t * 2))
    elif motion == "walk":
        dy = int(-5 * abs(math.sin(t)))
        dx = int(3 * math.sin(t))
        squash = int(3 * math.sin(t))
    elif motion == "run":
        dy = int(-9 * abs(math.sin(t * 1.5)))
        dx = int(6 * math.sin(t * 1.5))
        squash = int(7 * math.sin(t * 1.5))
    elif motion == "rest":
        dy = int(8 + 2 * math.sin(t * 0.7))
        squash = int(6 + 4 * math.sin(t * 0.7))
    elif motion == "popcorn":
        dy = int(-6 * abs(math.sin(t * 1.3)))
        squash = int(4 * math.sin(t * 1.3))
    elif motion == "sleep":
        dy = int(4 + 2 * math.sin(t * 0.5))
        squash = int(6 + 4 * math.sin(t * 0.5))
    elif motion == "play":
        dx = int(10 * math.sin(t * 4))
        squash = int(5 * abs(math.sin(t * 4)))
    elif motion == "happy":
        dy = int(-8 * abs(math.sin(t * 1.5)))
        squash = int(5 * math.sin(t * 1.5))

    left, right = cx - r + dx, cx + r + dx
    top, bottom = cy - r + dy + squash, cy + r + dy - squash
    d.ellipse([left, top, right, bottom], fill=color + (255,))

    eye_y = top + (bottom - top) // 3
    eye_dx = r // 3
    er = 5
    if motion == "rest":
        d.line([cx - eye_dx - er, eye_y, cx - eye_dx + er, eye_y], fill=(30, 30, 30, 255), width=3)
        d.line([cx + eye_dx - er, eye_y, cx + eye_dx + er, eye_y], fill=(30, 30, 30, 255), width=3)
    else:
        for ex in (cx - eye_dx, cx + eye_dx):
            d.ellipse([ex - er, eye_y - er, ex + er, eye_y + er], fill=(30, 30, 30, 255))

    # --- per-motion decorations (placeholders the user will replace with real cats) ---
    if motion == "popcorn":
        bx = cx + dx
        d.polygon([(bx - 8, bottom + 2), (bx + 8, bottom + 2),
                   (bx + 14, bottom + 18), (bx - 14, bottom + 18)],
                  fill=(220, 120, 40, 255))
        for k in range(3):
            kx = bx - 14 + k * 14 + int(4 * math.sin(t * 4 + k))
            ky = bottom - 8 - int(7 * math.sin(t * 4 + k * 2))
            d.ellipse([kx - 4, ky - 4, kx + 4, ky + 4], fill=(255, 242, 200, 255))
    elif motion == "sleep":
        d.text((cx + eye_dx + 6, top - 20), "Z z", fill=(215, 225, 245, 255))
    elif motion == "play":
        pawx = cx + r // 2 + int(8 * math.sin(t * 4))
        d.ellipse([pawx - 7, cy - 3, pawx + 7, cy + 9], fill=(150, 220, 120, 255))
        d.ellipse([pawx - 10, cy - 9, pawx + 4, cy + 3], fill=(150, 220, 120, 255))
    elif motion == "happy":
        hx, hy = cx + r // 3, top - 6
        d.ellipse([hx - 8, hy - 4, hx - 2, hy + 4], fill=(255, 80, 80, 255))
        d.ellipse([hx - 2, hy - 4, hx + 4, hy + 4], fill=(255, 80, 80, 255))
        d.polygon([(hx - 8, hy - 1), (hx + 4, hy - 1), (hx - 2, hy + 9)],
                  fill=(255, 80, 80, 255))
    return img


def build_gif(filename, color, motion):
    frames = [draw_blob(color, i / FRAMES, motion) for i in range(FRAMES)]
    frames[0].save(filename, save_all=True, append_images=frames[1:],
                   duration=DURATION, loop=0, disposal=2, transparency=0)
    print(f"  created {filename}")


if __name__ == "__main__":
    print("Generating placeholder GIFs...")
    for name, color, motion in STATES:
        build_gif(name, color, motion)
    print("Done. 11 GIFs created.")
