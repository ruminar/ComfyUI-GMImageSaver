# ComfyUI-GMImageSaver

ComfyUI用の、GraphicsMagickを用いた画像保存ノード群です。

最初のノード **GM Image JPEG Save** は、出力専用のJPEG保存ノードです。  
最大の特徴は、**中間PNGファイルを作らず、ComfyUIの `IMAGE` テンソルから直接GraphicsMagickへ流し込んでJPEG化する**ことです。プレビューも返さず、余計なI/Oを減らしたJPEG特化ノードです。

## このノードの強み

- **SSDに優しいダイレクト変換**  
  中間PNGを書き出さず、`IMAGE` テンソルを直接GraphicsMagickへ渡すため、余計なディスクI/Oを抑えられます。

- **モデル名で自動仕分け**  
  `label` ピンにCheckpoint名（`ckpt_name_safe` など）を繋げば、画像ファイル名やフォルダ名に自動で付与できます。

- **賢いディレクトリ生成**  
  `directory_pattern` を選ぶだけで、整理されたディレクトリ構造へ保存できます。

- **自由な出力先パス**  
  ComfyUI標準の出力フォルダだけでなく、任意の場所へ直接保存できます。

- **あえてのGraphicsMagick採用**  
  多機能で重厚なImageMagickではなく、このノードでは軽量かつ堅牢なGraphicsMagickをコアに据えています。きのこたけのこ論争で「きのこ派」を貫くような、少数派ながらも渋い玄人に深く刺さるチョイスです。

## ノード詳細

### GM Image JPEG Save

「ただひたすらにJPEGを保存する」ことに特化した、意図的に機能を絞り込んだノードです。

- JPEG専用
- プレビュー出力なし
- `IMAGE` のパススルーなし
- フロントエンドや localStorage への依存なし
- HandpickerSuite への直接的な依存なし
- 入力ピン経由でのみ、任意のJPEGコメントを追加可能
- `label` 入力ピンを用いた、ファイル・ディレクトリの柔軟な命名
- 画像が保存されるごとに、ComfyUIのプログレスバーを更新

PNGで保存したい時は、ComfyUI標準の Save Image ノードを使ってください。

## 動作要件

**GraphicsMagick が必須です。**

このノードは `gm` コマンドを呼び出してJPEG保存を行います。  
GraphicsMagickをインストールし、ComfyUIから `gm` を実行できる状態にしてください。インストール後は ComfyUI を再起動してください。

### Windows

GraphicsMagick をインストールし、コマンドラインツールを有効にしてください。  
インストール後、PowerShellやコマンドプロンプトで以下が実行できることを確認してください。

```text
gm version
```

その後、ComfyUI を再起動してください。

### Linux

お使いのディストリビューションのパッケージマネージャーから GraphicsMagick をインストールしてください。

Debian / Ubuntu の例:

```bash
sudo apt install graphicsmagick
gm version
```

## 入力

必須ピン:

- `images`: ComfyUIの `IMAGE` テンソル
- `filename_prefix`: ファイル名の接頭辞。デフォルトは `image`
- `directory_pattern`: ディレクトリの構成パターン。デフォルトは `prefix/date`
- `filename_date_format`: ファイル名に付与する日付の書式。デフォルトは `none`
- `quality`: JPEGの品質（1〜100）。デフォルトは `80`
- `subsampling`: JPEGのクロマサブサンプリング。デフォルトは `4:2:2`
- `progressive`: プログレッシブJPEGにするか否か。デフォルトは `False`

オプションピン:

- `output_dir`: 出力先のベースディレクトリ。文字列ノードから接続してください。
- `label`: 追加の命名用ラベル。`ckpt_name_safe` などを接続できます。
- `comment`: JPEGに埋め込むコメント文。文字列ノードから接続してください。

`output_dir` が未接続、または空欄の場合は、ComfyUI標準の output ディレクトリが使われます。  
相対パスを指定した場合は標準outputディレクトリの配下に、絶対パスを指定した場合はその場所に直接保存されます。

## ディレクトリパターン

`directory_pattern` は、`output_dir` の下に作られるフォルダ構造を決定します。  
`date` 部分は常に `yyyyMMdd` 形式です。

選択可能なパターン:

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

出力例:

```text
output_dir: D:\ComfyJPEG
filename_prefix: image
label: meinamix_v11
date: 20260601
```

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

`label` を含むパターンを選んだ場合は、必ず `label` ピンに文字列を接続してください。

## ファイル名の日付フォーマット

`filename_date_format` は、ファイル名そのものに刻まれる日付を制御します。ディレクトリとは別です。

選択可能な値:

```text
none
yyyyMMdd
yyyyMMdd_HHmm
```

連番は常に4桁です。

出力例:

```text
image_0001.jpg
image_20260601_0001.jpg
image_20260601_1423_0001.jpg
image_meinamix_v11_0001.jpg
image_meinamix_v11_20260601_1423_0001.jpg
```

`label` ピンが接続されている場合は、ファイル名にも組み込まれます。  
タイムスタンプはノード実行時に1回だけ固定されるため、同じバッチ内で生成された画像は同じ時刻のファイル名になります。

## プレビューに関するポリシー

このノードは意図的にプレビュー画像を返しません。

プレビューを見たい場合は、このノードの直前で `IMAGE` テンソルを分岐させ、お好みのプレビュー専用ノードへ接続してください。

```text
VAE Decode / IMAGE
  ├─ Preview node
  └─ GM Image JPEG Save
```

## 棚卸し用途の画質設定

初期設定は高品質寄りです。

```text
quality: 95
subsampling: 4:4:4
```

大量生成後の棚卸し用途でファイルサイズを抑えたい場合は、以下のような設定も有効です。

```text
quality: 75〜85
subsampling: 4:2:0
```

お気に入りCheckpointを絞り込んだ後、`quality: 95` / `subsampling: 4:4:4` などへ上げて再保存する運用もおすすめです。

## Project scope

このリポジトリは、将来的に GraphicsMagick を用いた他の保存系ノードを追加できるように **GMImageSaver** という名前にしています。

ただし、今回の初期ノードはあえて「狭い」機能を追求しています。

- JPEG保存のみ
- プレビューなし
- PNGサポートなし
- メタデータの自動注入なし
- 外部プロジェクトとの強制的な結合なし

## License

GPL-3.0
