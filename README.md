# logmo

自宅サーバー監視 Web アプリ — リソース監視・サービス状態取得・通知機能を提供します。

## 概要
`logmo` は自宅サーバー上で稼働する軽量の監視 Web アプリです。Nextcloud や Immich などのサービス状態、ストレージ使用率、重要ログを収集し、閾値を超えた場合に通知します。systemd と uvicorn/FastAPI で常時稼働する構成です。

## 自分の役割
- 設計・実装・デプロイ（フルスタック、ソロ開発）
- API と監視ロジック、systemd サービス定義の作成、通知フロー実装

## 主な機能
- 各種サービス（Nextcloud、Immich 等）のバージョンチェック
- ストレージ使用率の監視と閾値超過時の通知
- システム／セキュリティ関連の高重要度ログ収集と通知
- サーバーの電源（コンセント）状態チェックと通知
- Web UI で状態を一覧表示（WebSocket で更新）

## 技術スタック
- 言語: Python
- フレームワーク: FastAPI
- ASGI サーバー: uvicorn
- デプロイ: systemd サービス
- フロントエンド: シンプルな静的 HTML/JS（WebSocket を利用）

## アーキテクチャ（要点）
- systemd が `uvicorn` を起動し、`main.py` 内の `FastAPI` アプリが稼働します。
- アプリ起動時にライフサイクル（lifespan）で初期化処理を行い、定期的に各サービスの状態を取得します。

## デプロイ（ systemd ）
作成済みの systemd ユニットファイル例（ `/etc/systemd/system/logmo.service` ）:

[Unit]
Description=logmo
After=network.target

[Service]
User=sogo
WorkingDirectory=/home/sogo/logmo
ExecStart=/home/sogo/logmo/venv/bin/uvicorn main:app --host 0.0.0.0
EnvironmentFile=/home/sogo/logmo/.env
Restart=always

[Install]
WantedBy=multi-user.target

起動・有効化例:

sudo systemctl daemon-reload
sudo systemctl enable --now logmo

## 環境変数（例）
- `IMMICH_URL`（既定: `http://localhost:2283`）
- `NEXTCLOUD_URL`（既定: `http://localhost`）
- `IMMICH_API_KEY`（必須: Immich で `server.versionCheck` 権限だけを付けた API キー）

キーは `.env`（`.gitignore` 済み、`chmod 600`）に書き、systemd ユニットの `[Service]` に `EnvironmentFile=/home/sogo/logmo/.env` を追加して読み込ませます。

## アクセス
ブラウザからアクセス: http://<TailscaleのIP>:8000

## 監視対象の詳細
- `IMMICH_URL`: `/api/server/version` で現在バージョン、`/api/server/version-check`（`IMMICH_API_KEY` を使用）で Immich 自身が1時間ごとに確認している最新バージョンを取得。5分ごとに更新
- `NEXTCLOUD_URL`: Nextcloud の `status.php` を利用して現在バージョンを取得。最新バージョンは公式配布サーバー（`download.nextcloud.com/server/releases/`）のファイル一覧から取得。1時間ごとに更新
- 取得結果はアプリ内に保存して使い回すため、ブラウザのタブを増やしても外部への問い合わせは増えません。取得に失敗した場合は前回の値を残し、エラーを表示します
- Immich・Nextcloud とも、更新を見つけると ntfy で1回だけ通知します

---------------------------------------------------------
