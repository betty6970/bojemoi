/*
 * Bojemoi Lab — Sentinel ESP32
 * Détection smartphones via WiFi probe requests + BLE scan
 * Publie sur MQTT : bojemoi/perimeter/wifi et bojemoi/perimeter/ble
 *
 * Dépendances Arduino :
 *   - PubSubClient (Nick O'Leary)
 *   - ArduinoJson
 *   - ESP32 BLE Arduino (inclus dans le core ESP32)
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEScan.h>

// ─── Configuration ──────────────────────────────────────────────────────────
#define WIFI_SSID       "bojemoi-iot"          // Réseau WiFi de l'ESP32
#define WIFI_PASS       "changeme"
#define MQTT_HOST       "192.168.1.121"        // IP manager (meta-76)
#define MQTT_PORT       1883
#define MQTT_USER       "sentinel"
#define MQTT_PASS       "changeme"
#define ESP32_ID        "sentinel-01"          // Identifiant unique par ESP32
#define ZONE_NAME       "front-door"           // Zone physique du capteur
                                               // Exemples: "front-door", "living-room",
                                               //           "garden", "garage", "office"
#define BLE_SCAN_SECS   5
#define LOOP_DELAY_MS   10000                  // Cycle BLE toutes les 10s

// MACs connues/autorisées (format "aa:bb:cc:dd:ee:ff" lowercase)
const char* WHITELIST[] = {
  "a4:c3:f0:xx:xx:xx",   // iPhone perso
  "dc:a6:32:xx:xx:xx",   // RaspberryPi
};
const int WHITELIST_SIZE = sizeof(WHITELIST) / sizeof(WHITELIST[0]);

// ─── Globals ─────────────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
BLEScan*     bleScan;

// ─── Helpers ─────────────────────────────────────────────────────────────────
String macToStr(const uint8_t* mac) {
  char buf[18];
  snprintf(buf, sizeof(buf), "%02x:%02x:%02x:%02x:%02x:%02x",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  return String(buf);
}

bool isWhitelisted(const String& mac) {
  for (int i = 0; i < WHITELIST_SIZE; i++) {
    if (mac.startsWith(String(WHITELIST[i]).substring(0, 8))) return true;
  }
  return false;
}

// Bit 1 du premier octet = locally administered (MAC aléatoire)
bool isMacRandomized(const uint8_t* mac) {
  return (mac[0] & 0x02) != 0;
}

void mqttReconnect() {
  while (!mqtt.connected()) {
    Serial.print("MQTT connect...");
    if (mqtt.connect(ESP32_ID, MQTT_USER, MQTT_PASS)) {
      Serial.println("ok");
    } else {
      Serial.printf("failed rc=%d, retry 5s\n", mqtt.state());
      delay(5000);
    }
  }
}

void publishDetection(const char* type, const String& mac, int rssi,
                      bool randomized, const String& extra = "") {
  StaticJsonDocument<256> doc;
  doc["esp32_id"]   = ESP32_ID;
  doc["zone"]       = ZONE_NAME;   // zone physique du capteur
  doc["type"]       = type;
  doc["mac"]        = mac;
  doc["rssi"]       = rssi;
  doc["randomized"] = randomized;
  doc["known"]      = isWhitelisted(mac);
  doc["ts"]         = millis();
  if (extra.length() > 0) doc["extra"] = extra;

  char payload[256];
  serializeJson(doc, payload);

  String topic = "bojemoi/perimeter/";
  topic += type;
  mqtt.publish(topic.c_str(), payload, false);

  Serial.printf("[%s] %s rssi=%d random=%d known=%d\n",
                type, mac.c_str(), rssi, randomized,
                isWhitelisted(mac) ? 1 : 0);
}

// ─── WiFi Promiscuous callback ────────────────────────────────────────────────
void IRAM_ATTR probeCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;

  wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  wifi_pkt_rx_ctrl_t ctrl     = pkt->rx_ctrl;
  uint8_t* payload             = pkt->payload;

  // Frame Control Field: 0x40 = Probe Request
  uint8_t frameType = payload[0];
  if (frameType != 0x40) return;

  // Source MAC = octets 10-15
  const uint8_t* srcMac = payload + 10;
  String mac = macToStr(srcMac);
  bool   rnd = isMacRandomized(srcMac);
  int    rssi = ctrl.rssi;

  // SSID probed (IE tag 0)
  String ssid = "";
  if (payload[24] == 0x00) {
    uint8_t ssidLen = payload[25];
    if (ssidLen > 0 && ssidLen < 33) {
      char ssidBuf[33] = {0};
      memcpy(ssidBuf, payload + 26, ssidLen);
      ssid = String(ssidBuf);
    }
  }

  // On publie uniquement les signaux suffisamment proches (filtre bruit lointain)
  if (rssi < -85) return;

  publishDetection("wifi", mac, rssi, rnd, ssid);
}

// ─── BLE Scan callback ────────────────────────────────────────────────────────
class BLECallback : public BLEAdvertisedDeviceCallbacks {
  void onResult(BLEAdvertisedDevice dev) override {
    String mac  = dev.getAddress().toString().c_str();
    int    rssi = dev.getRSSI();
    String name = dev.haveName() ? dev.getName().c_str() : "";

    // Ignore RSSI trop faible
    if (rssi < -85) return;

    uint8_t macBytes[6];
    sscanf(mac.c_str(), "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
           &macBytes[0], &macBytes[1], &macBytes[2],
           &macBytes[3], &macBytes[4], &macBytes[5]);

    publishDetection("ble", mac, rssi, isMacRandomized(macBytes), name);
  }
};

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.printf("\nSentinel ESP32 — ID: %s\n", ESP32_ID);

  // Connexion WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi...");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf(" ok (%s)\n", WiFi.localIP().toString().c_str());

  // MQTT
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);
  mqttReconnect();

  // Promiscuous mode WiFi (probe sniff)
  // Note: on doit quitter STA mode managé temporairement pour le promiscuous
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(probeCallback);
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);  // commence canal 1

  // BLE
  BLEDevice::init("sentinel");
  bleScan = BLEDevice::getScan();
  bleScan->setAdvertisedDeviceCallbacks(new BLECallback(), true);
  bleScan->setActiveScan(false);  // passif = moins de bruit
  bleScan->setInterval(150);
  bleScan->setWindow(100);

  Serial.println("Sentinel ready.");
}

// ─── Loop ────────────────────────────────────────────────────────────────────
uint8_t currentChannel = 1;
unsigned long lastBLEScan = 0;
unsigned long lastChannelHop = 0;

void loop() {
  if (!mqtt.connected()) mqttReconnect();
  mqtt.loop();

  // Channel hopping (1→6→11→1) pour couvrir les 3 canaux non-chevauchants
  if (millis() - lastChannelHop > 500) {
    lastChannelHop = millis();
    currentChannel = (currentChannel == 1) ? 6 : (currentChannel == 6) ? 11 : 1;
    esp_wifi_set_channel(currentChannel, WIFI_SECOND_CHAN_NONE);
  }

  // Scan BLE périodique
  if (millis() - lastBLEScan > LOOP_DELAY_MS) {
    lastBLEScan = millis();
    bleScan->start(BLE_SCAN_SECS, false);
    bleScan->clearResults();
  }
}
