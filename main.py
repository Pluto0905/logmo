from flask import Flask, render_template_string
import shutil
import requests

app = Flask(__name__)

# --- 設定：自分の現在のバージョン ---
MY_IMMICH_VERSION = "v1.120.0" 

def get_immich_version():
    try:
        url = "https://api.github.com/repos/immich-app/immich/releases/latest"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get("tag_name", "取得失敗")
    except:
        return "エラー"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Logmo Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; text-align: center; background: #f4f7f6; padding: 50px 20px; }
        .card { background: white; padding: 25px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 10px rgba(0,0,0,0.1); min-width: 300px; margin: 10px; vertical-align: top; }
        h1 { color: #333; font-size: 1.1rem; margin-bottom: 20px; }
        .value { font-size: 2.5rem; font-weight: bold; color: #2ecc71; }
        .version { color: #3498db; font-size: 1.5rem; font-weight: bold; margin-bottom: 10px; }
        .status { padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; font-weight: bold; }
        .update-needed { background: #ff7675; color: white; }
        .up-to-date { background: #55efc4; color: #00b894; }
        .info { color: #777; margin-top: 15px; font-size: 0.8rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>サーバー使用率</h1>
        <div class="value">{{ percent }}%</div>
        <div class="info">{{ free_gb }} GB / {{ total_gb }} GB</div>
    </div>

    <div class="card">
        <h1>Immich アップデート確認</h1>
        <div class="version">最新: {{ latest_ver }}</div>
        <div class="version" style="color:#777">現在: {{ current_ver }}</div>
        
        {% if latest_ver != current_ver and latest_ver != "エラー" %}
            <span class="status update-needed">アップデートがあります！</span>
        {% else %}
            <span class="status up-to-date">最新です</span>
        {% endif %}
        
        <div class="info">GitHub APIより取得</div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    total, used, free = shutil.disk_usage("/")
    percent = round(used / total * 100, 1)
    
    latest_ver = get_immich_version()
    
    return render_template_string(HTML_TEMPLATE, 
                                 percent=percent, 
                                 free_gb=free // (2**30), 
                                 total_gb=total // (2**30), 
                                 latest_ver=latest_ver,
                                 current_ver=MY_IMMICH_VERSION)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)