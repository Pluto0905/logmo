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


import os

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


async def fetch_immich_versions():
    immich_url = os.getenv("IMMICH_URL", "http://localhost:2283").rstrip("/") #urlの末尾から"/"を取り除く
    current_version = None
    latest_version = None
    error = None

    async with httpx.AsyncClient(timeout=10.0) as client: #httpリクエストを送るための道具. 10.0たっても返事がなければ失敗とする
        try:
            current_res = await client.get(f"{immich_url}/api/server/version")
            
            #with open("/tmp/logmo_debug.log", "a") as f:
             #   f.write(f"DEBUG: Status={current_res.status_code}, URL={immich_url}/api/server/version\n")
            
            current_res.raise_for_status() #200でない場合、例外を発生させてexceptへ飛ぶ
            current_payload = current_res.json() #current_resというhttpレスポンス本文をjsonに変換して、適切にpythonに対応した型として代入される
            
            #with open("/tmp/logmo_debug.log", "a") as f:
             #   f.write(f"DEBUG: current_payload={current_payload}\n")
              #  f.write(f"DEBUG: types - major:{type(current_payload.get('major'))}, minor:{type(current_payload.get('minor'))}, patch:{type(current_payload.get('patch'))}\n")
            
            if isinstance(current_payload, dict): #current_payloadがdict型かどうか
                major = current_payload.get("major")
                minor = current_payload.get("minor")
                patch = current_payload.get("patch")
                if all(isinstance(v, int) for v in (major, minor, patch)):
                    current_version = f"v{major}.{minor}.{patch}"
        except Exception as e:
            error = f"current_version_error: {e}"
            
            #with open("/tmp/logmo_debug.log", "a") as f:
             #   f.write(f"DEBUG: Exception in current_version - {e}\n")

        try:
            latest_res = await client.get(
                "https://api.github.com/repos/immich-app/immich/releases/latest",
                headers={"Accept": "application/vnd.github+json"}, #application/vnd.github+json ←というデータ形式しか受け付けませんよと言っている
            )
            latest_res.raise_for_status()
            latest_payload = latest_res.json()
            if isinstance(latest_payload, dict):
                tag = latest_payload.get("tag_name")
                if isinstance(tag, str) and tag.strip(): #文字列型かつ空白でない
                    latest_version = tag.strip() #文字列の前後から空白を除いたもの
        except Exception as e:
            if error:
                error = f"{error}; latest_version_error: {e}" #current_versionの方のエラーを追加している。余談だが;にはそういう意味でつかわれる
            else:
                error = f"latest_version_error: {e}"

    return {
        "immich_current_version": current_version,
        "immich_latest_version": latest_version,
        "immich_error": error,
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


@app.get("/immich/version")
async def get_immich_version():
    return await fetch_immich_versions()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket): #Websocket型のデータがwebsocketという変数にFastAPIが自動で代入する。WebSocketとはhttpのような通信方式の名前
    await websocket.accept()

    while True:
        storage = fetch_storage()
        power = fetch_power()
        immich = await fetch_immich_versions()

        await websocket.send_json({
            **storage, #**で２つの辞書型のデータを合体させている
            **power,
            **immich,
        })

        await asyncio.sleep(60)