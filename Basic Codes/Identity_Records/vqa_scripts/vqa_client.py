import cv2
import requests
import base64
import time
from datetime import datetime

CAMERA = "/dev/video0"
SERVER = "http://127.0.0.1:8080/v1/chat/completions"

cap = cv2.VideoCapture(CAMERA)

if not cap.isOpened():
    print("Could not open camera")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("VQA started. Press Ctrl+C to stop.")

try:
    while True:

        # Capture frame
        ret, frame = cap.read()

        if not ret:
            print("Camera capture failed")
            continue

        # Save JPEG
        _, jpeg = cv2.imencode(".jpg", frame)

        # Convert image to base64
        image_data = base64.b64encode(jpeg.tobytes()).decode("utf-8")

        # Send to VLM
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is the person doing? Answer with one short sentence."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 20,
            "temperature": 0.1
        }

        try:
            response = requests.post(
                SERVER,
                json=payload,
                timeout=30
            )

            result = response.json()

            answer = result["choices"][0]["message"]["content"].strip()

            timestamp = datetime.now().strftime("%H:%M:%S")

            print(f"[{timestamp}] {answer}")

        except Exception as e:
            print("VLM error:", e)

        # Wait 3 seconds
        time.sleep(3)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    cap.release()
