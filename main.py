import os
import requests
import psutil
from flask import Flask
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# --- 設定（通知しきい値など） ---
STORAGE_THRESHOLD = 80  # 80%を超えたら警告

def get_immich_version():
    url = f"{os.getenv('IMMICH_URL')}/api/server/about"
    headers = {'x-api-key': os.getenv('IMMICH_API_KEY')}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        return r.json().get('version', '取得失敗')
    except:
        return "接続エラー"

def get_nextcloud_version():
    # Nextcloudはセキュリティ上の理由でAPI取得が複雑なため、
    # まずはプレースホルダとして作成（環境変数にURL等を設定する想定）
    return "v28.0.2 (Sample)"

def get_storage_info():
    # サーバーのルートディレクトリ（/）のストレージ情報を取得
    usage = psutil.disk_usage('/')
    return {
        "total": usage.total // (2**30),      # GB単位
        "used": usage.used // (2**30),
        "percent": usage.percent
    }

@app.route('/')
def home():
    immich_ver = get_immich_version()
    nc_ver = get_nextcloud_version()
    storage = get_storage_info()
    
    # ストレージ警告の判定
    storage_style = "color: red; font-weight: bold;" if storage['percent'] > STORAGE_THRESHOLD else ""

    # HTMLの中身（metaタグで30秒ごとに自動リロード設定）
    return f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="30">
            <title>My Server Dashboard</title>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; background: #f4f4f4; }}
                .card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <h1>🖥️ My Server Monitor</h1>
            
            <div class="card">
                <h2>📦 Software Versions</h2>
                <p><strong>Immich:</strong> {immich_ver}</p>
                <p><strong>Nextcloud:</strong> {nc_ver}</p>
            </div>

            <div class="card">
                <h2>💾 Storage Info</h2>
                <p style="{storage_style}">
                    Usage: {storage['percent']}% ({storage['used']}GB / {storage['total']}GB)
                </p>
                {"<p style='color:red;'>⚠️ WARNING: Storage is almost full!</p>" if storage['percent'] > STORAGE_THRESHOLD else ""}
            </div>

            <p><small>Last updated: 自動更新中（30秒毎）</small></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)