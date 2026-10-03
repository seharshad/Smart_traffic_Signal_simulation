"""
Smart Traffic Signal - Simulation Module
-----------------------------------------
An adaptive traffic-signal simulation for a 4-way intersection, built with
Pygame. Instead of the fixed (static) timer used by traditional signals,
the green-light duration for each direction is calculated from the number
of vehicles waiting in that direction, so busier directions get more green
time (within a minimum/maximum limit to avoid starving any direction).

This is a self-contained simulation: vehicle counts are taken directly from
the simulated lanes (instead of a real camera + YOLO pipeline), which makes
the project easy to run anywhere with just `pip install pygame`.

Run with:  python simulation.py
"""

import os
import sys
import math
import random
import pygame

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 1000, 700
CX, CY = SCREEN_W // 2, SCREEN_H // 2
ROAD_W = 160

LANE_MAIN_OFFSET = 20   # car / bus / truck / rickshaw lane (closer to center line)
LANE_BIKE_OFFSET = 60   # bike-only lane (outer lane)

GAP = 12                 # minimum gap (px) kept between two vehicles in a lane
SPAWN_INTERVAL = 0.7      # seconds between new vehicle spawns
YELLOW_TIME = 5           # seconds
MIN_GREEN = 10            # seconds
MAX_GREEN = 60            # seconds
DEFAULT_GREEN = 20        # seconds (used for the very first cycle)
NUM_LANES = 2             # per direction, used in the GST formula

# Average time (seconds) each vehicle class takes to clear the intersection.
# Used only inside the green-time formula (not the animation speed).
AVG_CROSS_TIME = {
    "car": 2.0,
    "bike": 1.0,
    "bus": 2.5,
    "truck": 2.7,
    "rickshaw": 2.2,
}

# Animation speed (pixels / second) per vehicle class.
SPEED = {
    "car": 95,
    "bike": 115,
    "bus": 55,
    "truck": 58,
    "rickshaw": 88,
}

# Which vehicle types can appear in which lane.
MAIN_LANE_TYPES = ["car", "car", "car", "bus", "truck", "rickshaw"]  # weighted
BIKE_LANE_TYPES = ["bike"]

DIRECTIONS = ["right", "down", "left", "up"]   # cyclic order of the signals
ROTATION = {"up": 0, "down": 180, "right": -90, "left": 90}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "images")


# --------------------------------------------------------------------------
# GEOMETRY HELPERS
# --------------------------------------------------------------------------
def lane_center(direction, lane_key):
    """Fixed coordinate on the cross-axis (the axis the vehicle does NOT
    travel along) for a given direction + lane."""
    off = LANE_MAIN_OFFSET if lane_key == "main" else LANE_BIKE_OFFSET
    if direction == "right":
        return CY + off
    if direction == "left":
        return CY - off
    if direction == "down":
        return CX + off
    if direction == "up":
        return CX - off


def stop_line(direction):
    """Coordinate on the travel-axis where a vehicle must stop for red/yellow."""
    if direction == "right":
        return CX - ROAD_W // 2 - 4
    if direction == "left":
        return CX + ROAD_W // 2 + 4
    if direction == "down":
        return CY - ROAD_W // 2 - 4
    if direction == "up":
        return CY + ROAD_W // 2 + 4


def travel_sign(direction):
    return 1 if direction in ("right", "down") else -1


def spawn_pos(direction, length):
    if direction == "right":
        return -length
    if direction == "left":
        return SCREEN_W + length
    if direction == "down":
        return -length
    if direction == "up":
        return SCREEN_H + length


def is_offscreen(direction, pos, length):
    if direction == "right":
        return pos - length / 2 > SCREEN_W
    if direction == "left":
        return pos + length / 2 < 0
    if direction == "down":
        return pos - length / 2 > SCREEN_H
    if direction == "up":
        return pos + length / 2 < 0


