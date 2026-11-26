# MHLW_houreiDB

厚生労働省法令等データベースサービスの通知を、RAGに取り込めるMarkdownに変換するためのリポジトリです。取得経路、変換ルール、原本との照合手順をここに残します。

## まず1件を変換する

Python 3.10以上を用意し、リポジトリのルートで実行します。厚生労働省サイトへのインターネット接続が必要です。

Windows（PowerShell）

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe notice_to_md.py 00ta4203
```

macOS・Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python notice_to_md.py 00ta4203
```

`output/00ta4203.md` が生成されます。引数には、通知本文のURLにある `dataId` を指定します。出力先は `--out` で変更できます。既定の出力フォルダはGitの管理対象から除外しています。

- [取得経路・変換ルール・確認手順](docs/notification-markdown.md)
- [厚生労働省法令等データベースサービス](https://www.mhlw.go.jp/hourei/)

## 保存した原本から再生成する

`--save-source` で取得時点のHTMLと取得日をJSONに保存できます。`--source` を使えば、保存した原本を元にオフラインで再生成できます。以下の `python` には、上で使った仮想環境のPythonを指定してください。

```sh
python notice_to_md.py 00ta4203 --save-source source/00ta4203.json
python notice_to_md.py 00ta4203 --source source/00ta4203.json --out output/reproduced
```

`output/00ta4203.md` と `output/reproduced/00ta4203.md` を比較できます。`source/` はGitの管理対象から除外しています。

現在のスクリプトは、通知IDを指定してDBのHTML本文を1件ずつ変換するところまで対応しています。
