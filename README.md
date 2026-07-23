<div align="center">

# 🔐 IoT ECC Authentication System

<img src="https://readme-typing-svg.herokuapp.com?font=Orbitron&size=22&duration=3000&pause=1000&color=00F5FF&center=true&vCenter=true&width=600&lines=ECC-Based+Secure+IoT+Authentication;Real-Time+Monitoring+Dashboard;Replay+Attack+Prevention;Multi-Device+Support" alt="Typing SVG" />

<br/>

[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-black?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![ESP32](https://img.shields.io/badge/ESP32-IoT_Device-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://www.espressif.com)
[![mbedTLS](https://img.shields.io/badge/mbedTLS-Cryptography-6DB33F?style=for-the-badge)](https://tls.mbed.org)
[![ECC](https://img.shields.io/badge/ECC-P--256-purple?style=for-the-badge)](https://en.wikipedia.org/wiki/Elliptic-curve_cryptography)

<br/>

> **A patent-filed, production-grade IoT security system that authenticates ESP32 devices using Elliptic Curve Cryptography (ECDSA P-256) — without ever transmitting a private key.**

<br/>

[![Stars](https://img.shields.io/github/stars/pralhadchape24/iot-authentication-server?style=social)](https://github.com/pralhadchape24/iot-authentication-server/stargazers)
[![Forks](https://img.shields.io/github/forks/pralhadchape24/iot-authentication-server?style=social)](https://github.com/pralhadchape24/iot-authentication-server/network)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📸 Dashboard Preview

```
╔══════════════════════════════════════════════════════════╗
║  🔐 SECUREIOT  — ECC Authentication Control Center       ║
╠══════════════════════════════════════════════════════════╣
║  Devices: 2    Online: 2    Auth OK: 47    Fail: 1       ║
╠════════════════════╦═════════════════════════════════════╣
║  📡 ESP001 🟢      ║  📋 Activity Log                    ║
║  Last seen: 3s ago ║  ✅ AUTH_SUCCESS  ESP001  22:14:01  ║
║  Token: [████░] 72%║  📦 DATA_ACCEPTED ESP002  22:14:05  ║
╠════════════════════║  🔑 CHALLENGE     ESP001  22:14:09  ║
║  📡 ESP002 🟢      ║  ✅ AUTH_SUCCESS  ESP002  22:14:11  ║
║  Last seen: 7s ago ║                                     ║
║  Token: [██░░░] 41%║  🛡 Security Score: 98 / 100        ║
╚════════════════════╩═════════════════════════════════════╝
```

---

## 📖 Table of Contents

- [Overview](#-overview)
- [How It Works](#-how-it-works)
- [Security Features](#-security-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Hardware Setup](#-hardware-setup)
- [Installation & Setup](#-installation--setup)
- [API Endpoints](#-api-endpoints)
- [Dashboard Features](#-dashboard-features)
- [Multi-Device Support](#-multi-device-support)
- [Patent](#-patent)
- [Future Enhancements](#-future-enhancements)
- [Authors](#-authors)

---

## 🌟 Overview

The **IoT ECC Authentication System** solves a critical problem in IoT security: how do you prove a device's identity without sending any secret over the network?

Traditional IoT systems use **API keys or passwords** — if intercepted once, the attacker has permanent access. Our system uses **Elliptic Curve Digital Signature Algorithm (ECDSA)** on the P-256 curve, the same cryptography that secures HTTPS and modern banking.

### Why ECC?

| Property | RSA-3072 | ECC P-256 |
|---|---|---|
| Equivalent Security | 3072-bit key | **256-bit key** |
| Key Size | Large | **12× smaller** |
| Signing Speed | Slow | **Fast** |
| Memory Usage | High | **Low** |
| Perfect for ESP32? | ❌ | **✅** |

---

## ⚙️ How It Works

```
ESP32                                    Flask Server
  │                                           │
  │──── POST /request_challenge ─────────────►│
  │     {"device_id": "ESP001"}               │  ① Check device in DB
  │                                           │  ② Apply rate limiting
  │◄─── {"challenge": "a3f9bc12..."} ────────│  ③ Generate random 128-bit challenge
  │                                           │
  │  [Signs challenge with private key]       │
  │  hash    = SHA256(challenge)              │
  │  sig     = ECDSA_sign(hash, private_key)  │
  │  encoded = Base64(sig)                    │
  │                                           │
  │──── POST /verify ─────────────────────────►│
  │     {device_id, signature}                │  ④ Check challenge expiry (60s)
  │                                           │  ⑤ ECDSA_verify(sig, challenge, pubkey)
  │◄─── {"token": "abc123...", expires: 300} ─│  ⑥ Issue 300s session token
  │                                           │
  │──── POST /send_data (every 10s) ──────────►│
  │     Header: Authorization: <token>        │  ⑦ Validate token
  │     Body: {temp, humidity, distance}      │  ⑧ Store sensor data
  │◄─── {"status": "Data Accepted"} ──────────│  ⑨ Update last_seen
```

### Key Principle
> **The private key NEVER leaves the ESP32.** Only the mathematical signature is sent. Even if someone intercepts all network traffic, they cannot extract or replicate the private key.

---

## 🛡️ Security Features

| Feature | Implementation | Protection Against |
|---|---|---|
| **ECC Authentication** | ECDSA P-256 + SHA-256 | Password theft, weak credentials |
| **Replay Prevention** | One-time random 128-bit challenge | Packet replay attacks |
| **Challenge Expiry** | 60-second timeout | Delayed replay attacks |
| **Rate Limiting** | 5 requests / 60s per device/IP | Brute force attacks |
| **Auto-Block** | 3 failures → blocked=1 | Sustained brute force |
| **Token Expiry** | 300-second session window | Token theft |
| **Device Isolation** | Independent key pair per device | Single-device compromise |
| **Email Alerts** | Gmail SMTP on auth failure | Silent attacks |

---

## 🛠️ Tech Stack

### Server Side
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.13 | Backend language |
| Flask | 3.x | REST API framework |
| SQLite | 3.x | Lightweight database |
| cryptography (hazmat) | 46.x | ECDSA verification, key loading |
| smtplib | stdlib | Email alert dispatch |

### ESP32 Firmware
| Library | Purpose |
|---|---|
| mbedTLS | ECDSA signing, SHA-256, RNG |
| WiFi.h | IEEE 802.11 WiFi connection |
| HTTPClient.h | REST API POST requests |
| base64.h | Signature encoding |
| DHT.h | Temperature & humidity sensor |

### Dashboard
| Technology | Purpose |
|---|---|
| HTML5 Canvas | Auth timeline chart, sensor graph |
| SVG | Circular token countdown ring |
| Fetch API | Async polling every 3 seconds |
| Web Notifications API | Browser push on auth failure |
| Web Audio API | Sound alert on security events |

---

## 📂 Project Structure

```
IoT-Authentication-Server/
│
├── 📁 ESP001_Sketch/
│   └── ESP001_Sketch.ino        ← ESP32 firmware (DHT11 + HC-SR04)
│
├── 📁 ESP002_Sketch/
│   └── ESP002_Sketch.ino        ← Second ESP32 firmware
│
├── 📁 templates/
│   ├── dashboard.html           ← Real-time monitoring dashboard
│   ├── device.html              ← Per-device detail page
│   └── login.html               ← Admin login page
│
├── app.py                       ← Flask server + all API endpoints
├── init_db.py                   ← Database initializer (all 6 tables)
├── generate_keys.py             ← ECC key pair generator per device
├── register_device.py           ← Register device public key in DB
├── sign_test.py                 ← Manual signature test utility
├── database.db                  ← SQLite database (auto-created)
│
├── private_key_ESP001.pem       ← ESP001 private key (flash to device)
├── public_key_ESP001.pem        ← ESP001 public key (stored in DB)
├── private_key_ESP002.pem       ← ESP002 private key
├── public_key_ESP002.pem        ← ESP002 public key
│
├── requirements.txt             ← Python dependencies
├── README.md
└── .gitignore                   ← Excludes .pem and .db files
```

> ⚠️ **Security Note:** `.pem` key files and `database.db` are excluded from version control via `.gitignore`. Never commit private keys to GitHub.

---

## 🔌 Hardware Setup

### Components Required

| Component | Quantity | Purpose |
|---|---|---|
| ESP32 Dev Board | 2 | IoT authentication devices |
| DHT11 Sensor | 1 per device | Temperature & humidity |
| HC-SR04 Ultrasonic | 1 per device | Distance measurement |
| Breadboard + Jumpers | — | Circuit assembly |
| 1kΩ + 2kΩ Resistors | 1 set | Voltage divider for HC-SR04 |

### Wiring — DHT11

| DHT11 Pin | ESP32 Pin |
|---|---|
| VCC | 3.3V |
| GND | GND |
| DATA | GPIO 4 |

### Wiring — HC-SR04

| HC-SR04 Pin | ESP32 Pin | Note |
|---|---|---|
| VCC | 5V / VIN | — |
| GND | GND | — |
| TRIG | GPIO 5 | Direct |
| ECHO | GPIO 18 | Via voltage divider (5V → 3.3V) |

> **Why voltage divider on ECHO?** HC-SR04 outputs 5V on ECHO but ESP32 GPIO max is 3.3V. Use 1kΩ + 2kΩ resistors: `Vout = 5V × 2/(1+2) = 3.33V`

### Network Setup

```
Laptop Hotspot (192.168.137.1:5000)
         │
    ┌────┴────┐
  ESP001   ESP002
(192.168.137.x)
```

Enable Mobile Hotspot on your laptop. Server IP is always `192.168.137.1`.  
Add Windows Firewall rule (run as Admin):
```powershell
netsh advfirewall firewall add rule name="Flask5000" dir=in action=allow protocol=TCP localport=5000
```

---

## 🚀 Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/pralhadchape24/iot-authentication-server.git
cd iot-authentication-server
```

### 2. Install Python Dependencies
```bash
pip install flask cryptography
```

### 3. Initialize Database
```bash
python init_db.py
```
Output:
```
Database initialized with tables: devices, sessions, logs, sensor_data, admin, rate_limit
Default login => username: admin  password: admin123
```

### 4. Generate Keys for Each Device
```bash
python generate_keys.py ESP001
python generate_keys.py ESP002
```
Creates: `private_key_ESP001.pem`, `public_key_ESP001.pem`, etc.

### 5. Register Devices in Database
```bash
python register_device.py ESP001
python register_device.py ESP002
```

### 6. Configure ESP32 Sketch

Open `ESP001_Sketch/ESP001_Sketch.ino` and update:
```cpp
const char* DEVICE_ID = "ESP001";          // device name

const char* private_key_pem = R"KEY(
-----BEGIN PRIVATE KEY-----
<paste contents of private_key_ESP001.pem here>
-----END PRIVATE KEY-----
)KEY";

const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
String server        = "http://192.168.137.1:5000";
```

Upload to ESP32 using Arduino IDE.

### 7. Start Flask Server
```bash
python app.py
```

### 8. Open Dashboard
```
http://localhost:5000
Login: admin / admin123
```

---

## 📡 API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/` | GET | Session | Dashboard home |
| `/login` | GET/POST | — | Admin login |
| `/logout` | GET | Session | Logout |
| `/device/<id>` | GET | Session | Per-device detail page |
| `/api/stats` | GET | Session | Dashboard JSON data |
| `/api/device/<id>` | GET | Session | Device-specific JSON |
| `/api/device/rename` | POST | Session | Rename device |
| `/api/device/delete` | POST | Session | Delete device |
| `/api/device/unblock` | POST | Session | Unblock device |
| `/api/logs/export` | GET | Session | Download logs CSV |
| `/api/change_password` | POST | Session | Change admin password |
| `/request_challenge` | POST | — | ESP32: get challenge |
| `/verify` | POST | — | ESP32: verify signature |
| `/send_data` | POST | Token | ESP32: send sensor data |

### Example — Request Challenge
```bash
curl -X POST http://localhost:5000/request_challenge \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ESP001"}'
```
```json
{"challenge": "a3f9bc12d4e5f67890abcdef12345678"}
```

### Example — Send Data (from ESP32)
```bash
curl -X POST http://localhost:5000/send_data \
  -H "Authorization: <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"temperature": 28.5, "humidity": 62.0, "distance": 34.2}'
```
```json
{"status": "Data Accepted"}
```

---

## 📊 Dashboard Features

### Real-Time Panels
| Panel | What it shows |
|---|---|
| **Device Monitor** | Online/Offline/Blocked, token ring (SVG), sensor badges, last seen |
| **Auth Analytics** | Timeline bar chart, success rate graph per minute |
| **24h Heatmap** | Which hours had most activity |
| **Security Score** | 0–100 based on auth failure rate, threat level (Low/Med/High) |
| **Network Topology** | Animated device → server connection map |
| **Session History** | All tokens, created/expiry time, Active/Expired |
| **Server Health** | Uptime, DB size, active session count |
| **Activity Log** | Search + filter by event type, live updates |

### Management Features
- ✏️ **Rename** — Give devices friendly names like "Room Sensor"
- 🔓 **Unblock** — Re-enable auto-blocked devices
- 🗑️ **Delete** — Remove device and all sessions
- ⬇️ **Export CSV** — Download all logs
- ⛶ **Fullscreen** — Presentation mode
- 🌙 **Dark/Light** — Theme toggle
- 🔔 **Notifications** — Browser + sound alerts on auth failure

### Per-Device Page
Click 📊 on any device card to open its detail page:
- Latest temperature, humidity, distance readings
- Sensor history line chart
- Complete session history table
- Full activity log for that device

---

## 📱 Multi-Device Support

The system supports unlimited devices. Each device gets:
- Its own ECC key pair (mathematically independent)
- Its own entry in the database
- Its own session tokens
- Its own sensor data history

```bash
# Add a third device
python generate_keys.py ESP003
python register_device.py ESP003
```

**Device Isolation:** If ESP002's private key is compromised, ESP001 and ESP003 are completely unaffected. Each device is cryptographically independent.

---

## 🗄️ Database Schema

```sql
-- Device registry
CREATE TABLE devices (
    device_id      TEXT PRIMARY KEY,
    public_key     TEXT,           -- PEM-encoded ECDSA P-256
    challenge      TEXT,           -- one-time challenge (cleared after use)
    challenge_time INTEGER,        -- Unix timestamp (60s expiry)
    last_seen      INTEGER,        -- Unix timestamp of last data packet
    blocked        INTEGER DEFAULT 0,
    nickname       TEXT
);

-- Session tokens
CREATE TABLE sessions (
    device_id TEXT,
    token     TEXT,                -- 64-char hex (256-bit)
    expiry    INTEGER,             -- Unix timestamp (now + 300s)
    created   INTEGER
);

-- Audit logs
CREATE TABLE logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    event     TEXT,                -- AUTH_SUCCESS, AUTH_FAIL, DATA_ACCEPTED...
    ip        TEXT,
    timestamp INTEGER
);

-- Sensor telemetry
CREATE TABLE sensor_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT,
    temperature REAL,              -- °C from DHT11
    humidity    REAL,              -- % from DHT11
    distance    REAL,              -- cm from HC-SR04
    timestamp   INTEGER
);

-- Admin credentials
CREATE TABLE admin (username TEXT PRIMARY KEY, password TEXT);

-- Rate limiting records
CREATE TABLE rate_limit (device_id TEXT, ip TEXT, timestamp INTEGER);
```

---

## 📧 Email Alerts Setup

To enable email notifications on auth failures:

1. Enable **2-Step Verification** on your Google account
2. Generate a **Gmail App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Update `app.py`:

```python
EMAIL_ENABLED  = True
EMAIL_FROM     = "your@gmail.com"
EMAIL_TO       = "alert@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # 16-char App Password
```

---

## 🔮 Future Enhancements

- [ ] **HTTPS / TLS** — Encrypt transport layer
- [ ] **Hardware Secure Element** — Store private key in ESP32 NVS or HSE
- [ ] **WebSocket** — True real-time dashboard (replace polling)
- [ ] **JWT Tokens** — Industry-standard token format
- [ ] **OTA Firmware Updates** — Over-the-air updates with auth
- [ ] **MQTT Support** — Lightweight IoT protocol
- [ ] **Cloud Deployment** — AWS / Azure / GCP hosting
- [ ] **Mobile App** — React Native dashboard
- [ ] **Telegram / Discord Alerts** — Webhook notifications
- [ ] **Multi-Server Federation** — Monitor multiple servers

---

## 📜 Patent

This project has been filed as a patent at **Vishwakarma Institute of Technology, Pune**.

> **Title:** ECC-Based Secure Authentication System for IoT Devices with Real-Time Monitoring and Anomaly Detection

**Inventor:**
- Pralhad Shivaji Chape

---

## 📚 References

- [NIST FIPS 186-4 — Digital Signature Standard (DSS)](https://csrc.nist.gov/publications/detail/fips/186/4/final)
- [RFC 6979 — Deterministic ECDSA](https://datatracker.ietf.org/doc/html/rfc6979)
- [mbedTLS Documentation](https://tls.mbed.org/api/)
- [ESP32 Technical Reference Manual](https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf)
- [Python cryptography library](https://cryptography.io/en/latest/)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

## 👨‍💻 Authors

| | |
|---|---|
| **Pralhad Shivaji Chape** | B.Tech Computer Engineering, VIT Pune |
| GitHub | [@pralhadchape24](https://github.com/pralhadchape24) |

<br/>

**Vishwakarma Institute of Technology (VIT), Pune**  
Department of Computer Engineering

<br/>

⭐ **If this project helped you, please give it a star!** ⭐

<br/>

![Footer](https://capsule-render.vercel.app/api?type=waving&color=00F5FF&height=100&section=footer)

</div>
