from flask import Flask, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "actions.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():    
    conn = get_db()
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
    conn.commit()
    conn.close()

@app.route("/")
def index():
    with open(os.path.join(os.path.dirname(__file__), "dashboard.html"), encoding='utf-8') as f:
        return f.read()

@app.route("/api/actions")
def actions():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM actions ORDER BY start_time DESC LIMIT 200"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/stats")
def stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
    by_action = conn.execute(
        "SELECT action, COUNT(*) as count, SUM(duration) as total_duration, AVG(confidence) as avg_confidence "
        "FROM actions GROUP BY action ORDER BY count DESC"
    ).fetchall()
    latest = conn.execute(
        "SELECT action, confidence FROM actions ORDER BY start_time DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return jsonify({
        "total": total,
        "by_action": [dict(r) for r in by_action],
        "latest": dict(latest) if latest else None,
    })

if __name__ == "__main__":
    init_db()
    print("→ Dashboard running at http://localhost:5000")
    app.run(debug=True, port=5000)
