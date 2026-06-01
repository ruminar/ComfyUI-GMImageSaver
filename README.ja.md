# ComfyUI-GMImageSaver

ComfyUI用の、GraphicsMagickを用いた画像保存ノード群じゃ。

記念すべき最初のノード **GM Image JPEG Save** は、出力専用のJPEG保存ノードじゃぞ。
最大の特徴は、**中間PNGファイルを作らず、ComfyUIの `IMAGE` テンソルから直接GraphicsMagickへ流し込んでJPEG化する**ことじゃ。プレビューも出さず、余計なI/Oを極限まで削ぎ落とした研ぎ澄まされた刃となっておる。

## 🌟 このノードの強み（アピールポイント）

* **SSDに優しいダイレクト変換:** 一度PNGとして保存するような野暮なことはせぬ。生データを直接パイプで送り込むため、高速かつおぬしのSSDの寿命に極めて優しいエコな設計じゃ。
* **モデル名で自動仕分け:** `label` ピンにCheckpoint名（`ckpt_name_safe` など）を繋げば、画像ファイル名やフォルダ名に自動で付与できるぞ。
* **賢いディレクトリ生成:** パターンを選ぶだけで、必要なフォルダを自動で掘って整理整頓してくれるのじゃ。
* **自由な出力先パス:** ComfyUI標準の出力フォルダだけでなく、任意の場所（絶対パス）へ直接保存可能じゃ。
* **あえてのGraphicsMagick採用:** 多機能で重厚なImageMagickではなく、軽量かつ堅牢なGraphicsMagickをコアに据えたぞ。きのこたけのこ論争で「きのこ派」を貫くような、渋い玄人に深く刺さるチョイスじゃな！

## 📦 ノード詳細

### GM Image JPEG Save

「ただひたすらにJPEGを保存する」ことに特化した、意図的に機能を絞り込んだノードじゃ。
汎用的な画像保存ノードを目指したものではない点に留意するのじゃぞ。

* JPEG専用（PNG出力はせぬ！）
* プレビュー出力なし
* `IMAGE` のパススルー（通過）なし
* フロントエンドや localStorage への依存なし
* HandpickerSuite への直接的な依存なし（疎結合じゃ！）
* 入力ピン経由でのみ、任意のJPEGコメントを追加可能
* `label` 入力ピンを用いた、ファイル・ディレクトリの柔軟な命名
* 画像が保存されるごとに、ComfyUIのプログレスバーをしっかり更新するぞ

※PNGで保存したい時は、ComfyUI標準の Save Image ノードを使うのじゃ。

## ⚙️ 動作要件 (Requirements)

**GraphicsMagick が必須じゃ。**

