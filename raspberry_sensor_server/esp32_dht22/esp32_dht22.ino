#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <time.h>

const char *WIFI_SSID = "SEU_WIFI";
const char *WIFI_PASSWORD = "SUA_SENHA";
const char *SERVER_HOST = "192.168.1.100";
const uint16_t SERVER_PORT = 8080;
const char *SENSOR_ID = "esp32-1"; // Use esp32-2 no segundo dispositivo
const char *API_KEY = ""; // Igual a SENSOR_API_KEY no Raspberry Pi

#define DHT_PIN 4
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);
const unsigned long SEND_INTERVAL_MS = 30000;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP do ESP32: ");
  Serial.println(WiFi.localIP());
}

String isoTimestamp() {
  struct tm timeInfo;
  if (!getLocalTime(&timeInfo, 1000)) {
    time_t now = time(nullptr);
    char buffer[25];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", gmtime(&now));
    return String(buffer);
  }

  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(buffer);
}

void setup() {
  Serial.begin(115200);
  dht.begin();
  connectWiFi();

  configTzTime("UTC0", "pool.ntp.org", "time.nist.gov");
  Serial.println("Sincronizando horario...");
}

void sendReading() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Falha na leitura do DHT22");
    return;
  }

  char payload[512];
  snprintf(
    payload,
    sizeof(payload),
    "{\"sensor_id\":\"%s\",\"timestamp\":\"%s\",\"temperature_c\":%.2f,\"humidity_percent\":%.2f}",
    SENSOR_ID,
    isoTimestamp().c_str(),
    temperature,
    humidity
  );

  HTTPClient http;
  String url = String("http://") + SERVER_HOST + ":" + SERVER_PORT + "/readings";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  if (strlen(API_KEY) > 0) {
    http.addHeader("X-API-Key", API_KEY);
  }

  int statusCode = http.POST((uint8_t *)payload, strlen(payload));
  Serial.printf("Sensor=%s temperatura=%.1f C umidade=%.1f%% HTTP=%d\n",
                SENSOR_ID, temperature, humidity, statusCode);

  if (statusCode < 0) {
    Serial.println(http.errorToString(statusCode));
  } else if (statusCode < 200 || statusCode >= 300) {
    Serial.println(http.getString());
  }
  http.end();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  static unsigned long lastSend = 0;
  unsigned long now = millis();
  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;
    sendReading();
  }

  delay(100);
}
