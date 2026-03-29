import cv2
import sqlite3
from datetime import datetime, timedelta

# ---------------- DB SETUP ----------------
conn = sqlite3.connect("actions.db")
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

# Optional: clear old data for clean testing
cursor.execute("DELETE FROM actions")
conn.commit()

# ---------------- CV SETUP ----------------
cap = cv2.VideoCapture(0)

current_action = None
start_time = None

def dummy_action_detector(frame):
    # Replace later
    return "sitting", 0.9

# ---------------- TIMER ----------------
record_duration = 10  # seconds
start_recording = datetime.now()

# ---------------- MAIN LOOP ----------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    action, confidence = dummy_action_detector(frame)
    now = datetime.now()

    # Stop after 10 seconds
    if (now - start_recording).total_seconds() > record_duration:
        break

    # Detect action change
    if current_action != action:

        # Save previous action
        if current_action is not None:
            end_time = now
            duration = (end_time - start_time).total_seconds()

            cursor.execute("""
                INSERT INTO actions (action, start_time, end_time, duration, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (current_action, start_time, end_time, duration, confidence))
            conn.commit()

        # Start new action
        current_action = action
        start_time = now

    # Display
    cv2.putText(frame, f"Action: {action}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Feed", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

# ---------------- SAVE LAST ACTION ----------------
if current_action is not None:
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    cursor.execute("""
        INSERT INTO actions (action, start_time, end_time, duration, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (current_action, start_time, end_time, duration, confidence))
    conn.commit()

# ---------------- PRINT DB ----------------
print("\n--- Recorded Actions ---\n")

cursor.execute("SELECT * FROM actions")
rows = cursor.fetchall()

for row in rows:
    print(f"""
ID: {row[0]}
Action: {row[1]}
Start: {row[2]}
End: {row[3]}
Duration: {row[4]:.2f}s
Location: {row[5]}
Confidence: {row[6]}
-------------------------
""")

# ---------------- CLEANUP ----------------
cap.release()
cv2.destroyAllWindows()
conn.close()