# 🔐 IoT Authentication Server

<p align="center">

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black?style=for-the-badge&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite)
![ESP8266](https://img.shields.io/badge/ESP8266-IoT-green?style=for-the-badge)

</p>

<p align="center">
A secure IoT authentication system that enables trusted communication between ESP8266 devices and a Flask server using device registration, cryptographic keys, and digital signature verification.
</p>

---

# 📖 Overview

IoT Authentication Server is a security-focused IoT project that authenticates ESP8266 devices before allowing communication with the server. It provides device registration, key generation, database management, and digital signature verification to ensure secure communication.

---

# ✨ Features

### 🔐 Device Authentication

- Device Registration
- Secure Authentication
- Identity Verification

### 🔑 Cryptography

- Public/Private Key Generation
- Digital Signature Verification
- Secure Key Management

### 🌐 Server

- Flask REST API
- SQLite Database
- Device Management

### 📡 IoT Integration

- ESP8266 Device Support
- Secure Server Communication
- Authentication Requests

---

# 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python | Backend |
| Flask | REST API |
| SQLite | Database |
| ESP8266 | IoT Device |
| Arduino IDE | Firmware Development |

---

# 📂 Project Structure

```text
IoT-Authentication-Server/
│
├── ESP001_Sketch/
│   └── ESP001_Sketch.ino
│
├── ESP002_Sketch/
│   └── ESP002_Sketch.ino
│
├── server/
│   ├── app.py
│   ├── database.py
│   ├── init_db.py
│   ├── register_device.py
│   ├── generate_key.py
│   ├── generate_keys.py
│   └── sign_test.py
│
├── README.md
└── .gitignore
```

---

# 🚀 Installation

Clone the repository

```bash
git clone https://github.com/pralhadchape24/iot-authentication-server.git
```

Install Python dependencies

```bash
pip install -r requirements.txt
```

Initialize the database

```bash
python init_db.py
```

Run the Flask server

```bash
python app.py
```

Upload the Arduino sketches to the ESP8266 devices using Arduino IDE.

---

# 🎯 Key Features

- Secure Device Registration
- Cryptographic Key Generation
- Digital Signature Verification
- Flask REST API
- SQLite Database
- ESP8266 Integration

---

# 📚 Learning Outcomes

- IoT Security
- Flask Development
- REST APIs
- Cryptography
- SQLite Database
- ESP8266 Programming

---

# 🔮 Future Enhancements

- MQTT Support
- TLS Encryption
- JWT Authentication
- Cloud Deployment
- Device Dashboard
- OTA Firmware Updates

---

# 👨‍💻 Author

**Pralhad Shivaji Chape**

B.Tech Computer Engineering

Vishwakarma Institute of Technology (VIT), Pune

GitHub: https://github.com/pralhadchape24