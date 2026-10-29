"""
Person action logger: camera -> vision model -> one action word -> actions.db -> dashboard.

Run (from Identity_Records):
    python3 main_vqa/main_vqa.py                       # live camera, logs to actions.db
    python3 main_vqa/main_vqa.py --image x.jpg         # one image, prints the action
    python3 main_vqa/main_vqa.py --prompt list          # alternative prompt style
Dashboard:
    python3 server.py  ->  http://localhost:5000

Starts llama-server itself (downloading the model the first time) and stops it on exit.
"""
import argparse
import base64
import os
import sqlite3
import subprocess
import threading
import time
from collections import Counter, deque
from datetime import datetime

import cv2
import requests

from action_words import ACTIONS, to_one_word

# ---------------- CONFIG ----------------
LLAMA_SERVER = os.path.expanduser("~/llama.cpp/build/bin/llama-server")
DEFAULT_MODEL = "ggml-org/LFM2-VL-450M-GGUF"  # best speed/accuracy on the Pi (see CHECKLIST.md)
DEFAULT_PORT = 8080

# Shared with main.py and server.py (one folder up)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "actions.db")

CAMERA_INDEX = 0
SAMPLE_SECONDS = 3  # how often to ask the model
MIN_SECONDS = 2  # actions shorter than this are vote flicker, not saved

# Two prompt styles. "list" asks for one word from our list; "describe" asks for a short
# sentence and lets action_words.to_one_word pick the word (works better for bigger models).
PROMPTS = {
    "list": (
        "What is the person doing? Answer with exactly one word from this list: "
        + ", ".join(ACTIONS)
        + ". If there is no person, answer: none."
    ),
    "describe": "Describe what the person in this photo is doing in one short sentence.",
}
DEFAULT_PROMPT = "describe"
CONTEXT_SIZE = 4096  # cap the context; some models default to huge contexts and run out of RAM


# ---------------- MODEL SERVER ----------------
class ModelServer:
    """Runs llama-server for one vision model and talks to it."""

    def __init__(self, model: str = DEFAULT_MODEL, port: int = DEFAULT_PORT, prompt: str = DEFAULT_PROMPT):
        self.model = model
        self.port = port
        self.question = PROMPTS[prompt]
        self.url = f"http://127.0.0.1:{port}"
        self.proc = None

    def ready(self) -> bool:
        try:
            return requests.get(f"{self.url}/health", timeout=2).status_code == 200
        except requests.RequestException:
            return False

    def start(self, timeout_s: int = 1800, log_path: str = os.devnull):
        """Start llama-server unless one is already running on this port.
        The first start of a model downloads it, hence the long timeout."""
        if self.ready():
            print(f"→ Using llama-server already running on port {self.port}")
            return self
        print(f"→ Starting llama-server with {self.model} ...")
        log = open(log_path, "w")
        self.proc = subprocess.Popen(
            [LLAMA_SERVER, "-hf", self.model, "--port", str(self.port), "-c", str(CONTEXT_SIZE)],
            stdout=log, stderr=subprocess.STDOUT,
        )
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"llama-server exited during startup ({self.model}). See {log_path}")
            if self.ready():
                print("→ Model ready.")
                return self
            time.sleep(1)
        self.stop()
        raise RuntimeError(f"llama-server did not become ready in {timeout_s}s")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

    def ask(self, jpeg_bytes: bytes) -> str:
        """Send a JPEG to the model and return its raw reply."""
        image_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
        payload = {
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": self.question},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }],
            "max_tokens": 30,  # small models answer in a sentence; give room to reach the verb
            "temperature": 0.1,
        }
        resp = requests.post(f"{self.url}/v1/chat/completions", json=payload, timeout=180)
        return resp.json()["choices"][0]["message"]["content"].strip()

    def classify_image_file(self, path: str):
        """Return (action word, raw reply) for an image file."""
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Cannot read image: {path}")
        ok, jpeg = cv2.imencode(".jpg", img)
        raw = self.ask(jpeg.tobytes())
        return to_one_word(raw), raw


