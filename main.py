import shutil
import time
from datetime import datetime

# 1. ストレージの情報を調べて表示する「機能」を作る
def check_storage():
    # ディスクの使用状況を取得
    total, used, free = shutil.disk_usage("/")
    
    # 使用率をパーセントで計算
    percent = used / total * 100
    
    # 現在の時刻を読みやすい形式にする
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 画面に結果を表示する
    print(f"[{now}] 使用率: {percent:.1f}% (空き: {free // (2**30)} GB)")

# 2. ここからがプログラムの「本番（実行）」
print("starting logmo...")

try:
    while True:         # ずっと繰り返す（無限ループ）
        check_storage() # 上で作った「機能」を実行する
        time.sleep(5)   # 5秒間お休みする
except KeyboardInterrupt:
    # Ctrl + C が押されたらここに来る
    print("\n監視を終了します。お疲れ様でした！")