# --------------------------------------------------------------------------
# VEHICLE
# --------------------------------------------------------------------------
class Vehicle:
    def __init__(self, vtype, direction, lane_key, base_size, image):
        self.type = vtype
        self.direction = direction
        self.lane_key = lane_key
        self.speed = SPEED[vtype]
        self.length = base_size[1]     # length along the travel axis
        self.width = base_size[0]      # width across the lane
        self.image = image
        self.crossed = False

        sign = travel_sign(direction)
        self.pos = spawn_pos(direction, self.length)   # travel-axis coordinate
        self.progress = self.pos * sign                # monotonically increasing

    def cross_axis_coord(self):
        return lane_center(self.direction, self.lane_key)

    def rect_center(self):
        if self.direction in ("right", "left"):
            return (self.pos, self.cross_axis_coord())
        else:
            return (self.cross_axis_coord(), self.pos)

    def update(self, dt, ahead, signal_is_green):
        sign = travel_sign(self.direction)
        desired_progress = self.progress + self.speed * dt

        if ahead is not None:
            max_progress = ahead.progress - (GAP + (self.length + ahead.length) / 2)
            desired_progress = min(desired_progress, max_progress)

        stop_progress = stop_line(self.direction) * sign - self.length / 2
        if not self.crossed and not signal_is_green:
            # Not allowed to pass yet -> clamp exactly at the stop line.
            desired_progress = min(desired_progress, stop_progress)

        self.progress = max(self.progress, desired_progress)
        self.pos = self.progress * sign

        # Only mark as crossed once it has actually moved PAST the stop
        # line (strictly, with a small margin). This can only happen when
        # the signal is green (or it had already crossed before) — a red
        # signal clamps progress to exactly stop_progress, so the vehicle
        # stays correctly stopped instead of being falsely marked crossed.
        if not self.crossed and self.progress > stop_progress + 0.5:
            self.crossed = True

    def draw(self, screen):
        cx, cy = self.rect_center()
        rect = self.image.get_rect(center=(cx, cy))
        screen.blit(self.image, rect)


# --------------------------------------------------------------------------
# TRAFFIC SIGNAL MANAGER
# --------------------------------------------------------------------------
class SignalController:
    """Implements the adaptive cyclic signal-switching logic."""

    def __init__(self):
        self.green_time = {d: DEFAULT_GREEN for d in DIRECTIONS}
        self.current_idx = 0
        self.state = "GREEN"          # GREEN -> YELLOW -> (next) GREEN ...
        self.timer = self.green_time[DIRECTIONS[0]]
        self.decision_made_for_next = False

    def current_direction(self):
        return DIRECTIONS[self.current_idx]

    def next_direction(self):
        return DIRECTIONS[(self.current_idx + 1) % len(DIRECTIONS)]

    def signal_state_for(self, direction):
        if direction == self.current_direction():
            return self.state          # "GREEN" or "YELLOW"
        return "RED"

    def update(self, dt, waiting_counts_fn):
        self.timer -= dt
        if self.timer > 0:
            return

        if self.state == "GREEN":
            # Switch to yellow, and calculate green time for the NEXT signal
            # now -- exactly like a real system would process the captured
            # image during the yellow-light interval.
            self.state = "YELLOW"
            self.timer = YELLOW_TIME
            counts = waiting_counts_fn(self.next_direction())
            self.green_time[self.next_direction()] = compute_green_time(counts)

        elif self.state == "YELLOW":
            self.current_idx = (self.current_idx + 1) % len(DIRECTIONS)
            self.state = "GREEN"
            self.timer = self.green_time[self.current_direction()]


def compute_green_time(counts):
    """Green Signal Time = sum(count_c * avgTime_c) / (numLanes + 1),
    clipped to [MIN_GREEN, MAX_GREEN]."""
    total = sum(counts.get(c, 0) * AVG_CROSS_TIME[c] for c in AVG_CROSS_TIME)
    gst = total / (NUM_LANES + 1)
    return max(MIN_GREEN, min(MAX_GREEN, round(gst) if gst > 0 else MIN_GREEN))


# --------------------------------------------------------------------------
# ASSET LOADING
# --------------------------------------------------------------------------
def load_assets():
    base_images = {}
    base_sizes = {}
    for vtype in AVG_CROSS_TIME:
        img = pygame.image.load(os.path.join(IMG_DIR, f"{vtype}.png")).convert_alpha()
        base_images[vtype] = img
        base_sizes[vtype] = img.get_size()

    rotated = {d: {} for d in DIRECTIONS}
    for d in DIRECTIONS:
        for vtype, img in base_images.items():
            rotated[d][vtype] = pygame.transform.rotate(img, ROTATION[d])

    signal_imgs = {
        s: pygame.image.load(os.path.join(IMG_DIR, "signals", f"{s}.png")).convert_alpha()
        for s in ("red", "yellow", "green")
    }

    background = pygame.image.load(os.path.join(IMG_DIR, "intersection.png")).convert()

    return base_sizes, rotated, signal_imgs, background


