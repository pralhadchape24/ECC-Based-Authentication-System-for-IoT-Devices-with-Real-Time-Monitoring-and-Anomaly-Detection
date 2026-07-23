#include <WiFi.h>
#include <HTTPClient.h>
#include "mbedtls/pk.h"
#include "mbedtls/sha256.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include <base64.h>

// ═══════════════════════════════════════════════
//   ESP002 CONFIG
// ═══════════════════════════════════════════════
const char* DEVICE_ID = "ESP002";

const char* private_key_pem = R"KEY(
-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgrcz1oNeJG80bVc5m
D0dM+Qo3PbMtqxEgIB1qwWQ2bcehRANCAARRA9ZLZ3OknUuLBxaqrXTadFgTTlYr
xTjCKRmoci3eBP7WkArBIBHNFgRklo+6h2nhtnnpdGQNK5S7alm8SWzC
-----END PRIVATE KEY-----
)KEY";

const char* ssid     = "PRALHAD_CHAPE 6535";
const char* password = "42]4kM36";
String server        = "http://192.168.137.1:5000";

// ═══════════════════════════════════════════════
//   SENSOR PINS
// ═══════════════════════════════════════════════
#define FLAME_PIN   4    // Flame sensor DO  → GPIO 4  (LOW = flame detected)
#define MQ2_PIN     34   // MQ2 sensor   AO  → GPIO 34 (analog 0–4095)

// MQ2 calibration — adjust MQ2_RO_CLEAN_AIR after 2-3 min warm-up in clean air
#define MQ2_RL_VALUE     10.0   // Load resistor on module in kΩ
#define MQ2_RO_CLEAN_AIR  9.83  // Sensor Ro in clean air (kΩ)
// ═══════════════════════════════════════════════

String token = "";

void authenticate();
String signChallenge(String challenge);
void sendData(bool flameDetected, float smokePPM, int rawADC);
float readMQ2PPM(int* rawOut);
bool  readFlame();

// ═══════════════════════════════════════════════
//   SETUP
// ═══════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== ESP002 Boot ===");

  // Sensor setup
  pinMode(FLAME_PIN, INPUT);
  analogReadResolution(12);        // 12-bit ADC: 0–4095
  analogSetAttenuation(ADC_11db); // Full 0–3.3V range on GPIO34

  WiFi.begin(ssid, password);
  int attempts = 0;
  while(WiFi.status() != WL_CONNECTED){
    delay(1000);
    Serial.println("Connecting... " + String(++attempts));
    if(attempts > 20){ Serial.println("WiFi Failed!"); return; }
  }
  Serial.println("Connected! IP: " + WiFi.localIP().toString());

  HTTPClient testHttp;
  testHttp.begin(server);
  int testCode = testHttp.GET();
  testHttp.end();
  if(testCode == -1){ Serial.println("ERROR: Cannot reach server!"); return; }

  Serial.println("Server OK! Authenticating...");
  authenticate();
}

// ═══════════════════════════════════════════════
//   LOOP
// ═══════════════════════════════════════════════
void loop(){
  delay(10000);

  int   rawADC        = 0;
  float smokePPM      = readMQ2PPM(&rawADC);
  bool  flameDetected = readFlame();

  // Local alerts
  if(flameDetected)
    Serial.println("⚠️  FLAME DETECTED!");
  if(smokePPM > 300)
    Serial.printf("⚠️  HIGH SMOKE: %.0f PPM\n", smokePPM);

  sendData(flameDetected, smokePPM, rawADC);
}

// ═══════════════════════════════════════════════
//   FLAME SENSOR
// ═══════════════════════════════════════════════
bool readFlame(){
  // DO module: LOW = flame detected, HIGH = no flame (active-low)
  bool detected = (digitalRead(FLAME_PIN) == LOW);
  Serial.printf("[FLAME] GPIO%d=%d  →  %s\n",
                FLAME_PIN, digitalRead(FLAME_PIN),
                detected ? "FLAME DETECTED" : "No flame");
  return detected;
}

// ═══════════════════════════════════════════════
//   MQ2 SMOKE SENSOR
// ═══════════════════════════════════════════════
float mq2GetRs(int adcValue){
  if(adcValue <= 0) adcValue = 1;
  float voltage = (adcValue / 4095.0f) * 3.3f;
  if(voltage <= 0.0f) voltage = 0.001f;
  return MQ2_RL_VALUE * (3.3f - voltage) / voltage;  // kΩ
}

float mq2PPMfromRatio(float ratio){
  // MQ2 datasheet log-log curve for LPG/Smoke
  // ppm = 10 ^ ((log10(ratio) - 0.55) / -0.47)
  return pow(10.0f, (log10(ratio) - 0.55f) / -0.47f);
}

float readMQ2PPM(int* rawOut){
  long sum = 0;
  for(int i = 0; i < 10; i++){
    sum += analogRead(MQ2_PIN);
    delay(5);
  }
  int adcAvg = sum / 10;
  if(rawOut) *rawOut = adcAvg;

  float rs    = mq2GetRs(adcAvg);
  float ratio = rs / MQ2_RO_CLEAN_AIR;
  float ppm   = mq2PPMfromRatio(ratio);

  Serial.printf("[MQ2]  ADC=%d  Rs=%.2fkΩ  Rs/Ro=%.3f  PPM=%.1f\n",
                adcAvg, rs, ratio, ppm);
  return ppm;
}

