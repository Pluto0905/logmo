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

import re

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


def normalize_version_text(version_text):
    if not isinstance(version_text, str):
        return None

    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_text)
    if not match:
        return None

    return f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"


async def fetch_immich_versions():
    immich_url = os.getenv("IMMICH_URL", "http://localhost:2283").rstrip("/") #urlの末尾から"/"を取り除く
    api_key = os.getenv("IMMICH_API_KEY") #version-checkはログインが必要なので、server.versionCheck権限だけのAPIキーを使う
    current_version = None
    latest_version = None
    errors = []

    async with httpx.AsyncClient(timeout=10.0) as client: #httpリクエストを送るための道具. 10.0たっても返事がなければ失敗とする
        try:
            current_res = await client.get(f"{immich_url}/api/server/version")
            current_res.raise_for_status() #200でない場合、例外を発生させてexceptへ飛ぶ
            current_payload = current_res.json() #current_resというhttpレスポンス本文をjsonに変換して、適切にpythonに対応した型として代入される

            if isinstance(current_payload, dict): #current_payloadがdict型かどうか
                major = current_payload.get("major")
                minor = current_payload.get("minor")
                patch = current_payload.get("patch")
                if all(isinstance(v, int) for v in (major, minor, patch)):
                    current_version = f"v{major}.{minor}.{patch}"
        except Exception as e:
            errors.append(f"current_version_error: {e}")

        #Immich自身が1時間に1回確認している最新バージョンを読むだけなので、GitHubには問い合わせない
        try:
            if not api_key:
                raise ValueError("IMMICH_API_KEY is not set")

            latest_res = await client.get(
                f"{immich_url}/api/server/version-check",
                headers={"x-api-key": api_key},
            )
            latest_res.raise_for_status()
            latest_payload = latest_res.json()
            if isinstance(latest_payload, dict):
                latest_version = normalize_version_text(latest_payload.get("releaseVersion"))

            if not latest_version: #Immichの管理画面でバージョンチェックが無効だとreleaseVersionがnullになる
                raise ValueError("releaseVersion is empty (is version check enabled in Immich?)")
        except Exception as e:
            errors.append(f"latest_version_error: {e}")

    return {
        "immich_current_version": current_version,
        "immich_latest_version": latest_version,
        "immich_error": "; ".join(errors) or None, #エラーが複数あれば;でつなぐ。なければNone
    }


async def fetch_nextcloud_versions():
    nextcloud_url = os.getenv("NEXTCLOUD_URL", "http://localhost:8080").rstrip("/")
    current_version = None
    latest_version = None
    errors = []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            current_res = await client.get(f"{nextcloud_url}/status.php")
            current_res.raise_for_status()
            current_payload = current_res.json()

            if isinstance(current_payload, dict):
                current_raw_version = current_payload.get("versionstring") or current_payload.get("version")
                current_version = normalize_version_text(current_raw_version)

            if not current_version:
                raise ValueError(f"{nextcloud_url}/status.php did not include a parseable version")
        except Exception as e:
            errors.append(f"current_version_error: {e}")

        #公式の配布サーバーのファイル一覧から、nextcloud-X.Y.Z.zip の一番新しい番号を最新とする。httpxが自動でgzip圧縮を頼むので約40KBで済む
        try:
            latest_res = await client.get("https://download.nextcloud.com/server/releases/")
            latest_res.raise_for_status()
            versions = re.findall(r'href="nextcloud-(\d+)\.(\d+)\.(\d+)\.zip"', latest_res.text)
            if not versions:
                raise ValueError("no release found in download.nextcloud.com listing")

            major, minor, patch = max(tuple(int(n) for n in v) for v in versions) #文字列のままだと"9">"35"になるので数値にして比べる
            latest_version = f"v{major}.{minor}.{patch}"
        except Exception as e:
            errors.append(f"latest_version_error: {e}")

    return {
        "nextcloud_current_version": current_version,
        "nextcloud_latest_version": latest_version,
        "nextcloud_error": "; ".join(errors) or None,
    }


#バージョン情報の保存場所。version_updater()が定期的に書き込み、monitor()やWebSocketはここを読むだけ。こうすることでタブをいくつ開いても外部への問い合わせは増えない
version_cache = {
    "immich_current_version": None,
    "immich_latest_version": None,
    "immich_error": None,
    "nextcloud_current_version": None,
    "nextcloud_latest_version": None,
    "nextcloud_error": None,
}


async def version_updater(fetch_versions, interval_seconds):
    while True:
        try:
            result = await fetch_versions()
            for key, value in result.items():
                #取得に失敗したバージョンはNoneなので上書きせず、前回の値を残す。エラーは毎回上書きして、直ったら消えるようにする
                if key.endswith("_error") or value is not None:
                    version_cache[key] = value
        except Exception as e:
            print(f"version updater error: {e}")

        await asyncio.sleep(interval_seconds)


async def monitor():
    last_ac_status = True
    last_storage_notified = False
    last_update_notified = {"immich": False, "nextcloud": False}

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

            #バージョンはversion_updater()が保存したものを読むだけ。ここでは外部に問い合わせない
            for prefix, name in (("immich", "Immich"), ("nextcloud", "Nextcloud")):
                current_version = version_cache[f"{prefix}_current_version"]
                latest_version = version_cache[f"{prefix}_latest_version"]
                if current_version and latest_version:
                    if current_version != latest_version:
                        if not last_update_notified[prefix]:
                            await send_notification(
                                f"⚠️ {name} に更新があります！ "
                                f"現在: {current_version} / "
                                f"最新: {latest_version}"
                            )
                            last_update_notified[prefix] = True
                    else:
                        last_update_notified[prefix] = False

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
    asyncio.create_task(version_updater(fetch_immich_versions, 5 * 60)) #Immichは手元のサーバーに聞くだけなので5分ごと
    asyncio.create_task(version_updater(fetch_nextcloud_versions, 60 * 60)) #Nextcloudは外部の配布サーバーなので1時間ごと
    asyncio.create_task(monitor())
    yield #FastAPIのlifespan関連のドキュメントにこう書けと書いてある。動作の主がuvicornが起動したapp(FastAPI)からuvicornに戻る。ブラウザからのリクエストを受け付け始める。


#webアプリの司令塔を作成。インスタンスを作成するという。司令塔を作成する際の追加オプションみたいな感じで、定義したlifespan()を引数に。main.pyでappに情報を詰め込み、そのappを基にuvicornがASGIサーバーを実行する
app = FastAPI(lifespan=lifespan)


#urlが/staticの場合、staticフォルダを見てね、ってことらしい
app.mount("/static", StaticFiles(directory="static"), name="static")


#関数をデコレートしてwebアプリの一部としてのインターフェース(/がAPI)となっている。今回これらのapiは用いていない。
@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.get("/storage")
def get_storage():
    return fetch_storage()


@app.get("/immich/version")
def get_immich_version():
    return {key: value for key, value in version_cache.items() if key.startswith("immich_")}


@app.get("/nextcloud/version")
def get_nextcloud_version():
    return {key: value for key, value in version_cache.items() if key.startswith("nextcloud_")}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket): #Websocket型のデータがwebsocketという変数にFastAPIが自動で代入する。WebSocketとはhttpのような通信方式の名前
    await websocket.accept()

    while True:
        storage = fetch_storage()
        power = fetch_power()

        await websocket.send_json({
            **storage, #**で２つの辞書型のデータを合体させている
            **power,
            **version_cache, #保存済みのバージョン情報を送るだけなので、接続が増えても外部への問い合わせは増えない
        })

        await asyncio.sleep(60)