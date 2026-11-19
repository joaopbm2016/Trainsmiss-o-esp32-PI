# Servidor de sensores ESP32 no Raspberry Pi

Sistema local para receber dados de dois ESP32 com DHT22 pela rede Wi-Fi.
O Raspberry Pi grava temperatura, umidade, hora enviada pelo ESP32 e hora de recebimento em SQLite.

## Valores assumidos

- DHT22 no GPIO 4 de cada ESP32
- Porta HTTP do Raspberry Pi: `8080`
- Os ESP32 enviam a leitura a cada 30 segundos
- Rede local sem senha da API por padrão

## No Raspberry Pi

```bash
cd /root/raspberry_sensor_server
python3 server.py
```

Para iniciar em segundo plano e configurar como serviço:

```bash
chmod +x install.sh
./install.sh
```

Descubra o endereço IP do Raspberry Pi:

```bash
hostname -I
```

Acompanhe as leituras em `http://IP_DO_RASPBERRY:8080` e a API em
`http://IP_DO_RASPBERRY:8080/readings`.

## Opcional: proteger a API

Antes de iniciar o servidor:

```bash
SENSOR_API_KEY='chave-secreta' python3 server.py
```

Para o serviço, adicione `Environment=SENSOR_API_KEY=chave-secreta` na seção
`[Service]` de `/etc/systemd/system/raspberry-sensor-server.service` e reinicie:

```bash
sudo systemctl restart raspberry-sensor-server
```

Configure o mesmo valor em `API_KEY` nos dois códigos Arduino.

## Nos ESP32

1. Instale na IDE do Arduino o suporte a placa ESP32.
2. Instale a biblioteca `DHT sensor library` de Adafruit.
3. Instale também a dependência `Adafruit Unified Sensor`.
4. Abra `esp32_dht22/esp32_dht22.ino`.
5. Configure `WIFI_SSID`, `WIFI_PASSWORD`, `SERVER_HOST` e `API_KEY`.
6. No primeiro ESP32 configure `SENSOR_ID = "esp32-1"`; no segundo use `"esp32-2"`.
7. Conecte o DHT22: VCC -> 3V3, GND -> GND e DATA -> GPIO 4.

Não use a porta 5V do ESP32 para alimentar o DHT22 caso a fonte do projeto seja limitada.

## Estrutura atual do projeto

```text
raspberry_sensor_server/
  server.py
  install.sh
  esp32_dht22/
    esp32_dht22.ino
router/
  setup_router.sh
  README.md
```

## Raspberry Pi como roteador

O projeto também inclui um instalador que transforma o Raspberry Pi em ponto de
acesso Wi-Fi para os ESP32, com DHCP e compartilhamento da Internet pela
conexão Ethernet.

Execute no Raspberry Pi:

```bash
cd raspberry_sensor_server/..
cd router
sudo bash setup_router.sh
```

Consulte `router/README.md` para os requisitos de interface, a configuração da
rede e os testes de funcionamento.