// ═══════════════════════════════════════════════
//   AUTH
// ═══════════════════════════════════════════════
void authenticate(){
  HTTPClient http;
  Serial.println("\n--- Authenticating " + String(DEVICE_ID) + " ---");

  http.begin(server + "/request_challenge");
  http.addHeader("Content-Type", "application/json");

  int code = http.POST("{\"device_id\":\"" + String(DEVICE_ID) + "\"}");

  Serial.println("Challenge HTTP: " + String(code));

  if(code <= 0){ http.end(); return; }
  if(code == 429){ Serial.println("Rate limited! Waiting..."); http.end(); delay(60000); return; }
  if(code == 403){ Serial.println("Device BLOCKED!"); http.end(); while(1) delay(10000); }

  String response = http.getString();
  Serial.println("Response: " + response);

  int start = response.indexOf("\"challenge\": \"");
  start = (start >= 0) ? start + 14 : response.indexOf("\"challenge\":\"") + 13;

  String challenge = response.substring(start, response.indexOf("\"", start));
  challenge.trim();

  Serial.println("Challenge: [" + challenge + "]");

  if(challenge.length() == 0){ http.end(); return; }

  String signature = signChallenge(challenge);
  if(signature == ""){ http.end(); return; }

  http.end();

  http.begin(server + "/verify");
  http.addHeader("Content-Type", "application/json");

  String vb = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"signature\":\"" + signature + "\"}";

  int vc = http.POST(vb);

  if(vc > 0){
    String vr = http.getString();
    Serial.println("Verify: " + vr);

    if(vc == 401){
      Serial.println("Auth REJECTED");
      http.end();
      return;
    }

    int tStart = vr.indexOf("\"token\": \"");
    tStart = (tStart >= 0) ? tStart + 10 : vr.indexOf("\"token\":\"") + 9;

    token = vr.substring(tStart, vr.indexOf("\"", tStart));
    token.trim();

    if(token.length() > 0)
      Serial.println("AUTH SUCCESS! ✓");
    else
      Serial.println("ERROR: Token parse failed");
  }

  http.end();
}

// ═══════════════════════════════════════════════
//   SIGN
// ═══════════════════════════════════════════════
String signChallenge(String challenge){
  mbedtls_pk_context pk;
  mbedtls_entropy_context entropy;
  mbedtls_ctr_drbg_context ctr_drbg;

  mbedtls_pk_init(&pk);
  mbedtls_entropy_init(&entropy);
  mbedtls_ctr_drbg_init(&ctr_drbg);

  const char* pers = "esp32_ecdsa";

  int ret = mbedtls_ctr_drbg_seed(
    &ctr_drbg,
    mbedtls_entropy_func,
    &entropy,
    (const unsigned char*)pers,
    strlen(pers)
  );

  if(ret != 0){
    Serial.printf("RNG failed: -0x%04X\n", -ret);
    return "";
  }

  ret = mbedtls_pk_parse_key(
    &pk,
    (const unsigned char*)private_key_pem,
    strlen(private_key_pem)+1,
    NULL,
    0,
    mbedtls_ctr_drbg_random,
    &ctr_drbg
  );

  if(ret != 0){
    Serial.printf("Key failed: -0x%04X\n", -ret);
    return "";
  }

  unsigned char hash[32];
  mbedtls_sha256((const unsigned char*)challenge.c_str(), challenge.length(), hash, 0);

  unsigned char signature[128];
  size_t sig_len = 0;

  ret = mbedtls_pk_sign(
    &pk,
    MBEDTLS_MD_SHA256,
    hash,
    32,
    signature,
    sizeof(signature),
    &sig_len,
    mbedtls_ctr_drbg_random,
    &ctr_drbg
  );

  if(ret != 0){
    Serial.printf("Sign failed: -0x%04X\n", -ret);
    return "";
  }

  String encoded = base64::encode(signature, sig_len);

  mbedtls_pk_free(&pk);
  mbedtls_entropy_free(&entropy);
  mbedtls_ctr_drbg_free(&ctr_drbg);

  return encoded;
}

// ═══════════════════════════════════════════════
//   SEND DATA
// ═══════════════════════════════════════════════
void sendData(bool flameDetected, float smokePPM, int rawADC){
  if(token == ""){
    Serial.println("[" + String(DEVICE_ID) + "] No token, re-auth...");
    authenticate();
    return;
  }

  HTTPClient http;
  http.begin(server + "/send_data");

  http.addHeader("Authorization", token);
  http.addHeader("Content-Type", "application/json");

  String flameStr = flameDetected ? "true" : "false";
  String body = "{\"flame\":"    + flameStr +
                ",\"smoke_ppm\":" + String(smokePPM, 1) +
                ",\"smoke_raw\":" + String(rawADC) + "}";

  Serial.println("[" + String(DEVICE_ID) + "] Sending: " + body);

  int code = http.POST(body);

  if(code > 0){
    String response = http.getString();
    Serial.println("[" + String(DEVICE_ID) + "] " + response);

    if(response.indexOf("Token Expired") >= 0 ||
       response.indexOf("Invalid Token") >= 0){
      token = "";
      authenticate();
    }
  } else {
    Serial.println("[" + String(DEVICE_ID) + "] sendData failed: " + String(code));
  }

  http.end();
}
