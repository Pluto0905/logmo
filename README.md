# logmo

自宅サーバー監視Webアプリ

## 起動方法
systemdで自動起動するため、手動起動は不要。

## systemdサービスの設定
以下のファイルを作成済み：
/etc/systemd/system/logmo.service

内容：
[Unit]
Description=logmo

##ネットワークが起動してからこのサービスを起動する
After=network.target

[Service]
User=sogo
WorkingDirectory=/home/sogo/logmo
ExecStart=/home/sogo/logmo/venv/bin/uvicorn main:app --host 0.0.0.0
Restart=always

[Install]
##どのユーザーでログインしようとしていたとしても、sogoで自動実行される
WantedBy=multi-user.target

## アクセス方法
http://TailscaleのIP:8000

## memo
全体の流れ

systemdがuvicornを起動 (/uvicorn main:app --host 0.0.0.0)
　↓
uvicornがPythonに「main.pyを実行して」と依頼する
　↓
Pythonがmain.pyを上から全部読む（登録、定義）
　↓
app = FastAPI(lifespan=lifespan) でappにlifespanが記憶される。この時appは作成されただけであり実行されていない。
　↓
uvicornがapp(FastAPI)を起動する。つまり今動いているのはFastAPI
　↓
appの中にlifespanがあるのでlifespan(app)を呼び出す（実行）
　↓
yieldでuvicornに制御が戻る

-----------------------------------------------------------------

uvicorn  → サーバーの土台。ブラウザからの接続を受け付ける。ASGIサーバーと呼ばれる
FastAPI  → アプリの司令塔。「このURLならこの処理」というルールを管理する。Webフレームワークの一つ。

---------------------------------------------------------------------

Webフレームワークの担当範囲

ブラウザ
　↓
uvicorn（サーバー）
　↓ ← ここから
FastAPI（Webフレームワーク）
・URLのルーティング（どのURLで何をするか）
・リクエストの解析
・レスポンスの生成
　↓ ← ここまで
uvicorn（サーバー）
　↓
ブラウザ

---------------------------------------------------------