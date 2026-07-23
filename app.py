from flask import Flask, request, jsonify, render_template, session, redirect, url_for, Response
import sqlite3, secrets, time, base64, os, threading
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
SERVER_START = int(time.time())

# ── Email config (edit these) ──────────────────────────────
EMAIL_ENABLED  = True          # Set True after configuring
EMAIL_FROM     = "chapepralhad0@gmail.com"
EMAIL_TO       = "pralhad.1252070034@vit.edu"
EMAIL_PASSWORD = "pmua ejiv vhhp ymps"   # Gmail App Password

# ── DB ─────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def log_event(device_id, event, ip=None):
    conn = get_db()
    conn.execute("INSERT INTO logs (device_id,event,ip,timestamp) VALUES (?,?,?,?)",
                 (device_id, event, ip, int(time.time())))
    conn.commit(); conn.close()

# ── Email alert ────────────────────────────────────────────
def send_email_alert(subject, body):
    if not EMAIL_ENABLED: return
    def _send():
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"]    = EMAIL_FROM
            msg["To"]      = EMAIL_TO
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                s.login(EMAIL_FROM, EMAIL_PASSWORD)
                s.send_message(msg)
            print(f"[EMAIL] Sent: {subject}")
        except Exception as e:
            print(f"[EMAIL] Failed: {e}")
    threading.Thread(target=_send, daemon=True).start()

# ── Rate limiting ──────────────────────────────────────────
RATE_LIMIT = 5   # max requests
RATE_WINDOW = 60 # per 60 seconds

def is_rate_limited(device_id, ip):
    conn  = get_db()
    since = int(time.time()) - RATE_WINDOW
    count = conn.execute(
        "SELECT COUNT(*) as c FROM rate_limit WHERE (device_id=? OR ip=?) AND timestamp>?",
        (device_id, ip, since)
    ).fetchone()["c"]
    if count >= RATE_LIMIT:
        conn.close()
        return True
    conn.execute("INSERT INTO rate_limit VALUES (?,?,?)", (device_id, ip, int(time.time())))
    # Clean old entries
    conn.execute("DELETE FROM rate_limit WHERE timestamp < ?", (since,))
    conn.commit(); conn.close()
    return False

# ── Anomaly / auto block ───────────────────────────────────
def check_anomaly(device_id):
    conn = get_db()
    fails = conn.execute(
        "SELECT COUNT(*) as c FROM logs WHERE device_id=? AND event='AUTH_FAIL' AND timestamp>?",
        (device_id, int(time.time())-60)
    ).fetchone()["c"]
    if fails >= 3:
        conn.execute("UPDATE devices SET blocked=1 WHERE device_id=?", (device_id,))
        conn.commit()
        send_email_alert(
            f"[IoT Alert] Device {device_id} AUTO-BLOCKED",
            f"Device {device_id} has been automatically blocked after {fails} failed auth attempts in 60 seconds."
        )
    conn.close()

# ── Auth decorator ─────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════════════════
#   DASHBOARD ROUTES
# ══════════════════════════════════════════════════════════

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        conn = get_db()
        row  = conn.execute("SELECT password FROM admin WHERE username=?", (username,)).fetchone()
        conn.close()
        if row and row["password"] == password:
            session["logged_in"] = True
            session["username"]  = username
            return redirect(url_for("dashboard"))
        error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/device/<device_id>")
@login_required
def device_page(device_id):
    return render_template("device.html", device_id=device_id)

