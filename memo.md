# memo


## 全体の流れ

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


## uvicornとFastAPIの違い

uvicorn  → サーバーの土台。ブラウザからの接続を受け付ける。ASGIサーバーと呼ばれる
FastAPI  → アプリの司令塔。「このURLならこの処理」というルールを管理する。Webフレームワークの一つ。


## Webフレームワークの担当範囲

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


## システム重要メモ

- プロジェクト名: logmo — 自宅サーバー監視 Web アプリ

- 目的: Nextcloud / Immich 等のサービス状態・ストレージ使用率・重要ログを収集し、閾値超過や重要イベントを通知する。

- systemd ユニット (作成済み): `/etc/systemd/system/logmo.service`

	内容例:

	[Unit]
	Description=logmo
	After=network.target

	[Service]
	User=sogo
	WorkingDirectory=/home/sogo/logmo
	ExecStart=/home/sogo/logmo/venv/bin/uvicorn main:app --host 0.0.0.0
	Restart=always

	[Install]
	WantedBy=multi-user.target

- 起動・管理コマンド:

	sudo systemctl daemon-reload
	sudo systemctl enable --now logmo
	sudo systemctl status logmo
	sudo journalctl -u logmo -f

- 環境変数（既定）:
	- `IMMICH_URL`: `http://localhost:2283`
	- `NEXTCLOUD_URL`: `http://localhost`

- アクセス: ブラウザから `http://<TailscaleのIP>:8000`

- 監視対象と方法:
	- `IMMICH_URL`: Immich の状態取得エンドポイント
	- `NEXTCLOUD_URL`: Nextcloud の `status.php` から現在バージョンを取得
	- 最新バージョンは GitHub Releases から取得して比較

- アーキテクチャ要点:
	- systemd が `uvicorn` を起動し、`main.py` 内の `FastAPI` アプリが稼働する
	- 起動時に `lifespan` で初期化処理を行い、定期ポーリングで各サービス状態を取得する

- 技術スタック（運用に必要な依存）:
	- Python, FastAPI, uvicorn
	- systemd によりプロセス管理

- 補足（運用メモ）:
	- ログは systemd/journal で管理される（`journalctl -u logmo`）
	- 実行ユーザー: `sogo`（ユニットファイル参照）
	- 作業ディレクトリ: `/home/sogo/logmo`