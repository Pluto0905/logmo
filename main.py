#ストレージ情報を取得するための標準ライブラリ
import shutil

#webアプリの土台。このURLにアクセスされたらこの処理をする、というルールを追加していく。
from fastapi import FastAPI, WebSocket

#静的ファイルを配信する
from fastapi.staticfiles import StaticFiles

#ファイルをブラウザに返す
from fastapi.responses import FileResponse

#非同期処理を行う。
import asyncio

#httpリクエストを実行する
import httpx

#yield のある非同期関数を async with で使えるように変換するものらしい
from contextlib import asynccontextmanager


def fetch_storage():
    usage = shutil.disk_usage("/")
    return {
        "total_gb": round(usage.total / (1024 ** 3), 1),
        "used_gb": round(usage.used / (1024 ** 3), 1),
        "free_gb": round(usage.free / (1024 ** 3), 1),
    }


def fetch_power():
    with open("/sys/class/power_supply/AC/online") as f: #ファイルを開いてfに入れてファイルを閉じる
        status = f.read().strip() #文字列を読み取り、余分な文字を取り除く
    return {
        "ac_connected": status == "1" #真なら{ac_connected: True}を返す。偽ならFalse
    }


async def monitor():
    last_ac_status = True
    last_storage_notified = False

    while True:
        try: #このブロックの中でpythonがException系を吐いたらexceptに飛ぶ。そしてそのインスタンスがe。try-except処理でエラーが出ても６０秒おきにmonitor()が実行するようになっている。もしこの処理がないと、無限ループ内なので、エラーの際そこで止まり続ける。
            power = fetch_power()
            storage = fetch_storage()

            if last_ac_status and not power["ac_connected"]:
                await send_notification("⚠️ AC電源が切断されました！")
            last_ac_status = power["ac_connected"]

            used_percent = storage["used_gb"] / storage["total_gb"] * 100
            if used_percent >= 90 and not last_storage_notified:
                await send_notification(f"⚠️ ストレージが{round(used_percent, 1)}%に達しました！")
                last_storage_notified = True
            elif used_percent < 90:
                last_storage_notified = False
        
        except Exception as e: #エラーがException系ならここ（except）に飛ぶ。そしてそのインスタンスがe
            print(f"monitor error: {e}") #内部にロギングされてるらしい

        await asyncio.sleep(60)


async def send_notification(message: str):
    async with httpx.AsyncClient() as client: #clientというhttpリクエストを送るインスタンスを作る
        await client.post(
            "http://localhost:8090/logmo", #ntfyサーバーのlogmoトピックのURL
            content=message.encode("utf-8"),
            headers={
                "Title": "logmo",
                "Icon": "https://raw.githubusercontent.com/Pluto0905/logmo/main/static/icon.jpg",
            }
        )


@asynccontextmanager #FastAPIが内部でasync withでこの関数を呼び出せるようにするためらしい
async def lifespan(app: FastAPI):
    asyncio.create_task(monitor())
    yield #FastAPIのlifespan関連のドキュメントにこう書けと書いてある。動作の主がuvicornが起動したapp(FastAPI)からuvicornに戻る。ブラウザからのリクエストを受け付け始める。


#webアプリの司令塔を作成。インスタンスを作成するという。司令塔を作成する際の追加オプションみたいな感じで、定義したlifespan()を引数に。main.pyでappに情報を詰め込み、そのappを基にuvicornがASGIサーバーを実行する
app = FastAPI(lifespan=lifespan)


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
        storage = fetch_storage()
        power = fetch_power()

        await websocket.send_json({
            **storage, #**で２つの辞書型のデータを合体させている
            **power,
        })

        await asyncio.sleep(60)