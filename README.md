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
- [画像OCRの試行結果・別PCでの再現手順](docs/image-ocr-trial.md)
- [厚生労働省法令等データベースサービス](https://www.mhlw.go.jp/hourei/)

## 保存した原本から再生成する

`--save-source` で取得時点のHTMLと取得日をJSONに保存できます。`--source` を使えば、保存した原本を元にオフラインで再生成できます。以下の `python` には、上で使った仮想環境のPythonを指定してください。

```sh
python notice_to_md.py 00ta4203 --save-source source/00ta4203.json
python notice_to_md.py 00ta4203 --source source/00ta4203.json --out output/reproduced
```

`output/00ta4203.md` と `output/reproduced/00ta4203.md` を比較できます。`source/` はGitの管理対象から除外しています。

スクリプトは、文書IDを指定してDBのHTML本文を1件ずつ変換します。

## 添付画像の文字起こしを加える

通知 `00td0412` に、前回の試行で原本と照合した「書面で提出する書類等送付状」の文字起こしを加える例です。

```sh
python notice_to_md.py 00td0412 --save-source source/00td0412.json
python notice_to_md.py 00td0412 --source source/00td0412.json --ocr-dir docs/examples --out output/with-ocr
```

`output/with-ocr/00td0412.md` の本文1ページ目の末尾に、様式の欄名と原本画像へのリンクが入ります。保存済みの原本JSONがあれば、2行目はオフラインで実行できます。

別の通知を処理するときは、保存済みの原本から添付画像を取得し、OCRエンジンに渡します。NDLOCR-Liteを導入した環境での例です。

```sh
python notice_images.py source/00td0412.json
ndlocr-lite --sourcedir output/ocr-input --output output/ocr-output
```

`notice_images.py` は原本の添付画像を `output/ocr-input/` に画像IDで保存します。OCR出力を原本と照合し、採用する内容をUTF-8の `画像ID.md` として `output/ocr-reviewed/` などに保存してください。変換時にそのフォルダを `--ocr-dir` で指定します。

### 低解像度の画像で検証する

[厚生省職員表彰規程の実施について](https://www.mhlw.go.jp/web/t_doc?dataId=00ta0019&dataType=1&pageNo=1) の添付画像2点（各630 × 916ピクセル）を使えます。Markdownは原本を目視で照合した比較用のサンプルです。

| 様式 | 原本PNG | 比較用Markdown | 確認する箇所 |
| --- | --- | --- | --- |
| 職員の表彰について（内申） | [7914669.png](https://www.mhlw.go.jp/web/t_img_res?img=7914669) | [7914669.md](docs/examples/7914669.md) | 小さな文字の見出し、文書番号、日付、宛先 |
| 表彰候補者名簿 | [7914670.png](https://www.mhlw.go.jp/web/t_img_res?img=7914670) | [7914670.md](docs/examples/7914670.md) | 記載例2人分の行の分離、年齢と勤続期間の対応 |

```sh
python notice_to_md.py 00ta0019 --save-source source/00ta0019.json
python notice_images.py source/00ta0019.json --out output/ocr-input/00ta0019
python notice_to_md.py 00ta0019 --source source/00ta0019.json --ocr-dir docs/examples --out output/with-ocr
```

画像取得コマンドは、この通知の添付画像3点を保存します。上の2点の文字起こしが `output/with-ocr/00ta0019.md` に追記されます。

### 法令の図や数式記号で検証する

原本URLが `dataType=0` の法令は、HTML取得時に `--data-type 0` を指定します。保存原本から変換する場合は保存済みの種別を使います。既存の通知原本は従来どおり読み込めます。[タール色素の省令で試したOCR結果と再現手順](docs/81074000-image-ocr-trial.md)
