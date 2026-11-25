#include <Arduino.h>
#include <DHT.h>
#include <math.h>

#define DHT_PIN 4
#define DHT_TYPE DHT22

DHT dht(DHT_PIN, DHT_TYPE);

const unsigned long READ_INTERVAL_MS = 2000;

float calculateDewPoint(float temperatureC, float humidityPercent);

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("========================================");
  Serial.println("Teste independente do sensor DHT22");
  Serial.printf("Placa: ESP32 | Pino de dados: GPIO %d\n", DHT_PIN);
  Serial.println("========================================");

  dht.begin();
  Serial.println("Sensor inicializado.");
  Serial.println("Aguardando primeira leitura...");
}

void loop() {
  float humidity = dht.readHumidity();
  float temperatureC = dht.readTemperature();

  if (isnan(humidity) || isnan(temperatureC)) {
    Serial.println("[ERRO] Falha na leitura do DHT22.");
    Serial.println("[VERIFIQUE] VCC=3V3, GND=GND, DATA=GPIO 4.");
  } else {
    float temperatureF = dht.readTemperature(true);

    Serial.println("----------------------------------------");
    Serial.printf("[OK] Umidade: %.2f %%\n", humidity);
    Serial.printf("[OK] Temperatura: %.2f C\n", temperatureC);

    if (!isnan(temperatureF)) {
      Serial.printf("[OK] Temperatura: %.2f F\n", temperatureF);
    }

    Serial.printf("[INFO] Ponto de orvalho aproximado: %.2f C\n",
                  calculateDewPoint(temperatureC, humidity));
  }

  delay(READ_INTERVAL_MS);
}

float calculateDewPoint(float temperatureC, float humidityPercent) {
  const float A = 17.27;
  const float B = 237.7;

  float alpha =
    (A * temperatureC) / (B + temperatureC) +
    log(humidityPercent / 100.0);

  return (B * alpha) / (A - alpha);
}
