from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import random
import functools
import os

app = Flask(__name__, template_folder='html', static_folder='static')
CORS(app)
app.secret_key = "monitopro_secret_2024"

client = MongoClient(os.environ.get("MONGO_URL", "mongodb+srv://kazimjf06_db_user:kazimjafri6@@cluster0.7mwov7w.mongodb.net/monitoring_db?appName=Cluster0"))
db = client["monitoring_db"]

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# ─── Login Required Decorator ─────────────────────────
def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── Auth Routes ──────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Pages (Protected) ────────────────────────────────
@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/alerts")
@login_required
def alerts_page():
    return render_template("alerts.html")

@app.route("/about")
@login_required
def about_page():
    return render_template("about.html")

@app.route("/history")
@login_required
def history_page():
    return render_template("history.html")

# ─── API: Metrics ─────────────────────────────────────
@app.route("/api/metrics")
@login_required
def get_metrics():
    data = {
        "cpu": random.randint(20, 40),
        "response_time": random.randint(100, 140),
        "error_rate": round(random.uniform(0.1, 0.5), 1),
        "timestamp": datetime.now().isoformat()
    }
    db.metrics.insert_one(dict(data))
    return jsonify(data)

# ─── API: Logs ────────────────────────────────────────
@app.route("/api/logs")
@login_required
def get_logs():
    logs = list(db.logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(20))
    return jsonify(logs)

# ─── API: Alerts ──────────────────────────────────────
@app.route("/api/alerts")
@login_required
def get_alerts():
    alerts = list(db.alerts.find({}, {"_id": 0}).sort("timestamp", -1).limit(20))
    return jsonify(alerts)

# ─── API: Fault History ───────────────────────────────
@app.route("/api/fault-history")
@login_required
def get_fault_history():
    faults = list(db.fault_history.find({}, {"_id": 0}).sort("timestamp", -1))
    return jsonify(faults)

# ─── API: Inject Fault ────────────────────────────────
@app.route("/api/inject", methods=["POST"])
@login_required
def inject_fault():
    body = request.get_json() or {}
    fault_type = body.get("fault_type", "null_pointer")
    now = datetime.now().isoformat()

    fault_map = {
        "null_pointer": {
            "label": "Null Pointer Exception",
            "logs": [
                ("ERROR",   "NullPointerException in UserService.java:142"),
                ("WARNING", "DB connection pool near limit (90%)"),
                ("ERROR",   "HTTP 500 — /api/checkout failed"),
            ],
            "alert": "ALERT: NullPointerException — error rate 18%",
            "cpu": random.randint(85, 95),
            "response_time": random.randint(700, 900),
            "error_rate": round(random.uniform(15, 20), 1),
        },
        "memory_leak": {
            "label": "Memory Leak",
            "logs": [
                ("WARNING", "Heap memory usage at 88% — possible leak"),
                ("WARNING", "GC overhead limit exceeded"),
                ("ERROR",   "OutOfMemoryError: Java heap space"),
            ],
            "alert": "ALERT: Memory usage critical — possible memory leak",
            "cpu": random.randint(70, 85),
            "response_time": random.randint(500, 700),
            "error_rate": round(random.uniform(8, 14), 1),
        },
        "db_down": {
            "label": "Database Down",
            "logs": [
                ("ERROR",   "Cannot connect to MongoDB: Connection refused"),
                ("ERROR",   "Retrying DB connection (attempt 1/3)"),
                ("ERROR",   "All DB retries failed — service unavailable"),
            ],
            "alert": "ALERT: Database unreachable — all queries failing",
            "cpu": random.randint(30, 50),
            "response_time": random.randint(3000, 5000),
            "error_rate": round(random.uniform(80, 99), 1),
        },
        "network_timeout": {
            "label": "Network Timeout",
            "logs": [
                ("WARNING", "API response time > 2000ms threshold"),
                ("ERROR",   "Gateway timeout: /api/payment service"),
                ("ERROR",   "Circuit breaker OPEN — too many failures"),
            ],
            "alert": "ALERT: Network timeout — payment service unreachable",
            "cpu": random.randint(60, 75),
            "response_time": random.randint(2000, 4000),
            "error_rate": round(random.uniform(20, 40), 1),
        },
    }

    f = fault_map.get(fault_type, fault_map["null_pointer"])

    for level, msg in f["logs"]:
        db.logs.insert_one({"level": level, "message": msg, "timestamp": now})

    db.alerts.insert_one({
        "message": f["alert"],
        "severity": "critical",
        "fault_type": f["label"],
        "timestamp": now
    })

    db.fault_history.insert_one({
        "fault_type": f["label"],
        "detected_in_seconds": random.randint(1, 4),
        "resolved_in_seconds": random.randint(5, 12),
        "timestamp": now,
        "status": "resolved"
    })

    return jsonify({
        "status": "fault injected",
        "fault_type": f["label"],
        "cpu": f["cpu"],
        "response_time": f["response_time"],
        "error_rate": f["error_rate"],
        "time": now
    })

# ─── API: Reset ───────────────────────────────────────
@app.route("/api/reset", methods=["POST"])
@login_required
def reset():
    db.logs.delete_many({})
    db.alerts.delete_many({})
    db.metrics.delete_many({})
    return jsonify({"status": "reset done"})

if __name__ == "__main__":
    app.run(debug=True)