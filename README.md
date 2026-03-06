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
