#!/usr/bin/env python3

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SENSOR_IDS = ("esp32-1", "esp32-2")
TIMEOUT_SECONDS = 60
SERVER_STARTED_AT = datetime.now(timezone.utc)
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8080"))
DB_FILE = Path(os.getenv("DB_FILE", str(Path(__file__).parent / "readings.db")))
API_KEY = os.getenv("SENSOR_API_KEY", "").strip()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def connect_db():
    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection
    
def get_sensor_status():
    now = datetime.now(timezone.utc)

    with connect_db() as connection:
        rows = connection.execute(
            """
            SELECT sensor_id, MAX(received_at) AS last_received
            FROM readings
            WHERE sensor_id IN (?, ?)
            GROUP BY sensor_id
            """,
            SENSOR_IDS,
        ).fetchall()

    latest = {row["sensor_id"]: row["last_received"] for row in rows}
    statuses = {}

    for sensor_id in SENSOR_IDS:
        last_received = latest.get(sensor_id)
        last_time = (
            datetime.fromisoformat(last_received.replace("Z", "+00:00"))
            if last_received
            else SERVER_STARTED_AT
        )
        seconds_without_data = int((now - last_time).total_seconds())

        statuses[sensor_id] = {
            "online": seconds_without_data < TIMEOUT_SECONDS,
            "last_received": last_received,
            "seconds_without_data": seconds_without_data,
        }
     return statuses

def monitor_sensors():
    previous = {}

    while True:
        statuses = get_sensor_status()

        for sensor_id, status in statuses.items():
            online = status["online"]

            if sensor_id not in previous and not online:
                print(f"AVISO: {sensor_id} não enviou dados há 60 segundos.")
            elif sensor_id in previous and previous[sensor_id] != online:
                message = "voltou a enviar dados" if online else "parou de enviar dados"
                print(f"AVISO: {sensor_id} {message}.")

            previous[sensor_id] = online

        time.sleep(5)

def init_db():
    with connect_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                sensor_timestamp TEXT,
                temperature_c REAL,
                humidity_percent REAL,
                received_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_sensor ON readings(sensor_id)"
        )


class Handler(BaseHTTPRequestHandler):
    server_version = "RaspberrySensorServer/1.0"

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def authorized(self):
        if not API_KEY:
            return True
        return self.headers.get("X-API-Key") == API_KEY

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.send_json(200, {"status": "ok", "time": utc_now()})
            return
        
        if parsed.path == "/status":
    	    self.send_json(200, {"sensors": get_sensor_status()})
    	    return


        if parsed.path == "/readings":
            params = parse_qs(parsed.query)
            sensor_id = params.get("sensor_id", [None])[0]
            try:
                limit = min(max(int(params.get("limit", ["100"])[0]), 1), 1000)
            except ValueError:
                limit = 100

            with connect_db() as connection:
                if sensor_id:
                    rows = connection.execute(
                        "SELECT * FROM readings WHERE sensor_id=? "
                        "ORDER BY id DESC LIMIT ?",
                        (sensor_id, limit),
                    ).fetchall()
                else:
                    rows = connection.execute(
                        "SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)
                    ).fetchall()

            self.send_json(200, {"readings": [dict(row) for row in rows]})
            return

        if parsed.path == "/" or parsed.path == "/index.html":
            html = DASHBOARD.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

        self.send_json(404, {"error": "endpoint_not_found"})

    def do_POST(self):
        if urlparse(self.path).path != "/readings":
            self.send_json(404, {"error": "endpoint_not_found"})
            return
        if not self.authorized():
            self.send_json(401, {"error": "invalid_api_key"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("invalid_content_length")
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "invalid_json"})
            return

        sensor_id = payload.get("sensor_id")
        temperature = payload.get("temperature_c")
        humidity = payload.get("humidity_percent")

        if not isinstance(sensor_id, str) or not sensor_id.strip():
            self.send_json(400, {"error": "sensor_id_required"})
            return
        if not isinstance(temperature, (int, float)) or not isinstance(humidity, (int, float)):
            self.send_json(400, {"error": "temperature_c_and_humidity_percent_required"})
            return
        if not (-100 <= float(temperature) <= 150):
            self.send_json(400, {"error": "temperature_c_out_of_range"})
            return
        if not (0 <= float(humidity) <= 100):
            self.send_json(400, {"error": "humidity_percent_out_of_range"})
            return

        sensor_timestamp = payload.get("timestamp")
        if not isinstance(sensor_timestamp, str):
            sensor_timestamp = utc_now()

        with connect_db() as connection:
            cursor = connection.execute(
                """
                INSERT INTO readings
                (sensor_id, sensor_timestamp, temperature_c, humidity_percent, received_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    sensor_id.strip()[:50],
                    sensor_timestamp[:100],
                    float(temperature),
                    float(humidity),
                    utc_now(),
                ),
            )
            reading_id = cursor.lastrowid

        self.send_json(
            201,
            {
                "id": reading_id,
                "sensor_id": sensor_id.strip(),
                "received_at": utc_now(),
            },
        )


    def log_message(self, fmt, *args):
        print(f"{utc_now()} {self.client_address[0]} {fmt % args}")


DASHBOARD = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Leituras dos sensores</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #ddd; padding: .7rem; text-align: left; }
    th { background: #f5f5f5; }
  </style>
</head>
<body>
  <h1>Leituras dos sensores</h1>
  <p>ESP 1: <strong id="esp32-1-status">Verificando...</strong></p>
  <p>ESP 2: <strong id="esp32-2-status">Verificando...</strong></p>
  <p id="status">Atualizando...</p>

  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>Sensor</th>
        <th>Temperatura</th>
        <th>Umidade</th>
        <th>Recebido</th>
      </tr>
    </thead>
    <tbody id="rows"></tbody>
  </table>

  <script>
    async function update() {
      const response = await fetch('/readings?limit=100');
      const data = await response.json();

      document.querySelector('#rows').innerHTML = data.readings.map(r => {
        const receivedAt = new Date(r.received_at).toLocaleString('pt-BR', {
          timeZone: 'America/Sao_Paulo'
        });

        return '<tr><td>' + r.id + '</td><td>' + r.sensor_id + '</td><td>' +
          r.temperature_c.toFixed(1) + ' C</td><td>' + r.humidity_percent.toFixed(1) +
          '%</td><td>' + receivedAt + '</td></tr>';
      }).join('');

      document.querySelector('#status').textContent =
        'Atualizado em ' + new Date().toLocaleString('pt-BR', {
          timeZone: 'America/Sao_Paulo'
        });
    }

    async function updateSensorStatus() {
      const response = await fetch('/status');
      const data = await response.json();

      for (const id of ['esp32-1', 'esp32-2']) {
        const sensor = data.sensors[id];
        document.querySelector('#' + id + '-status').textContent = sensor.online
          ? 'Online'
          : 'SEM DADOS há ' + sensor.seconds_without_data + ' segundos';
      }
    }

    update();
    updateSensorStatus();
    setInterval(update, 10000);
    setInterval(updateSensorStatus, 5000);
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    init_db()
    threading.Thread(target=monitor_sensors, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Servidor iniciado em http://0.0.0.0:{PORT}")
    server.serve_forever()