- [GraphicsMagick official site](https://www.graphicsmagick.org/)
- [GraphicsMagick Download](https://www.graphicsmagick.org/download.html)
- [Windows Installation Notes](https://www.graphicsmagick.org/INSTALL-windows.html)

このノードは、以下の順序で GraphicsMagick の実行パスを探すぞ。

1. 環境変数 `GM_PATH`
2. PATH に通っている `gm` コマンド

環境変数のPATHに GraphicsMagick が登録されておれば、特別な設定は不要じゃ。

### Windows の場合

GraphicsMagick をインストールし、インストーラーのオプションで「PATHを更新する」にチェックを入れるのじゃ。インストール後は、更新されたPATHを読み込ませるために ComfyUI を再起動するのじゃぞ。

もしPATHを通せない事情があるなら、環境変数 `GM_PATH` に `gm.exe` のフルパスを直接設定してやれ。
例: `C:\Program Files\GraphicsMagick-1.3.45-Q16\gm.exe`

### Linux の場合

お使いのディストリビューションのパッケージマネージャーから GraphicsMagick をインストールし、ターミナルで `gm` コマンドが使える状態にしておくのじゃ。
Debian / Ubuntu の例:

```bash
sudo apt install graphicsmagick

```

## 🎛️ 入力 (Inputs)

**必須ピン:**

* `images`: ComfyUIの `IMAGE` テンソルじゃ。
* `filename_prefix`: ファイル名の接頭辞（プレフィックス）。デフォルトは `image` じゃ。
* `directory_pattern`: ディレクトリの構成パターン。デフォルトは `prefix/date` じゃ。
* `filename_date_format`: ファイル名に付与する日付の書式。デフォルトは `none`（なし）じゃ。
* `quality`: JPEGの品質（1〜100）。デフォルトは `95` じゃ。
* `subsampling`: JPEGのクロマサブサンプリング。デフォルトは `4:4:4` じゃ。
* `progressive`: プログレッシブJPEGにするか否か。デフォルトは `False` じゃ。

**オプションピン（外部入力）:**

* `output_dir`: 出力先のベースディレクトリじゃ。文字列(String)ノードから繋ぐのじゃ。
* `label`: 追加の命名用ラベルじゃ。ここに `ckpt_name_safe` などの文字列を繋ぐと良いぞ。
* `comment`: JPEGに埋め込むコメント文じゃ。文字列(String)ノードから繋ぐのじゃ。

`output_dir` が未接続、または空欄の場合は、ComfyUI標準の output ディレクトリが使われるぞ。
相対パスを指定した場合は標準outputディレクトリの配下に、絶対パスを指定した場合はその場所に直接保存される仕様じゃ。

## 📁 ディレクトリパターン (Directory patterns)

`directory_pattern` は、`output_dir` の下に作られるフォルダ構造を決定するぞ。
`date`（日付）部分は常に `yyyyMMdd` 形式じゃ。

**選択可能なパターン:**

```text
none
date
prefix
prefix_date
prefix/date
label
label_date
label/date
prefix_label
prefix/label
prefix_label_date
prefix/label/date
prefix_date_label
prefix/date/label

```

**出力例:**

```text
output_dir: D:\ComfyJPEG
filename_prefix: image
label: meinamix_v11
date: 20260601

```

上記の設定で動かした場合の結果じゃ:

```text
none                -> D:\ComfyJPEG
date                -> D:\ComfyJPEG\20260601
prefix              -> D:\ComfyJPEG\image
prefix_date         -> D:\ComfyJPEG\image_20260601
prefix/date         -> D:\ComfyJPEG\image\20260601
label               -> D:\ComfyJPEG\meinamix_v11
label_date          -> D:\ComfyJPEG\meinamix_v11_20260601
label/date          -> D:\ComfyJPEG\meinamix_v11\20260601
prefix_label        -> D:\ComfyJPEG\image_meinamix_v11
prefix/label        -> D:\ComfyJPEG\image\meinamix_v11
prefix_label_date   -> D:\ComfyJPEG\image_meinamix_v11_20260601
prefix/label/date   -> D:\ComfyJPEG\image\meinamix_v11\20260601
prefix_date_label   -> D:\ComfyJPEG\image_20260601_meinamix_v11
prefix/date/label   -> D:\ComfyJPEG\image\20260601\meinamix_v11

```

※ `label` を含むパターンを選んだ場合は、必ず `label` ピンに何かを接続するのじゃぞ！

## 📅 ファイル名の日付フォーマット

`filename_date_format` は、ファイル名そのものに刻まれる日付を制御するぞ（ディレクトリとは別じゃ）。

**選択可能な値:**

```text
none
yyyyMMdd
yyyyMMdd_HHmm

```

連番（カウンター）は常に4桁で付与されるぞ。

**出力例:**

```text
image_0001.jpg
image_20260601_0001.jpg
image_20260601_1423_0001.jpg
image_meinamix_v11_0001.jpg
image_meinamix_v11_20260601_1423_0001.jpg

```

`label` ピンが接続されている場合は、このように自動的にファイル名にも組み込まれるのじゃ。
また、タイムスタンプは「ノード実行時に1回だけ」固定されるため、同じバッチ内で生成された画像はすべて同じ時刻のファイル名になるぞ。途中で分が切り替わってファイル名が割れる心配はない！

## 👁️ プレビューに関するポリシー

繰り返すが、このノードは意図的にプレビュー画像を返さない仕様にしておる。
プレビューを見たい場合は、このノードの直前で `IMAGE` テンソルを分岐させ、お好みのプレビュー専用ノード（Preview Imageなど）を繋ぐのじゃ。

**推奨する配線の例:**

```text
VAE Decode / IMAGE
  ├─ Preview node (ここでお顔を見るのじゃ！)
  └─ GM Image JPEG Save (こちらは黙々とディスクへ書き込む！)

```

## 🗺️ プロジェクトの展望 (Project scope)

このリポジトリは、将来的に GraphicsMagick を用いた他の保存系ノードを追加できるように **GMImageSaver** という名前にしておる。

じゃが、今回の初期ノードはあえて「狭い」機能を追求したぞ。

* JPEG保存のみ
* プレビューなし
* PNGサポートなし
* メタデータの自動注入など、複雑なおせっかい機能なし
* 外部プロジェクト（HandpickerSuiteなど）との強制的な結合なし

この「引き算の美学」を楽しんでくれると嬉しいのう！

## 📄 ライセンス

GPL-3.0（ComfyUI本体の掟に従っておるぞ！） じゃ。自由に、そして自己責任で使い倒すのじゃぞ！