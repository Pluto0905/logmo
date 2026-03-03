#ストレージ情報を取得するための標準ライブラリ
import shutil

#webアプリの土台。このURLにアクセスされたらこの処理をする、というルールを追加していく。
from fastapi import FastAPI

#静的ファイルを配信する
from fastapi.staticfiles import StaticFiles

#ファイルをブラウザに返す
from fastapi.responses import FileResponse


#webアプリの司令塔、インスタンスを作成する
app = FastAPI()

#urlが/staticの場合、staticフォルダを見てね、ってことらしい
app.mount("/static", StaticFiles(directory="static"), name="static")


#関数をデコレートしてwebアプリの一部としてのインターフェースとなっている
@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.get("/storage")
def get_storage():
    usage = shutil.disk_usage("/")

    total_gb = usage.total / (1024 ** 3)
    used_gb = usage.used / (1024 ** 3)
    free_gb = usage.free / (1024 ** 3)
    return {
        "total_gb": round(total_gb, 1),
        "used_gb": round(used_gb, 1),
        "free_gb": round(free_gb, 1),
    }