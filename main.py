import os
import requests
from flask import Flask
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# さっき作ったバージョン取得関数を少し改造
def get_version():
    url = f"{os.getenv('IMMICH_URL')}/api/server/about"
    headers = {'x-api-key': os.getenv('IMMICH_API_KEY')}
    try:
        r = requests.get(url, headers=headers)
        return r.json().get('version', '取得失敗')
    except:
        return "サーバーに接続できません"

@app.route('/')
def home():
    version = get_version()
    return f"<h1>Immich Status</h1><p>Current Version: {version}</p>"

if __name__ == "__main__":
    # 0.0.0.0にすることで、外部（スマホ）からの接続を受け付けます
    app.run(host='0.0.0.0', port=5000)