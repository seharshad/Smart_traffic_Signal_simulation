"""
Smart Traffic Signal - AI Vehicle Detection Module
----------------------------------------------------
This is the "AI" part of the project: it uses a pretrained YOLOv8 object
detection model (Ultralytics) to detect and count real vehicles (car,
motorcycle/bike, bus, truck) in traffic photos, then feeds those counts
into the SAME adaptive green-signal-time formula used by the Pygame
simulation (simulation.py). This shows the full pipeline described in the
project report:

    CCTV image  --(AI object detection)-->  vehicle counts
               --(signal-switching formula)-->  green signal time

Unlike the original darkflow/YOLOv2 approach, YOLOv8 here is installed
with a single `pip install ultralytics` and downloads its own pretrained
weights automatically on first run — no manual weight download, no old
TensorFlow 1.x, no Python-version headaches.

HOW TO USE
----------
1. Put a few real traffic photos (jpg/png) inside the `test_images/`
   folder next to this script (e.g. a photo of a road, junction, or
   traffic-heavy street).
2. Run:  python vehicle_detection.py
3. Annotated images (with bounding boxes + labels) are saved into
   `output_images/`, and vehicle counts + the calculated green signal
   time are printed to the terminal for each image.
"""

import os
import cv2
from ultralytics import YOLO

# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(BASE_DIR, "test_images")
OUT_DIR = os.path.join(BASE_DIR, "output_images")
os.makedirs(TEST_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# Map YOLO's COCO class names to our 4 vehicle categories
CLASS_MAP = {
    "car": "car",
    "motorcycle": "bike",
    "bus": "bus",
    "truck": "truck",
}
CONF_THRESHOLD = 0.35   # minimum confidence to count a detection

# Same constants used by the signal-switching algorithm in simulation.py,
# so the formula here is identical to the one driving the simulation.
AVG_CROSS_TIME = {"car": 2.0, "bike": 1.0, "bus": 2.5, "truck": 2.7}
NUM_LANES = 2
MIN_GREEN = 10
MAX_GREEN = 60


def compute_green_time(counts):
    """GST = sum(count_c * avgTime_c) / (numLanes + 1), clipped to [MIN,MAX]."""
    total = sum(counts.get(c, 0) * AVG_CROSS_TIME[c] for c in AVG_CROSS_TIME)
    gst = total / (NUM_LANES + 1)
    return max(MIN_GREEN, min(MAX_GREEN, round(gst) if gst > 0 else MIN_GREEN))


def detect_vehicles(model, image_path):
    """Runs YOLOv8 on one image. Returns (counts dict, path to annotated image)."""
    results = model.predict(image_path, conf=CONF_THRESHOLD, verbose=False)
    result = results[0]

    counts = {"car": 0, "bike": 0, "bus": 0, "truck": 0}
    for box in result.boxes:
        cls_name = model.names[int(box.cls[0])]
        if cls_name in CLASS_MAP:
            counts[CLASS_MAP[cls_name]] += 1

    annotated = result.plot()  # numpy array (BGR) with boxes + labels drawn
    out_path = os.path.join(OUT_DIR, os.path.basename(image_path))
    cv2.imwrite(out_path, annotated)

    return counts, out_path


def main():
    images = [
        f for f in sorted(os.listdir(TEST_DIR))
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not images:
        print(f"No images found in: {TEST_DIR}")
        print("Add a few traffic photos (.jpg / .png) there and run this again.")
        return

    print("Loading YOLOv8 model (weights download automatically on first run)...")
    model = YOLO("yolov8n.pt")

    print(f"\nFound {len(images)} image(s). Running detection...\n")
    for img_name in images:
        img_path = os.path.join(TEST_DIR, img_name)
        counts, out_path = detect_vehicles(model, img_path)
        total = sum(counts.values())
        green_time = compute_green_time(counts)

        print(f"--- {img_name} ---")
        print(f"  Detected -> car: {counts['car']}, bike: {counts['bike']}, "
              f"bus: {counts['bus']}, truck: {counts['truck']}  (total: {total})")
        print(f"  Adaptive Green Signal Time for this lane = {green_time} seconds")
        print(f"  Annotated image saved to: {out_path}\n")


if __name__ == "__main__":
    main()
