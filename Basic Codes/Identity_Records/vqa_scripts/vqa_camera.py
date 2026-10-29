import cv2
import subprocess
import time
import os

CAMERA = "/dev/video0"
IMAGE = "/tmp/vqa.jpg"

cap = cv2.VideoCapture(CAMERA)

if not cap.isOpened():
    print("ERROR: Could not open camera")
    exit(1)

# Set a modest resolution to keep capture fast
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("VQA camera started.")
print("Press Ctrl+C to stop.")

try:
    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to capture image")
            time.sleep(1)
            continue

        # Save current camera frame
        cv2.imwrite(IMAGE, frame)

        # Run SmolVLM
        command = [
            os.path.expanduser("~/llama.cpp/build/bin/llama-cli"),
            "-m",
            os.path.expanduser(
                "~/.cache/llama.cpp/ggml-org/SmolVLM-256M-Instruct-GGUF/SmolVLM-256M-Instruct-Q8_0.gguf"
            ),
            "--image",
            IMAGE,
            "-p",
            "What is the person doing? Answer with one short sentence.",
            "-n",
            "20",
            "--temp",
            "0.1",
            "-st",
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        print("\nMODEL OUTPUT:")
        print(result.stdout)

        # Wait before next image
        time.sleep(3)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    cap.release()
