import os
import subprocess
import requests
import psutil
import time
import threading
from flask import Flask, render_template_string, redirect, url_for
from dotenv import load_dotenv

# 設定の読み込み
load_dotenv()
app = Flask(__name__)

# グローバル変数で状態を管理
status = {
    "immich": {"cur": "---", "lat": "---", "upd": False},
    "nextcloud": {"cur": "---", "lat": "---", "upd": False},
    "storage": {"percent": 0, "used": 0, "total": 0},
    "power": {"plugged": True, "battery": 0},
    "logs": []
}

def send_alert(msg):
    """Discord(Android通知)へメッセージを送信"""
    url = os.getenv('DISCORD_WEBHOOK_URL')
    if url:
        try:
            requests.post(url, json={"content": f"🚨 **Server Alert**: {msg}"}, timeout=5)
        except: pass

def get_latest_ver(repo):
    """GitHub APIから最新のタグ名を取得"""
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=5)
        if r.status_code == 200:
            return r.json().get('tag_name', '').lstrip('v')
    except: return "Error"
    return "Error"

def get_nextcloud_current():
    """Nextcloudの稼働バージョンを取得"""
    try:
        container = os.getenv('NEXTCLOUD_CONTAINER_NAME', 'nextcloud-app')
        cmd = f"docker exec {container} php occ -V"
        res = subprocess.check_output(cmd, shell=True).decode().strip()
        return res.split(' ')[2]
    except: return "Unknown"

def get_immich_current():
    """Immichの稼働バージョンを取得"""
    try:
        url = f"{os.getenv('IMMICH_URL')}/api/server/version"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return f"{data['major']}.{data['minor']}.{data['patch']}"
    except: return "Unknown"

def monitor_worker():
    """バックグラウンド監視ループ (5分ごと)"""
    while True:
        # 1. 電源監視 (コンセント抜けチェック)
        battery = psutil.sensors_battery()
        if battery:
            if status["power"]["plugged"] and not battery.power_plugged:
                send_alert(f"コンセントが抜けました！バッテリー駆動中 ({battery.percent}%)")
            status["power"] = {"plugged": battery.power_plugged, "battery": battery.percent}

        # 2. ストレージ監視
        usage = psutil.disk_usage('/')
        status["storage"] = {"percent": usage.percent, "used": usage.used // (1024**3), "total": usage.total // (1024**3)}
        if usage.percent > int(os.getenv('STORAGE_THRESHOLD', 80)):
            send_alert(f"ストレージ容量低下: {usage.percent}% 使用中")

        # 3. バージョン監視 (GitHub比較)
        # Nextcloud
        status["nextcloud"]["cur"] = get_nextcloud_current()
        status["nextcloud"]["lat"] = get_latest_ver("nextcloud/server")
        if status["nextcloud"]["cur"] != status["nextcloud"]["lat"] and status["nextcloud"]["lat"] != "Error":
            if not status["nextcloud"]["upd"]: # 初回検知時のみ通知
                send_alert(f"Nextcloudの更新があります: v{status['nextcloud']['lat']}")
            status["nextcloud"]["upd"] = True

        # Immich
        status["immich"]["cur"] = get_immich_current()
        status["immich"]["lat"] = get_latest_ver("immich-app/immich")
        if status["immich"]["cur"] != status["immich"]["lat"] and status["immich"]["lat"] != "Error":
            if not status["immich"]["upd"]:
                send_alert(f"Immichの更新があります: v{status['immich']['lat']}")
            status["immich"]["upd"] = True

        # 4. システムログ監視 (info以上の最新5件)
        try:
            log_out = subprocess.check_output("journalctl -p info --since '5 min ago' -n 5 --no-pager", shell=True).decode()
            status["logs"] = log_out.split('\n') if log_out else ["異常なし"]
        except: status["logs"] = ["ログ取得エラー"]

        time.sleep(300)

# 監視スレッドの開始
threading.Thread(target=monitor_worker, daemon=True).start()

@app.route('/')
def index():
    # スマホで見やすいようにデザインしたHTML
    html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="60">
        <title>Server Dashboard</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
            .card { background: #1e1e1e; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); border-left: 6px solid #333; }
            .alert { border-left-color: #ff5252; background: #2c1a1a; }
            .ok { border-left-color: #4caf50; }
            h2 { margin-top: 0; font-size: 1.2em; color: #03a9f4; }
            .btn { background: #03a9f4; color: white; border: none; padding: 12px; border-radius: 8px; width: 100%; font-size: 1em; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; }
            .btn-update { background: #ff9800; margin-top: 10px; }
            pre { background: #000; padding: 10px; font-size: 0.8em; overflow-x: auto; color: #00ff00; border-radius: 5px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        </style>
    </head>
    <body>
        <h1>📊 自宅鯖管理</h1>

        <div class="card {{ 'ok' if s['power']['plugged'] else 'alert' }}">
            <h2>⚡ 電源状態</h2>
            <p>{{ '🔌 外部電源接続中' if s['power']['plugged'] else '⚠️ バッテリー駆動中' }}</p>
            <p>残量: {{ s['power']['battery'] }}%</p>
        </div>

        <div class="card">
            <h2>💾 ストレージ</h2>
            <p>使用率: {{ s['storage']['percent'] }}%</p>
            <p>容量: {{ s['storage']['used'] }}GB / {{ s['storage']['total'] }}GB</p>
        </div>

        <div class="card {{ 'alert' if s['nextcloud']['upd'] or s['immich']['upd'] else '' }}">
            <h2>📦 アップデート</h2>
            <p><b>Nextcloud:</b> {{ s['nextcloud']['cur'] }} → <b style="color:#ff9800">{{ s['nextcloud']['lat'] }}</b></p>
            <p><b>Immich:</b> {{ s['immich']['cur'] }} → <b style="color:#ff9800">{{ s['immich']['lat'] }}</b></p>
            {% if s['nextcloud']['upd'] or s['immich']['upd'] %}
                <a href="/update_all" class="btn btn-update">一括アップデート実行</a>
            {% else %}
                <p style="color:#4caf50">✅ すべて最新です</p>
            {% endif %}
        </div>

        <div class="card">
            <h2>📜 システムログ (Info+)</h2>
            <pre>{% for log in s['logs'] %}{{ log }}\n{% endfor %}</pre>
        </div>

    </body>
    </html>
    """
    return render_template_string(html, s=status)

@app.route('/update_all')
def update_all():
    """
    一括アップデートを実行するルート
    ※実際の環境に合わせてパスやdocker-composeのコマンドを調整してください
    """
    send_alert("システムの自動更新を開始します...")
    
    # ここに実際の更新コマンドを記述（例）
    # subprocess.Popen("docker-compose pull && docker-compose up -d", shell=True, cwd="/home/sogo/server")
    
    return redirect(url_for('index'))

if __name__ == "__main__":
    # 外部（スマホ）からアクセスできるように 0.0.0.0 で起動
    app.run(host='0.0.0.0', port=5000)