# ── API Stats ──────────────────────────────────────────────
@app.route("/api/stats")
@login_required
def api_stats():
    conn = get_db()
    now  = int(time.time())

    devices         = conn.execute("SELECT device_id,last_seen,blocked,nickname FROM devices").fetchall()
    active_sessions = conn.execute("SELECT device_id,token,expiry,created FROM sessions WHERE expiry>?", (now,)).fetchall()
    session_map     = {s["device_id"]: s for s in active_sessions}
    all_sessions    = conn.execute("SELECT device_id,token,expiry,created FROM sessions ORDER BY created DESC LIMIT 30").fetchall()

    logs = conn.execute("SELECT device_id,event,ip,timestamp FROM logs ORDER BY timestamp DESC LIMIT 50").fetchall()

    stats_row = conn.execute("""
        SELECT
          SUM(event='AUTH_SUCCESS')   as auth_success,
          SUM(event='AUTH_FAIL')      as auth_fail,
          SUM(event='DATA_ACCEPTED')  as data_packets,
          SUM(event='CHALLENGE_ISSUED') as challenges
        FROM logs
    """).fetchone()

    event_counts = {}
    for r in conn.execute("SELECT event,COUNT(*) as c FROM logs GROUP BY event").fetchall():
        event_counts[r["event"]] = r["c"]

    # Chart: last 20 auth events
    chart_events = conn.execute(
        "SELECT event,timestamp FROM logs WHERE event IN ('AUTH_SUCCESS','AUTH_FAIL') ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()

    # Hourly heatmap last 24h
    hourly = conn.execute(
        "SELECT strftime('%H',datetime(timestamp,'unixepoch','localtime')) as hr, COUNT(*) as c FROM logs WHERE timestamp>? GROUP BY hr",
        (now-86400,)
    ).fetchall()
    hourly_data = {r["hr"]: r["c"] for r in hourly}

    # Auth success rate over last 10 minutes (per minute)
    rate_data = []
    for i in range(10):
        t_start = now - (10-i)*60
        t_end   = now - (9-i)*60
        s = conn.execute("SELECT COUNT(*) as c FROM logs WHERE event='AUTH_SUCCESS' AND timestamp BETWEEN ? AND ?", (t_start,t_end)).fetchone()["c"]
        f = conn.execute("SELECT COUNT(*) as c FROM logs WHERE event='AUTH_FAIL'    AND timestamp BETWEEN ? AND ?", (t_start,t_end)).fetchone()["c"]
        rate_data.append({"success": s, "fail": f, "label": f"-{9-i}m"})

    # DB size
    db_size = os.path.getsize("database.db") if os.path.exists("database.db") else 0

    conn.close()

    device_list  = []
    online_count = 0
    for d in devices:
        last_seen   = d["last_seen"] or 0
        is_online   = (now - last_seen) < 30 and not d["blocked"]
        seconds_ago = now - last_seen if last_seen else None
        s           = session_map.get(d["device_id"])
        if is_online: online_count += 1

        if   seconds_ago is None:  lss = "Never"
        elif seconds_ago < 60:     lss = f"{seconds_ago}s ago"
        elif seconds_ago < 3600:   lss = f"{seconds_ago//60}m ago"
        else:                      lss = f"{seconds_ago//3600}h ago"

        tr  = max(0, s["expiry"]-now) if s else 0
        tpc = int((tr/300)*100) if tr > 0 else 0

        device_list.append({
            "device_id":       d["device_id"],
            "nickname":        d["nickname"] or d["device_id"],
            "status":          "Blocked" if d["blocked"] else ("Online" if is_online else "Offline"),
            "blocked":         bool(d["blocked"]),
            "last_seen_str":   lss,
            "last_seen_ago":   seconds_ago,
            "token_remaining": tr,
            "token_percent":   tpc,
        })

    uptime_sec = now - SERVER_START
    if   uptime_sec < 60:    uptime_str = f"{uptime_sec}s"
    elif uptime_sec < 3600:  uptime_str = f"{uptime_sec//60}m {uptime_sec%60}s"
    else:                    uptime_str = f"{uptime_sec//3600}h {(uptime_sec%3600)//60}m"

    return jsonify({
        "devices": device_list,
        "logs": [{"device_id":l["device_id"],"event":l["event"],"ip":l["ip"],
                  "timestamp":l["timestamp"],"time_str":time.strftime("%H:%M:%S",time.localtime(l["timestamp"]))} for l in logs],
        "sessions": [{"device_id":s["device_id"],"token":s["token"][:16]+"...","expiry":s["expiry"],
                      "created":s["created"],"active":s["expiry"]>now,
                      "created_str":time.strftime("%H:%M:%S",time.localtime(s["created"])) if s["created"] else "?",
                      "expiry_str": time.strftime("%H:%M:%S",time.localtime(s["expiry"]))} for s in all_sessions],
        "stats": {
            "total_devices":  len(devices),
            "online_devices": online_count,
            "auth_success":   stats_row["auth_success"]  or 0,
            "auth_fail":      stats_row["auth_fail"]      or 0,
            "data_packets":   stats_row["data_packets"]   or 0,
            "challenges":     stats_row["challenges"]     or 0,
        },
        "event_counts": event_counts,
        "chart_events": [{"event":e["event"],"timestamp":e["timestamp"]} for e in chart_events],
        "hourly_data":  hourly_data,
        "rate_data":    rate_data,
        "server": {
            "uptime":   uptime_str,
            "db_size":  f"{db_size/1024:.1f} KB",
            "time":     time.strftime("%H:%M:%S"),
        }
    })

# ── Device detail API ──────────────────────────────────────
@app.route("/api/device/<device_id>")
@login_required
def api_device(device_id):
    conn = get_db()
    now  = int(time.time())

    device = conn.execute("SELECT * FROM devices WHERE device_id=?", (device_id,)).fetchone()
    if not device:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    logs = conn.execute(
        "SELECT event,ip,timestamp FROM logs WHERE device_id=? ORDER BY timestamp DESC LIMIT 100",
        (device_id,)
    ).fetchall()

    sensor = conn.execute(
        "SELECT temperature,humidity,distance,timestamp FROM sensor_data WHERE device_id=? ORDER BY timestamp DESC LIMIT 50",
        (device_id,)
    ).fetchall()

    sessions = conn.execute(
        "SELECT token,expiry,created FROM sessions WHERE device_id=? ORDER BY created DESC LIMIT 10",
        (device_id,)
    ).fetchall()

    stats = conn.execute("""
        SELECT
          SUM(event='AUTH_SUCCESS') as ok,
          SUM(event='AUTH_FAIL')    as fail,
          SUM(event='DATA_ACCEPTED') as data
        FROM logs WHERE device_id=?
    """, (device_id,)).fetchone()

    sensor_latest = sensor[0] if sensor else None
    conn.close()

    last_seen   = device["last_seen"] or 0
    is_online   = (now - last_seen) < 30 and not device["blocked"]

    return jsonify({
        "device_id": device_id,
        "nickname":  device["nickname"] or device_id,
        "status":    "Blocked" if device["blocked"] else ("Online" if is_online else "Offline"),
        "blocked":   bool(device["blocked"]),
        "last_seen": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_seen)) if last_seen else "Never",
        "stats": {"auth_ok": stats["ok"] or 0, "auth_fail": stats["fail"] or 0, "data": stats["data"] or 0},
        "logs": [{"event":l["event"],"ip":l["ip"],"time":time.strftime("%H:%M:%S",time.localtime(l["timestamp"]))} for l in logs],
        "sensor": [{"temp":s["temperature"],"hum":s["humidity"],"dist":s["distance"],"time":time.strftime("%H:%M:%S",time.localtime(s["timestamp"]))} for s in sensor],
        "sensor_latest": {"temp":sensor_latest["temperature"],"hum":sensor_latest["humidity"],"dist":sensor_latest["distance"]} if sensor_latest else None,
        "sessions": [{"token":s["token"][:16]+"...","active":s["expiry"]>now,
                      "created":time.strftime("%H:%M:%S",time.localtime(s["created"])) if s["created"] else "?",
                      "expiry": time.strftime("%H:%M:%S",time.localtime(s["expiry"]))} for s in sessions],
    })

