import cv2
import sqlite3
import threading
from collections import deque, Counter
from datetime import datetime
from PIL import Image
import torch
import os
from transformers import BlipProcessor, BlipForQuestionAnswering

# ---------------- VQA MODEL SETUP ----------------
MODEL_ID = "Salesforce/blip-vqa-base"

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"→ Loading BLIP on {device.upper()} ...")
processor = BlipProcessor.from_pretrained(MODEL_ID)
model = BlipForQuestionAnswering.from_pretrained(MODEL_ID).to(device)
model.eval()
print("→ Model ready.")

_vqa_lock = threading.Lock()
_vqa_result = ("unknown", 0.0)
_vqa_busy = False
_action_buffer = deque(maxlen=5)


def _run_vqa(pil_img: Image.Image) -> None:
    global _vqa_result, _vqa_busy
    inputs = processor(pil_img, "What is the person doing?", return_tensors="pt").to(device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=12)
    raw = processor.decode(out[0], skip_special_tokens=True).strip().lower()

    _action_buffer.append(raw)
    top, count = Counter(_action_buffer).most_common(1)[0]
    conf = round(count / len(_action_buffer), 2)

    with _vqa_lock:
        _vqa_result = (top, conf)
    _vqa_busy = False


def vqa_action(frame, frame_idx: int, sample_every: int = 10):
    global _vqa_busy
    if frame_idx % sample_every == 0 and not _vqa_busy:
        _vqa_busy = True
        pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        threading.Thread(target=_run_vqa, args=(pil_img,), daemon=True).start()
    with _vqa_lock:
        return _vqa_result


# ---------------- DB SETUP ----------------
db_path = os.path.join(os.path.dirname(__file__), "actions.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration REAL,
    location TEXT DEFAULT 'room_1',
    confidence REAL
)
""")
conn.commit()

# ---------------- CV SETUP ----------------
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

# Set format and warm up (first frames are often black)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
for _ in range(10):
    cap.read()

current_action = None
start_time = None
confidence = 0.0
frame_idx = 0

# ---------------- MAIN LOOP ----------------
print("→ Press Ctrl+C to stop.")
try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        action, confidence = vqa_action(frame, frame_idx, sample_every=10)
        frame_idx += 1
        now = datetime.now()

        if current_action != action:
            if current_action is not None:
                end_time = now
                duration = (end_time - start_time).total_seconds()
                cursor.execute("""
                    INSERT INTO actions (action, start_time, end_time, duration, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """, (current_action, start_time.isoformat(sep=' '), end_time.isoformat(sep=' '), duration, confidence))
                conn.commit()
                print(f"  [{end_time.strftime('%H:%M:%S')}] {current_action}  ({duration:.1f}s, conf={confidence})")

            current_action = action
            start_time = now
            print(f"→ {action}", flush=True)

except KeyboardInterrupt:
    pass

# ---------------- SAVE LAST ACTION ----------------
if current_action is not None:
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    cursor.execute("""
        INSERT INTO actions (action, start_time, end_time, duration, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (current_action, start_time.isoformat(sep=' '), end_time.isoformat(sep=' '), duration, confidence))
    conn.commit()

# ---------------- PRINT DB ----------------
print("\n--- Recorded Actions ---\n")
cursor.execute("SELECT * FROM actions ORDER BY start_time DESC LIMIT 20")
for row in cursor.fetchall():
    print(f"ID:{row[0]}  action={row[1]}  dur={row[4]:.2f}s  conf={row[6]}  loc={row[5]}")
    print(f"  start={row[2]}  end={row[3]}\n  ----")

# ---------------- CLEANUP ----------------
cap.release()
conn.close()