# ---------------- LIVE TRACKING ----------------
class ActionTracker:
    """Samples frames in a background thread and smooths answers with a 5-vote majority."""

    def __init__(self, server: ModelServer):
        self.server = server
        self.lock = threading.Lock()
        self.result = ("unknown", 0.0)
        self.raw_for = {}  # action word -> latest model sentence that gave it
        self.busy = False
        self.last_sample = 0.0
        self.buffer = deque(maxlen=5)

    def _run(self, jpeg_bytes: bytes) -> None:
        try:
            raw = self.server.ask(jpeg_bytes)
            word = to_one_word(raw)
            self.buffer.append(word)
            top, count = Counter(self.buffer).most_common(1)[0]
            with self.lock:
                self.result = (top, round(count / len(self.buffer), 2))
                self.raw_for[word] = raw
        except Exception as e:
            print("VLM error:", e)
        finally:
            self.busy = False

    def update(self, frame):
        """Returns (action, confidence)."""
        now = time.time()
        if now - self.last_sample >= SAMPLE_SECONDS and not self.busy:
            ok, jpeg = cv2.imencode(".jpg", frame)
            if ok:
                self.busy = True
                self.last_sample = now
                threading.Thread(target=self._run, args=(jpeg.tobytes(),), daemon=True).start()
        with self.lock:
            return self.result

    def sentence_for(self, action):
        """The latest model sentence that produced this action word."""
        with self.lock:
            return self.raw_for.get(action)


# ---------------- DATABASE ----------------
def open_db(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    conn.execute("""
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
    # Extra columns for the VLM logger; old rows keep NULL, dashboard is unaffected
    existing = {row[1] for row in conn.execute("PRAGMA table_info(actions)")}
    for col in ("raw_text", "model"):
        if col not in existing:
            conn.execute(f"ALTER TABLE actions ADD COLUMN {col} TEXT")
    conn.commit()
    return conn


def save_action(conn, action, start, end, conf, raw_text=None, model=None):
    duration = (end - start).total_seconds()
    if action in ("unknown", "none") or duration < MIN_SECONDS:  # startup, empty room, flicker
        return
    conn.execute(
        "INSERT INTO actions (action, start_time, end_time, duration, confidence, raw_text, model) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (action, start.isoformat(sep=" "), end.isoformat(sep=" "), duration, conf, raw_text, model),
    )
    conn.commit()
    print(f"  [{end.strftime('%H:%M:%S')}] {action}  ({duration:.1f}s, conf={conf})  \"{raw_text}\"")


# ---------------- LIVE CAMERA LOOP ----------------
def run_camera(server: ModelServer):
    conn = open_db()
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera {CAMERA_INDEX}")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    for _ in range(10):  # first frames are often black
        cap.read()

    tracker = ActionTracker(server)
    current_action, start_time, current_conf = None, None, 0.0

    print("→ Press Ctrl+C to stop.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera capture failed")
                break

            action, confidence = tracker.update(frame)
            now = datetime.now()
            if action != current_action:
                if current_action is not None:
                    save_action(conn, current_action, start_time, now, current_conf,
                                tracker.sentence_for(current_action), server.model)
                current_action, start_time = action, now
                print(f"→ {action}", flush=True)
            current_conf = confidence  # confidence of the action that is current right now

            time.sleep(0.03)
    except KeyboardInterrupt:
        pass
    finally:
        if current_action is not None:
            save_action(conn, current_action, start_time, datetime.now(), current_conf,
                        tracker.sentence_for(current_action), server.model)
        print("\n--- Recent Actions ---")
        for row in conn.execute(
            "SELECT id, action, duration, confidence, start_time FROM actions ORDER BY start_time DESC LIMIT 10"
        ):
            print(f"ID:{row[0]}  {row[1]:<11} {row[2]:6.1f}s  conf={row[3]}  start={row[4]}")
        cap.release()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Vision-model person action logger")
    parser.add_argument("--image", help="classify one image file instead of using the camera")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face GGUF repo for llama-server -hf")
    parser.add_argument("--prompt", choices=PROMPTS, default=DEFAULT_PROMPT)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = ModelServer(args.model, args.port, args.prompt).start()
    try:
        if args.image:
            action, raw = server.classify_image_file(args.image)
            print(f"{action}    (model said: \"{raw}\")")
        else:
            run_camera(server)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
