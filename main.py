from flask import Flask, render_template_string
import shutil

app = Flask(__name__)

# ブラウザでアクセスした時に表示される「見た目（HTML）」
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Logmo - Storage Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; text-align: center; background: #f4f7f6; padding-top: 50px; }
        .card { background: white; padding: 20px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .usage { font-size: 3rem; font-weight: bold; color: #e74c3c; }
        .info { color: #777; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>サーバー使用率</h1>
        <div class="usage">{{ percent }}%</div>
        <div class="info">空き容量: {{ free_gb }} GB / 全容量: {{ total_gb }} GB</div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    # ストレージ情報を取得
    total, used, free = shutil.disk_usage("/")
    
    # データを整理
    total_gb = total // (2**30)
    used_gb = used // (2**30)
    free_gb = free // (2**30)
    percent = round(used / total * 100, 1)
    
    # HTMLにデータを流し込んで表示する
    return render_template_string(HTML_TEMPLATE, percent=percent, free_gb=free_gb, total_gb=total_gb)

if __name__ == '__main__':
    # サーバーを起動（port 5000番を使用）
    app.run(host='0.0.0.0', port=5000)