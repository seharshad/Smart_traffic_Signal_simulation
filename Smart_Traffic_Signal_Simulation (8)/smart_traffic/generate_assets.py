"""
Generates simple, original top-view vehicle icons, traffic-signal icons,
and an intersection background — all drawn with PIL (no external images).
Vehicles face "up" (north) by default; the simulation rotates them for
other directions.
"""
from PIL import Image, ImageDraw
import math
import os

OUT = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(os.path.join(OUT, "signals"), exist_ok=True)


def rounded_rect(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def new_canvas(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


# ---------------------------------------------------------------- CAR
def make_car(color=(210, 60, 60)):
    w, h = 34, 56
    img = new_canvas(w, h)
    d = ImageDraw.Draw(img)
    rounded_rect(d, [3, 2, w - 3, h - 2], 10, fill=color, outline=(30, 30, 30), width=2)
    # windshield + rear window
    d.rounded_rectangle([7, 10, w - 7, 20], radius=4, fill=(160, 210, 235, 230))
    d.rounded_rectangle([7, h - 20, w - 7, h - 10], radius=4, fill=(160, 210, 235, 230))
    # roof line
    d.rounded_rectangle([9, 21, w - 9, h - 21], radius=4, fill=(min(color[0]+25,255), min(color[1]+25,255), min(color[2]+25,255)))
    # headlights
    d.ellipse([5, 3, 10, 7], fill=(255, 244, 180))
    d.ellipse([w - 10, 3, w - 5, 7], fill=(255, 244, 180))
    return img


# ---------------------------------------------------------------- BIKE
def make_bike(color=(40, 40, 40)):
    w, h = 16, 34
    img = new_canvas(w, h)
    d = ImageDraw.Draw(img)
    d.ellipse([4, 2, w - 4, 10], fill=(230, 60, 60))  # rider helmet
    d.rectangle([w / 2 - 2, 8, w / 2 + 2, h - 6], fill=color)  # body/bike line
    d.ellipse([2, h - 10, w - 2, h - 2], fill=(20, 20, 20))  # rear wheel shadow
    d.ellipse([w / 2 - 5, 10, w / 2 + 5, 20], fill=(90, 90, 90))  # seat area
    return img


# ---------------------------------------------------------------- BUS
def make_bus(color=(235, 190, 40)):
    w, h = 38, 92
    img = new_canvas(w, h)
    d = ImageDraw.Draw(img)
    rounded_rect(d, [2, 2, w - 2, h - 2], 8, fill=color, outline=(40, 40, 40), width=2)
    # windows
    for i in range(6):
        y0 = 12 + i * 12
        d.rounded_rectangle([6, y0, w - 6, y0 + 8], radius=2, fill=(150, 205, 230, 230))
    d.rectangle([2, h - 14, w - 2, h - 2], fill=(60, 60, 60))  # back bumper
    return img


# ---------------------------------------------------------------- TRUCK
def make_truck(color=(70, 120, 190)):
    w, h = 36, 90
    img = new_canvas(w, h)
    d = ImageDraw.Draw(img)
    # cargo box
    rounded_rect(d, [2, 26, w - 2, h - 2], 6, fill=color, outline=(30, 30, 30), width=2)
    # cabin
    rounded_rect(d, [5, 2, w - 5, 28], 8, fill=(90, 90, 95), outline=(30, 30, 30), width=2)
    d.rounded_rectangle([9, 6, w - 9, 16], radius=3, fill=(160, 210, 235, 230))
    return img


# ---------------------------------------------------------------- RICKSHAW
def make_rickshaw(color=(235, 150, 40)):
    w, h = 26, 40
    img = new_canvas(w, h)
    d = ImageDraw.Draw(img)
    rounded_rect(d, [3, 4, w - 3, h - 4], 8, fill=color, outline=(40, 40, 40), width=2)
    d.rounded_rectangle([6, 8, w - 6, 18], radius=4, fill=(160, 210, 235, 230))  # windshield
    d.ellipse([2, h - 10, 9, h - 3], fill=(20, 20, 20))
    d.ellipse([w - 9, h - 10, w - 2, h - 3], fill=(20, 20, 20))
    return img


VEHICLES = {
    "car": make_car(),
    "bike": make_bike(),
    "bus": make_bus(),
    "truck": make_truck(),
    "rickshaw": make_rickshaw(),
}
for name, img in VEHICLES.items():
    img.save(os.path.join(OUT, f"{name}.png"))


# ---------------------------------------------------------------- SIGNALS
def make_signal(active):
    w, h = 36, 96
    img = new_canvas(w, h)
    d = ImageDraw.Draw(img)
    rounded_rect(d, [2, 2, w - 2, h - 2], 10, fill=(25, 25, 25), outline=(0, 0, 0), width=2)
    colors = {
        "red": (60, 20, 20),
        "yellow": (70, 60, 15),
        "green": (20, 55, 25),
    }
    bright = {"red": (230, 45, 45), "yellow": (240, 200, 40), "green": (60, 200, 90)}
    order = ["red", "yellow", "green"]
    for i, key in enumerate(order):
        cy = 20 + i * 28
        fill = bright[key] if key == active else colors[key]
        d.ellipse([8, cy - 11, w - 8, cy + 11], fill=fill, outline=(10, 10, 10), width=1)
    return img


for state in ["red", "yellow", "green"]:
    make_signal(state).save(os.path.join(OUT, "signals", f"{state}.png"))


# ---------------------------------------------------------------- BACKGROUND
def make_background(w=1000, h=700):
    img = Image.new("RGB", (w, h), (86, 140, 74))  # grass
    d = ImageDraw.Draw(img)
    road_w = 160
    cx, cy = w // 2, h // 2

    # horizontal & vertical roads (asphalt)
    d.rectangle([0, cy - road_w // 2, w, cy + road_w // 2], fill=(58, 58, 62))
    d.rectangle([cx - road_w // 2, 0, cx + road_w // 2, h], fill=(58, 58, 62))

    # lane dividers (dashed yellow center lines)
    dash, gap = 22, 16
    x = 0
    while x < w:
        if not (cx - road_w // 2 - 10 < x < cx + road_w // 2 + 10):
            d.rectangle([x, cy - 3, x + dash, cy + 3], fill=(235, 205, 60))
        x += dash + gap
    y = 0
    while y < h:
        if not (cy - road_w // 2 - 10 < y < cy + road_w // 2 + 10):
            d.rectangle([cx - 3, y, cx + 3, y + dash], fill=(235, 205, 60))
        y += dash + gap

    # lane boundary (white dashed) between the 2 lanes each side
    for offset in (-road_w // 4, road_w // 4):
        x = 0
        while x < w:
            if not (cx - road_w // 2 - 10 < x < cx + road_w // 2 + 10):
                d.rectangle([x, cy + offset - 2, x + 14, cy + offset + 2], fill=(230, 230, 230))
            x += 14 + 14
        y = 0
        while y < h:
            if not (cy - road_w // 2 - 10 < y < cy + road_w // 2 + 10):
                d.rectangle([cx + offset - 2, y, cx + offset + 2, y + 14], fill=(230, 230, 230))
            y += 14 + 14

    # stop lines (white) - 4 sides, offset from center by half road_w
    m = 8
    d.rectangle([cx - road_w // 2, cy - road_w // 2 - m - 6, cx, cy - road_w // 2 - m], fill=(240, 240, 240))
    d.rectangle([cx, cy + road_w // 2 + m, cx + road_w // 2, cy + road_w // 2 + m + 6], fill=(240, 240, 240))
    d.rectangle([cx + road_w // 2 + m, cy, cx + road_w // 2 + m + 6, cy + road_w // 2], fill=(240, 240, 240))
    d.rectangle([cx - road_w // 2 - m - 6, cy - road_w // 2, cx - road_w // 2 - m, cy], fill=(240, 240, 240))

    # zebra crossing marks
    def zebra_h(x0, x1, ypos):
        xx = x0
        while xx < x1:
            d.rectangle([xx, ypos, xx + 10, ypos + road_w], fill=(235, 235, 235))
            xx += 22

    def zebra_v(y0, y1, xpos):
        yy = y0
        while yy < y1:
            d.rectangle([xpos, yy, xpos + road_w, yy + 10], fill=(235, 235, 235))
            yy += 22

    # a few simple trees for decoration
    import random
    random.seed(7)
    for _ in range(26):
        tx = random.randint(20, w - 20)
        ty = random.randint(20, h - 20)
        # keep off the roads
        if abs(tx - cx) < road_w // 2 + 40 or abs(ty - cy) < road_w // 2 + 40:
            continue
        r = random.randint(10, 16)
        d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=(52, 105, 48))
        d.ellipse([tx - r + 3, ty - r + 3, tx + r - 5, ty + r - 5], fill=(66, 128, 60))

    return img


make_background().save(os.path.join(OUT, "intersection.png"))

print("All assets generated in", OUT)
