#include <WiFi.h>
#include <HTTPClient.h>
#include "mbedtls/pk.h"
#include "mbedtls/sha256.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include <base64.h>
#include <DHT.h>

// ═══════════════════════════════════════════════
//   ESP001 CONFIG
// ═══════════════════════════════════════════════
const char* DEVICE_ID = "ESP001";

const char* private_key_pem = R"KEY(
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgtXTfTsg60Z/GRmCF
iNhtYLZIwTJ+GtTBU3yWVcZegkahRANCAASyRQNLM861xGItaMBvZwD2HXJOb+Hq
lh4Jw/JVDjpXdpVv1XQDBEMgqIHLpQWs4os3UyCnuHGRCzQNZSbghRFA
-----END PRIVATE KEY-----
)KEY";

const char* ssid     = "PRALHAD_CHAPE 6535";
const char* password = "42]4kM36";
String server        = "http://192.168.137.1:5000";

// ── Sensor Pins ──────────────────────────────
#define DHT_PIN    4      // DHT11 DATA  → GPIO 4
#define DHT_TYPE   DHT11
#define TRIG_PIN   5      // HC-SR04 TRIG → GPIO 5
#define ECHO_PIN   18     // HC-SR04 ECHO → GPIO 18 (via voltage divider)
// ═══════════════════════════════════════════════

DHT dht(DHT_PIN, DHT_TYPE);
String token = "";
unsigned long lastAuthAttempt = 0;
const int AUTH_RETRY_DELAY = 5000;

void authenticate();
String signChallenge(String challenge);
void sendData();
String extractValue(String json, String key);
float readDistance();

// ── SETUP ──────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== ESP001 Boot ===");

  // Init sensors
  dht.begin();
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.println("Sensors initialized: DHT11 + HC-SR04");

  // Connect WiFi
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting... " + String(++attempts));
    if (attempts > 20) { Serial.println("WiFi Failed!"); return; }
  }
  Serial.println("Connected! IP: " + WiFi.localIP().toString());

  // Test server reachable
  HTTPClient http;
  http.begin(server);
  int code = http.GET();
  http.end();
  if (code <= 0) { Serial.println("Server unreachable!"); return; }

  Serial.println("Server OK! Authenticating...");
  authenticate();
}

// ── LOOP ───────────────────────────────────────
void loop() {
  delay(10000);
  sendData();
}

// ── AUTHENTICATE ───────────────────────────────
void authenticate() {
  if (millis() - lastAuthAttempt < AUTH_RETRY_DELAY) {
    Serial.println("Auth cooldown...");
    return;
  }
  lastAuthAttempt = millis();

  HTTPClient http;
  Serial.println("\n--- Authenticating ESP001 ---");

  // Step 1: Request challenge
  http.begin(server + "/request_challenge");
  http.addHeader("Content-Type", "application/json");
  int code = http.POST("{\"device_id\":\"ESP001\"}");
  Serial.println("Challenge HTTP: " + String(code));

  if (code == 429) {
    Serial.println("Rate limited! Waiting 60s...");
    http.end();
    delay(60000);
    return;
  }
  if (code == 403) {
    Serial.println("Device BLOCKED by server!");
    http.end();
    while (1) delay(10000);
  }
  if (code != 200) {
    Serial.println("Challenge request failed");
    http.end();
    return;
  }

  String response = http.getString();
  Serial.println("Response: " + response);
  http.end();

  String challenge = extractValue(response, "challenge");
  if (challenge == "") {
    Serial.println("No challenge found in response");
    return;
  }
  Serial.println("Challenge: [" + challenge + "]");

  // Step 2: Sign challenge
  String signature = signChallenge(challenge);
  if (signature == "") return;

  // Step 3: Verify signature
  http.begin(server + "/verify");
  http.addHeader("Content-Type", "application/json");
  String verifyBody = "{\"device_id\":\"ESP001\",\"signature\":\"" + signature + "\"}";
  int verifyCode = http.POST(verifyBody);
  Serial.println("Verify HTTP: " + String(verifyCode));

  if (verifyCode == 200) {
    String vr = http.getString();
    Serial.println("Verify response: " + vr);
    token = extractValue(vr, "token");
    if (token.length() > 0)
      Serial.println("AUTH SUCCESS ✓  Token: " + token.substring(0, 16) + "...");
    else
      Serial.println("ERROR: Token missing in response!");
  } else {
    Serial.println("Auth rejected: HTTP " + String(verifyCode));
  }
  http.end();
}

