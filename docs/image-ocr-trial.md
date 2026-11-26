# 厚労省通知の画像OCR試行

2026年11月26日。公開されている通知の様式画像4枚で、日本語の文字認識と罫線表の復元を試した。数式は、正解が既知の試作画像3枚を別に用意した。

## 試した画像

| 通知ID | 画像 | 画素 |
| --- | --- | --- |
| 00td0412 | [書面で提出する書類等送付状](https://www.mhlw.go.jp/web/t_img?img=8027388) | 1181 × 1695 |
| 00ta0019 | [表彰の内申](https://www.mhlw.go.jp/web/t_img?img=7914669) | 630 × 916 |
| 00ta0019 | [表彰候補者名簿](https://www.mhlw.go.jp/web/t_img?img=7914670) | 630 × 916 |
| 00ta0019 | [功績調書](https://www.mhlw.go.jp/web/t_img?img=7914671) | 630 × 916 |

## 結果

### 送付状の項目名

原本を目視して、様式番号と表題を含む18ラベルを採点対象にした。出力行と正解を、UnicodeのNFKC正規化と空白除去を施した後に完全一致で比較した。行をまたいだ文字の再結合は行っていない。数値はこの画像での一致数であり、全体の精度を示すものではない。

| OCR | 一致 | 誤読・欠落の例 |
| --- | --- | --- |
| NDLOCR-Lite 2.0.0 | 17 / 18 | 「行政機関記入欄」を「行政機関記入横」と誤読。テキスト出力では右列の項目が後ろに回った。 |
| Tesseract 5.5.0、日本語モデル、PSM 11 | 13 / 18 | 「GW受付番号」を「6W受付番号」と誤読。「様式」の欄が欠落。「申請・届出者名」は途中で行が分かれた。 |

NDLOCR-LiteのOCR結果に同梱のTableCenterNetを適用すると、表の左側の「GW受付番号」と右側の「提出(予定)日」を同じ行へ配置できた。原本の最初の行は4セルだが、試行出力は6列になった。横に結合された備考欄の見出しも5セルに繰り返された。送付状のような空欄の様式は、RAGでは欄名の一覧を先に使う方が読みやすい。

原本と照合した追記例は、この文書の「通知Markdownに追記する例」を参照。

### 低解像度の画像

NDLOCR-Liteでは「職員の表彰について(内申)」「表彰候補者名簿」「功績調書」を読み取れた。Tesseractでは同じ画像で「簡員の表形について(内申)」などの誤読があった。

表彰候補者名簿では、NDLOCR-LiteとTableCenterNetを組み合わせても、2人分の記載例が一つの行にまとまり、年齢などの数字が欠落・誤読した。画像をLanczos法で2倍に拡大してNDLOCR-Liteを再実行した際も、数字は原本と一致しなかった。名簿のように行と値の対応に意味がある表は、照合してからMarkdownに入れる。

### 数式画像

220 DPIで生成した数式3枚をTesseractの英語モデル（PSM 7）で処理した。構造まで一致した式は0/3だった。

| 試作画像の数式 | 結果 |
| --- | --- |
| 重み付き平均。分子・分母に総和と添字 | 出力なし |
| 極限と差分商 | 極限の条件と分数が欠落 |
| 差分を分子にした百分率と「以上」の条件 | 分数の分母が落ち、`≥` を `=` と認識 |

LaTeXに変換する専用エンジンRapidLaTeXOCRは、実行時の予期しないテレメトリー通信を自動審査が拒否したため、結果を採点していない。上の結果は汎用OCRの試行であり、専用モデルの精度は未確認。

## 実行を確認できなかった候補

YomiToku 0.16.3のCPU軽量モードも試したが、RapidLaTeXOCRと同様に、実行時の予期しない外部テレメトリー通信を自動審査が拒否した。YomiTokuとRapidLaTeXOCRの精度は比較対象に含めていない。

## 再現用メモ

- 日本語OCRにはNDLOCR-Lite 2.0.0のコミット `ba8bb854d7b3f8e904bebc47e710a9ce64ade939` の同梱モデルを使用。原本PNGをRGBに変換し、CLIでテキスト・JSON・XMLを出力した。表の復元には同コミットの `model/tablecenternet_s_800_v3.onnx` と `infer_tables_from_page` を使った。[NDLOCR-Lite](https://github.com/ndl-lab/ndlocr-lite)
- Tesseractの様式画像は `-l jpn --psm 11`。数式画像は `-l eng --psm 7`。[日本語モデル](https://github.com/tesseract-ocr/tessdata_fast)
- 厚労省DBの `t_img` リンクから表示用HTMLを取得し、その中の `t_img_res` の画像URLから原本PNGを取得した。

比較に用いた数式画像は、下記のTeXを `matplotlib.mathtext.math_to_image()` で220 DPIのPNGに描画した。

```tex
S = \frac{\sum_{i=1}^{n} w_i x_i}{\sum_{i=1}^{n} w_i}
\lim_{h\to 0}\frac{f(x+h)-f(x)}{h}=f^\prime(x)
R = \frac{A-B}{C}\times 100 \geq 80\%
```

## 別のPCで再開する

1. リポジトリの [README](../README.md) に従ってPython環境を用意し、`python notice_to_md.py 00td0412 --save-source source/00td0412.json` で通知のMarkdownとHTML原本を取得する。
2. 様式画像を取得する。下記はWindows PowerShellの例。Linux・macOSでは `curl.exe` を `curl` に置き換える。

   ```powershell
   mkdir output/ocr-input
   curl.exe -fL "https://www.mhlw.go.jp/web/t_img_res?img=8027388" -o output/ocr-input/form.png
   ```

   低解像度の3画像も試す場合は、URLの末尾を `7914669`、`7914670`、`7914671` に入れ替え、画像ごとに別名で保存する。

3. NDLOCR-Liteを別のPython環境に導入し、下記を実行する。v2のCLIはPython 3.11以上が必要で、PyPI版の初回実行時にモデルを取得する。試行時のモデルを揃える場合は、上記のコミットをチェックアウトし、その同梱モデルを使う。[導入手順](https://github.com/ndl-lab/ndlocr-lite/tree/ba8bb854d7b3f8e904bebc47e710a9ce64ade939#コマンドラインからの利用)

   ```powershell
   python -m pip install ndlocr-lite==2.0.0
   ndlocr-lite --sourcedir output/ocr-input --output output/ocr-output
   ```

   Tesseractを日本語モデル付きで導入済みの場合は、同じ画像から比較用のテキストを作れる。

   ```powershell
   tesseract output/ocr-input/form.png stdout -l jpn --psm 11
   ```

4. OCRのテキスト、JSON、XMLを確認して、下記の例と比較する。原本画像とOCR結果はローカルに保管し、再生成に使う場合は画像ID、使用モデル、設定も一緒に記録する。

## 通知Markdownに追記する例

この試行で照合した欄名を、[8027388.md](examples/8027388.md) から `--ocr-dir` で取り込める。[画像の保存と文字起こしの取り込み手順](../README.md#添付画像の文字起こしを加える) を参照。

`00td0412` の本文1ページ目にある「様式1」の画像リンク直後に、原本と照合した欄名を追記した例。

```markdown
様式1

[原本に画像あり（画像1 (16KB)）](<https://www.mhlw.go.jp/web/t_img?img=8027388>)

**様式1の文字起こし（NDLOCR-Liteで認識し、画像と照合した試作）**

書面で提出する書類等送付状

- GW受付番号
- 提出（予定）日
- 申請・届出等名称
- 申請・届出者名
- 申請・届出等担当者
- 担当者電話番号
- メールアドレス
- 提出窓口
- 様式
- システム受付番号
- 販売名、製造所名等
- 申請区分
- 手数料区分
- 書面で提出する書類の情報、その他備考
- 収入印紙貼付欄
- 行政機関記入欄
```

## 次の作業

- 空欄の様式は欄名一覧として取り込む。値入りの表は行・列・値の対応を原本と照合し、確認できない値は推測で埋めず、原本リンクを残す。
- 専用エンジンによる数式からLaTeXへの変換と、RAGが表や数式の構造を維持して読み込めるかを確認する。
