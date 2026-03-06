#ストレージ情報を取得するための標準ライブラリ
import shutil

#webアプリの土台。このURLにアクセスされたらこの処理をする、というルールを追加していく。
from fastapi import FastAPI, WebSocket

#静的ファイルを配信する
from fastapi.staticfiles import StaticFiles

#ファイルをブラウザに返す
from fastapi.responses import FileResponse

import asyncio


def fetch_storage():
    usage = shutil.disk_usage("/")
    return {
        "total_gb": round(usage.total / (1024 ** 3), 1),
        "used_gb": round(usage.used / (1024 ** 3), 1),
        "free_gb": round(usage.free / (1024 ** 3), 1),
    }


#webアプリの司令塔、インスタンスを作成する
app = FastAPI()

#urlが/staticの場合、staticフォルダを見てね、ってことらしい
app.mount("/static", StaticFiles(directory="static"), name="static")


#関数をデコレートしてwebアプリの一部としてのインターフェース(/がAPI)となっている
@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.get("/storage")
def get_storage():
    return fetch_storage()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket): #Websocket型のデータがwebsocketという変数にFastAPIが自動で代入する。WebSocketとはhttpのような通信方式の名前
    await websocket.accept()
    while True:
        await websocket.send_json(fetch_storage())
        await asyncio.sleep(5)