// ── READ DISTANCE (HC-SR04) ────────────────────
float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Timeout = 30 ms  →  ~5 m max range
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;  // No echo / out of range

  return (duration * 0.0343f) / 2.0f;  // cm
}

// ── SEND DATA ──────────────────────────────────
void sendData() {
  if (token == "") {
    Serial.println("[ESP001] No token → re-authenticating");
    authenticate();
    return;
  }

  // Read DHT11
  float temperature = dht.readTemperature();
  float humidity    = dht.readHumidity();

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("[ESP001] DHT11 read failed! Using 0");
    temperature = 0;
    humidity    = 0;
  } else {
    Serial.printf("[ESP001] DHT11  →  Temp: %.1f°C   Humidity: %.1f%%\n",
                  temperature, humidity);
  }

  // Read HC-SR04
  float distance = readDistance();
  if (distance < 0) {
    Serial.println("[ESP001] HC-SR04 → Out of range / no echo");
  } else {
    Serial.printf("[ESP001] HC-SR04 →  Distance: %.1f cm\n", distance);
  }

  // Build JSON payload
  String body = "{";
  body += "\"temperature\":" + String(temperature, 1) + ",";
  body += "\"humidity\":"    + String(humidity,    1) + ",";
  body += "\"distance\":"    + String(distance,    1);
  body += "}";

  Serial.println("[ESP001] Posting: " + body);

  // POST to server  —  Authorization: <token>  (no "Bearer " prefix)
  HTTPClient http;
  http.begin(server + "/send_data");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", token);

  int code = http.POST(body);

  if (code > 0) {
    String resp = http.getString();
    Serial.println("[ESP001] Server reply: " + resp);

    if (resp.indexOf("Token Expired") >= 0 ||
        resp.indexOf("Invalid Token") >= 0) {
      Serial.println("[ESP001] Token invalid → will re-auth next cycle");
      token = "";
    }
  } else {
    Serial.println("[ESP001] POST error: " + String(code));
  }
  http.end();
}

// ── SIGN CHALLENGE (ECDSA / SHA-256) ──────────
String signChallenge(String challenge) {
  mbedtls_pk_context pk;
  mbedtls_entropy_context entropy;
  mbedtls_ctr_drbg_context ctr_drbg;

  mbedtls_pk_init(&pk);
  mbedtls_entropy_init(&entropy);
  mbedtls_ctr_drbg_init(&ctr_drbg);

  const char* pers = "esp32_ecdsa";
  int ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy,
                                   (const unsigned char*)pers, strlen(pers));
  if (ret != 0) {
    Serial.printf("RNG seed failed: -0x%04X\n", -ret);
    mbedtls_pk_free(&pk);
    mbedtls_entropy_free(&entropy);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    return "";
  }

  // strlen + 1  →  include the null terminator (required by mbedTLS)
  ret = mbedtls_pk_parse_key(&pk,
                              (const unsigned char*)private_key_pem,
                              strlen(private_key_pem) + 1,
                              NULL, 0,
                              mbedtls_ctr_drbg_random, &ctr_drbg);
  if (ret != 0) {
    Serial.printf("Key parse failed: -0x%04X\n", -ret);
    mbedtls_pk_free(&pk);
    mbedtls_entropy_free(&entropy);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    return "";
  }

  unsigned char hash[32];
  mbedtls_sha256((const unsigned char*)challenge.c_str(),
                 challenge.length(), hash, 0);

  unsigned char signature[128];
  size_t sig_len = 0;
  ret = mbedtls_pk_sign(&pk, MBEDTLS_MD_SHA256, hash, 32,
                        signature, sizeof(signature), &sig_len,
                        mbedtls_ctr_drbg_random, &ctr_drbg);
  if (ret != 0) {
    Serial.printf("Sign failed: -0x%04X\n", -ret);
    mbedtls_pk_free(&pk);
    mbedtls_entropy_free(&entropy);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    return "";
  }

  String encoded = base64::encode(signature, sig_len);

  mbedtls_pk_free(&pk);
  mbedtls_entropy_free(&entropy);
  mbedtls_ctr_drbg_free(&ctr_drbg);

  return encoded;
}

// ── LIGHTWEIGHT JSON VALUE EXTRACTOR ──────────
String extractValue(String json, String key) {
  String p1 = "\"" + key + "\":\"";
  String p2 = "\"" + key + "\": \"";

  int start = json.indexOf(p1);
  if (start >= 0) start += p1.length();
  else {
    start = json.indexOf(p2);
    if (start < 0) return "";
    start += p2.length();
  }

  int end = json.indexOf("\"", start);
  if (end < 0) return "";
  return json.substring(start, end);
}
