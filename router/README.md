# Raspberry Pi como roteador dos ESP32

Esta configuracao cria uma rede Wi-Fi exclusiva para os ESP32 e compartilha
a Internet da conexao Ethernet.

## O que sera criado

- Rede Wi-Fi configuravel pelo script
- Gateway dos ESP32: `192.168.50.1`
- DHCP: `192.168.50.20` a `192.168.50.200`
- NAT para encaminhar trafego pela interface Ethernet
- Encaminhamento IPv4 ativado no Raspberry Pi

## Antes de executar

O Raspberry Pi precisa estar conectado a Internet pela Ethernet, por exemplo:

```text
Internet --> roteador da casa --> Ethernet --> Raspberry Pi
                                          WLAN --> ESP32
```

Use a interface Wi-Fi integrada do Raspberry Pi como ponto de acesso.
Nao use a mesma rede Wi-Fi da interface Ethernet.

Consulte as interfaces:

```bash
ip -br link
```

Normalmente:

```text
eth0 = Ethernet
wlan0 = Wi-Fi
```

Nao execute esta configuracao remotamente por SSH na rede Wi-Fi que sera
convertida em ponto de acesso.

## Instalar

No Raspberry Pi:

```bash
cd ~/raspberry_sensor_server/router
chmod +x setup_router.sh
sudo bash setup_router.sh
```

Informe:

- Nome da rede Wi-Fi dos ESP32
- Senha com pelo menos oito caracteres
- Interface Wi-Fi, normalmente `wlan0`
- Interface Ethernet com Internet, normalmente `eth0`

O script instala `hostapd`, `dnsmasq` e `nftables`.

## Configurar o servidor de sensores

O servidor pode continuar na porta `8080`. Reinicie-o depois da configuracao:

```bash
sudo systemctl restart raspberry-sensor-server
```

No painel web do proprio Raspberry Pi:

```text
http://192.168.50.1:8080
```

No codigo normal dos ESP32, configure o servidor:

```cpp
const char *WIFI_SSID = "NOME_DA_REDE_CRIADA";
const char *WIFI_PASSWORD = "SENHA_DA_REDE";
const char *SERVER_HOST = "192.168.50.1";
const uint16_t SERVER_PORT = 8080;
```

Identificadores separados:

```cpp
const char *SENSOR_ID = "esp32-1";
```

No segundo ESP32:

```cpp
const char *SENSOR_ID = "esp32-2";
```

## Verificar

Verifique os processos:

```bash
sudo systemctl status hostapd
sudo systemctl status dnsmasq
sudo systemctl status nftables
sudo systemctl status esp32-router-ip
```

Verifique o IP interno:

```bash
ip -br address
```

Verifique se o Wi-Fi esta transmitindo:

```bash
sudo systemctl status hostapd --no-pager
```

Verifique se um ESP32 recebeu IP:

```bash
sudo cat /var/lib/misc/dnsmasq.leases
```

Teste o encaminhamento no Raspberry Pi:

```bash
sudo sysctl net.ipv4.ip_forward
sudo nft list ruleset
```

## Remover ou desativar temporariamente

```bash
sudo systemctl disable --now hostapd
sudo systemctl disable --now dnsmasq
sudo systemctl disable --now esp32-router-ip
sudo systemctl stop nftables
```
