# Smart Traffic Signal — Adaptive System with AI Vehicle Detection

An adaptive (smart) traffic signal system for a 4-way intersection, built
with **Python**. It has two parts:

1. **AI Vehicle Detection** (`vehicle_detection.py`) — uses a pretrained
   **YOLOv8** object-detection model (Ultralytics) to detect and count real
   vehicles (car, bike, bus, truck) in a traffic photo.
2. **Pygame Simulation** (`simulation.py`) — a live animated 4-way
   intersection that demonstrates the adaptive signal-timing logic end to
   end (vehicles queue up, signal timers adjust automatically).

Both parts use the **same green-signal-time formula**, so the AI module is
a direct, working demonstration of "real" vehicle detection feeding the
same algorithm that drives the simulation.

Unlike a traditional traffic light that gives every direction the same
fixed green time, this system calculates the green-light duration for
each direction based on how many vehicles are waiting there — busier
directions automatically get more green time, within a minimum/maximum
limit so no direction is ever starved.

All simulation graphics (vehicles, signals, background) are custom-drawn
(see `generate_assets.py`) — no external/copyrighted images are used.

---

## The AI part — how it works

`vehicle_detection.py` loads a pretrained **YOLOv8n** model (this is a
real, published object-detection neural network, trained on the COCO
dataset — it recognizes cars, motorcycles, buses, and trucks out of the
box, no custom training needed). For each traffic photo you provide:

1. The model detects every vehicle and draws bounding boxes around them.
2. Vehicles are counted per class (car / bike / bus / truck).
3. Those counts are plugged into the same formula used by the algorithm:

   ```
   GreenTime = Σ (count_of_class × avg_crossing_time_of_class) / (lanes + 1)
   ```

   clipped between a minimum (10s) and maximum (60s).
4. The annotated image (with boxes) is saved, and the calculated green
   time is printed — this is the "Vehicle Detection Module" of the
   project, using a real, modern AI model instead of simulated counts.

This is much simpler to run than older YOLOv2/darkflow-based approaches:
`pip install ultralytics` is the only step — the model weights download
automatically the first time you run it (no manual download, no old
TensorFlow 1.x, no Python-version issues).

---

## Project structure

```
smart_traffic/
├── simulation.py          # Pygame simulation — adaptive signal demo
├── vehicle_detection.py   # AI module — real YOLOv8 vehicle detection
├── generate_assets.py     # (re)generates the simulation's images
├── requirements.txt
├── README.md
├── test_images/           # put your own traffic photos here
├── output_images/         # annotated detection results are saved here
└── images/
    ├── car.png, bike.png, bus.png, truck.png, rickshaw.png
    ├── intersection.png   # simulation background
    └── signals/red.png, yellow.png, green.png
```

---

## How to run

**1. Make sure Python 3.9–3.12 is installed** (YOLOv8/PyTorch don't yet
support brand-new Python versions like 3.13/3.14 — if `pip install` fails,
install Python 3.11 and use that instead).
```
python --version
```

**2. Install dependencies**
```
python -m pip install -r requirements.txt
```
(`ultralytics` will also pull in PyTorch and OpenCV — this download is a
few hundred MB and only happens once.)

**3a. Run the AI vehicle-detection module**
```
python vehicle_detection.py
```
- Put a few real traffic/road photos (`.jpg` / `.png`) inside
  `test_images/` first.
- Annotated images (with bounding boxes) are saved to `output_images/`.
- Vehicle counts and the calculated green signal time are printed for
  each image.

**3b. Run the live simulation**
```
python simulation.py
```
A window opens showing the 4-way intersection. Close the window or press
`Esc` to stop.

### If you want to regenerate the simulation's images
```
python -m pip install pillow
python generate_assets.py
```

---

## Notes for the report / presentation

- The **AI Vehicle Detection module** (`vehicle_detection.py`) is the real
  object-detection component: it uses YOLOv8, a genuine deep-learning
  model, to detect vehicles in actual photos — this satisfies the "AI
  must be used" requirement directly and verifiably (you can show the
  annotated output images with bounding boxes as proof).
- The **Simulation module** (`simulation.py`) demonstrates the adaptive
  signal-switching algorithm live and visually, using simulated vehicle
  counts (so it can run smoothly in real time without needing a live
  camera feed) — this is the same approach the original project report
  describes for its "Simulation Module".
- Both modules share the exact same green-time formula, showing that the
  AI module's real-world detections plug into the same algorithm driving
  the simulation.