# ── Device management ──────────────────────────────────────
@app.route("/api/device/rename",  methods=["POST"])
@login_required
def rename_device():
    d = request.json
    conn = get_db()
    conn.execute("UPDATE devices SET nickname=? WHERE device_id=?", (d["nickname"].strip(), d["device_id"]))
    conn.commit(); conn.close()
    return jsonify({"status":"ok"})

@app.route("/api/device/delete",  methods=["POST"])
@login_required
def delete_device():
    d = request.json
    conn = get_db()
    conn.execute("DELETE FROM devices  WHERE device_id=?", (d["device_id"],))
    conn.execute("DELETE FROM sessions WHERE device_id=?", (d["device_id"],))
    conn.commit(); conn.close()
    log_event(d["device_id"], "DEVICE_DELETED", request.remote_addr)
    return jsonify({"status":"ok"})

@app.route("/api/device/unblock", methods=["POST"])
@login_required
def unblock_device():
    d = request.json
    conn = get_db()
    conn.execute("UPDATE devices SET blocked=0 WHERE device_id=?", (d["device_id"],))
    conn.commit(); conn.close()
    log_event(d["device_id"], "DEVICE_UNBLOCKED", request.remote_addr)
    return jsonify({"status":"ok"})

@app.route("/api/logs/export")
@login_required
def export_logs():
    conn = get_db()
    logs = conn.execute("SELECT device_id,event,ip,timestamp FROM logs ORDER BY timestamp DESC").fetchall()
    conn.close()
    csv = "device_id,event,ip,timestamp,datetime\n"
    for l in logs:
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(l["timestamp"]))
        csv += f"{l['device_id']},{l['event']},{l['ip'] or ''},{l['timestamp']},{dt}\n"
    return Response(csv, mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=iot_logs.csv"})

@app.route("/api/change_password", methods=["POST"])
@login_required
def change_password():
    d = request.json
    conn = get_db()
    conn.execute("UPDATE admin SET password=? WHERE username=?", (d["new_password"], session["username"]))
    conn.commit(); conn.close()
    return jsonify({"status":"ok"})

# ══════════════════════════════════════════════════════════
#   ESP32 API ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.route("/request_challenge", methods=["POST"])
def request_challenge():
    data      = request.json
    device_id = data.get("device_id")
    ip        = request.remote_addr

    if is_rate_limited(device_id, ip):
        return jsonify({"status":"Rate limit exceeded, try later"}), 429

    conn   = get_db()
    device = conn.execute("SELECT device_id,blocked FROM devices WHERE device_id=?", (device_id,)).fetchone()

    if not device:
        conn.close()
        log_event(device_id, "CHALLENGE_FAIL_UNREGISTERED", ip)
        return jsonify({"status":"Device not registered"}), 400

    if device["blocked"]:
        conn.close()
        return jsonify({"status":"Device blocked"}), 403

    challenge = secrets.token_hex(16)
    conn.execute("UPDATE devices SET challenge=?,challenge_time=? WHERE device_id=?",
                 (challenge, int(time.time()), device_id))
    conn.commit(); conn.close()
    log_event(device_id, "CHALLENGE_ISSUED", ip)
    print(f"[{device_id}] Challenge issued")
    return jsonify({"challenge": challenge})

@app.route("/verify", methods=["POST"])
def verify():
    data      = request.json
    device_id = data.get("device_id")
    ip        = request.remote_addr

    try:    signature = base64.b64decode(data["signature"])
    except:
        log_event(device_id,"AUTH_FAIL",ip)
        return jsonify({"status":"Invalid encoding"}), 400

    conn = get_db()
    row  = conn.execute("SELECT public_key,challenge,challenge_time,blocked FROM devices WHERE device_id=?", (device_id,)).fetchone()

    if not row:
        conn.close(); log_event(device_id,"AUTH_FAIL",ip)
        return jsonify({"status":"Not registered"}), 400

    if row["blocked"]:
        conn.close()
        return jsonify({"status":"Device blocked"}), 403

    # Challenge expiry check (60 seconds)
    if row["challenge_time"] and (int(time.time()) - row["challenge_time"]) > 60:
        conn.close(); log_event(device_id,"AUTH_FAIL",ip)
        return jsonify({"status":"Challenge expired"}), 401

    if not row["challenge"]:
        conn.close(); log_event(device_id,"AUTH_FAIL",ip)
        return jsonify({"status":"No challenge"}), 400

    public_key = load_pem_public_key(row["public_key"].encode())
    try:
        public_key.verify(signature, row["challenge"].encode(), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        conn.close(); log_event(device_id,"AUTH_FAIL",ip)
        check_anomaly(device_id)
        send_email_alert(
            f"[IoT Alert] Auth FAILED — {device_id}",
            f"Device {device_id} failed authentication at {time.strftime('%H:%M:%S')} from IP {ip}"
        )
        return jsonify({"status":"Invalid Signature"}), 401

    token  = secrets.token_hex(32)
    expiry = int(time.time()) + 300
    conn.execute("INSERT INTO sessions VALUES (?,?,?,?)", (device_id, token, expiry, int(time.time())))
    conn.execute("UPDATE devices SET challenge=NULL,challenge_time=NULL WHERE device_id=?", (device_id,))
    conn.commit(); conn.close()
    log_event(device_id,"AUTH_SUCCESS",ip)
    print(f"[{device_id}] Authenticated ✓")
    return jsonify({"status":"Authenticated","token":token,"expires_in":300})

@app.route("/send_data", methods=["POST"])
def send_data():
    token = request.headers.get("Authorization")
    ip    = request.remote_addr
    conn  = get_db()
    row   = conn.execute("SELECT device_id,expiry FROM sessions WHERE token=?", (token,)).fetchone()

    if not row:
        conn.close(); return jsonify({"status":"Invalid Token"}), 401
    if row["expiry"] < int(time.time()):
        conn.close(); return jsonify({"status":"Token Expired"}), 401

    device_id = row["device_id"]

    # Save sensor data if provided
    body = request.json or {}
    temp = body.get("temperature")
    hum  = body.get("humidity")
    dist = body.get("distance")

    # ── ESP002: flame/smoke payload → map into sensor_data columns ──
    # ESP002 sends: {"flame": bool, "smoke_ppm": float, "smoke_raw": int}
    # We store:  temperature=smoke_ppm, humidity=smoke_raw, distance=1.0/0.0 (flame flag)
    smoke_ppm = body.get("smoke_ppm")
    smoke_raw = body.get("smoke_raw")
    flame     = body.get("flame")

    if temp is None and smoke_ppm is not None:
        temp = float(smoke_ppm)
        hum  = float(smoke_raw) if smoke_raw is not None else 0.0
        dist = 1.0 if flame else 0.0

    if temp is not None and hum is not None:
        conn.execute(
            "INSERT INTO sensor_data (device_id,temperature,humidity,distance,timestamp) VALUES (?,?,?,?,?)",
            (device_id, temp, hum, dist, int(time.time()))
        )

    conn.execute("UPDATE devices SET last_seen=? WHERE device_id=?", (int(time.time()), device_id))
    conn.commit(); conn.close()
    log_event(device_id,"DATA_ACCEPTED",ip)
    print(f"[{device_id}] Data accepted — temp:{temp} hum:{hum} dist:{dist}")
    return jsonify({"status":"Data Accepted"})

if __name__ == "__main__":
    # Migrate: add distance column if it doesn't exist yet
    try:
        conn = get_db()
        conn.execute("ALTER TABLE sensor_data ADD COLUMN distance REAL")
        conn.commit()
        conn.close()
        print("[DB] Migrated: added distance column to sensor_data")
    except Exception:
        pass  # Column already exists
    app.run(host="0.0.0.0", port=5000, debug=True)