SIGNAL_SCREEN_POS = {
    # RIGHT road -> signal ABOVE the right (west) arm
    "right": (260, 150),
    # LEFT road -> signal ABOVE the left (east) arm
    "left":  (600, 150),
    # DOWN road -> signal to the LEFT of the down (north) arm
    "down":  (374, 130),
    # UP road -> signal to the LEFT of the up (south) arm
    "up":    (374, 550),
}
DIRECTION_LABELS = {
    "right": "RIGHT",
    "left": "LEFT",
    "down": "DOWN",
    "up": "UP",
}


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Smart Traffic Signal - Simulation")
    clock = pygame.time.Clock()

    base_sizes, rotated_images, signal_imgs, background = load_assets()

    font = pygame.font.SysFont("arial", 20, bold=True)
    small_font = pygame.font.SysFont("arial", 15)

    lanes = {(d, lane): [] for d in DIRECTIONS for lane in ("main", "bike")}
    crossed_count = {d: 0 for d in DIRECTIONS}

    controller = SignalController()

    elapsed = 0.0
    time_since_spawn = 0.0

    def waiting_counts(direction):
        counts = {c: 0 for c in AVG_CROSS_TIME}
        for lane_key in ("main", "bike"):
            for v in lanes[(direction, lane_key)]:
                if not v.crossed:
                    counts[v.type] += 1
        return counts

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        elapsed += dt
        time_since_spawn += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # ---------------- spawn new vehicles ----------------
        if time_since_spawn >= SPAWN_INTERVAL:
            time_since_spawn = 0.0
            direction = random.choice(DIRECTIONS)
            lane_key = "bike" if random.random() < 0.25 else "main"
            vtype = random.choice(BIKE_LANE_TYPES if lane_key == "bike" else MAIN_LANE_TYPES)
            image = rotated_images[direction][vtype]
            v = Vehicle(vtype, direction, lane_key, base_sizes[vtype], image)
            lanes[(direction, lane_key)].append(v)

        # ---------------- signal logic ----------------
        controller.update(dt, waiting_counts)

        # ---------------- move vehicles ----------------
        for (direction, lane_key), vlist in lanes.items():
            is_green = controller.signal_state_for(direction) == "GREEN"
            ahead = None
            for v in vlist:
                v.update(dt, ahead, is_green)
                ahead = v

            # remove vehicles that left the screen, counting them
            still_on_screen = []
            for v in vlist:
                if is_offscreen(direction, v.pos, v.length):
                    if v.crossed:
                        crossed_count[direction] += 1
                else:
                    still_on_screen.append(v)
            lanes[(direction, lane_key)] = still_on_screen

        # ---------------- draw ----------------
        screen.blit(background, (0, 0))

        for vlist in lanes.values():
            for v in vlist:
                v.draw(screen)

        for direction in DIRECTIONS:
            state = controller.signal_state_for(direction)
            img_key = "green" if state == "GREEN" else "yellow" if state == "YELLOW" else "red"
            pos = SIGNAL_SCREEN_POS[direction]
            screen.blit(signal_imgs[img_key], pos)

            # countdown number (only meaningful for the active + next-up signal)
            if direction == controller.current_direction():
                label = f"{max(0, math.ceil(controller.timer))}"
            elif direction == controller.next_direction() and controller.state == "YELLOW":
                label = f"{controller.green_time[direction]}"
            else:
                label = state

            text = small_font.render(label, True, (255, 255, 255))
            screen.blit(text, (pos[0] + 2, pos[1] - 20))

            dir_label = small_font.render(DIRECTION_LABELS[direction], True, (255, 255, 0))
            screen.blit(dir_label, (pos[0] - 2, pos[1] - 38))

            count_text = small_font.render(f"Crossed: {crossed_count[direction]}", True, (20, 20, 20))
            screen.blit(count_text, (pos[0] - 6, pos[1] + 100))

        # top bar
        pygame.draw.rect(screen, (255, 255, 255), (0, 0, SCREEN_W, 34))
        title = font.render("Smart Traffic Signal - Adaptive Simulation", True, (30, 30, 30))
        screen.blit(title, (10, 6))
        elapsed_text = font.render(f"Time Elapsed: {int(elapsed)}s", True, (30, 30, 30))
        screen.blit(elapsed_text, (SCREEN_W - elapsed_text.get_width() - 10, 6))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
