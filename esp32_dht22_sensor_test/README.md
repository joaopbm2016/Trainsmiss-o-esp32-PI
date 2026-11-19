# Teste direto do DHT22 no ESP32

Este programa permite testar o DHT22 apenas pela conexão USB do ESP32.
Ele não usa Wi-Fi, servidor, HTTP, banco de dados ou outro sensor.

## Conexões

| DHT22 | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| DATA | GPIO 4 |

Recomenda-se também uma resistência de `10 kΩ` entre DATA e VCC.

## Biblioteca

Na IDE do Arduino, instale:

1. `DHT sensor library`, da Adafruit.
2. `Adafruit Unified Sensor`.

## Executar

1. Conecte o ESP32 ao computador por cabo USB.
2. Abra `esp32_dht22_sensor_test.ino`.
3. Selecione a placa ESP32 em `Ferramentas > Placa`.
4. Selecione a porta USB em `Ferramentas > Porta`.
5. Clique em `Verificar`.
6. Clique em `Upload`.
7. Abra `Ferramentas > Monitor Serial`.
8. Configure o Monitor Serial para `115200 baud`.

A leitura deve aparecer a cada dois segundos.

Exemplo de leitura correta:

```text
[OK] Umidade: 55.20 %
[OK] Temperatura: 24.50 C
```

Exemplo de falha:

```text
[ERRO] Falha na leitura do DHT22.
[VERIFIQUE] VCC=3V3, GND=GND, DATA=GPIO 4.
```
