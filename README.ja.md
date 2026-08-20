# ComfyUI-GMImageSaver

[English](README.md) | [日本語](README.ja.md)

ComfyUI用の、GraphicsMagickを利用した画像保存ノードです。

最初に収録されている **GM Image JPEG Save** は、JPEG保存に特化した出力ノードです。ComfyUIの `IMAGE` テンソルを中間PNGファイルへ書き出さず、GraphicsMagickへ直接ストリーミングしてJPEGへ変換します。プレビューや画像のパススルー出力は意図的に返しません。

## 特長

- GraphicsMagickによるテンソルからJPEGへの直接変換
- 中間PNGファイルを作成しないため、不要なディスクI/Oを削減
- JPEG専用、プレビューなしの出力ノード
- JPEG品質、クロマサブサンプリング、プログレッシブ形式を設定可能
- ファイル名やディレクトリ名へ任意のラベルを追加可能
- 日付、プレフィックス、ラベルを組み合わせたディレクトリ構成
- 任意の出力先ディレクトリに対応
- 長いプロンプトを含むUTF-8のJPEGコメントに対応
- 画像ごとにComfyUIのプログレスバーを更新
- フロントエンド、localStorage、HandpickerSuiteへの直接依存なし

オプションの `label` 入力には `ckpt_name_safe` などのCheckpoint名を接続できます。HandpickerSuite自体へ依存せず、疎結合なワークフローを構成できます。

## 動作要件

GraphicsMagickを別途インストールし、ComfyUIを起動する環境の `PATH` から `gm` コマンドを実行できるようにしてください。

次のコマンドで確認できます。

```text
gm version
```

GraphicsMagickのインストール後や `PATH` の変更後は、ComfyUIを再起動してください。

### Windows

コマンドラインツールを有効にしてGraphicsMagickをインストールします。ComfyUIを起動する環境と同じPowerShellまたはコマンドプロンプトで、`gm version` が成功することを確認してください。

### Linux

ディストリビューションのパッケージマネージャーからGraphicsMagickをインストールします。DebianまたはUbuntuの場合：

```bash
sudo apt install graphicsmagick
gm version
```

## インストール

このリポジトリをComfyUIの `custom_nodes` ディレクトリへクローンし、ComfyUIを再起動してください。

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ruminar/ComfyUI-GMImageSaver.git
```

## ノード：GM Image JPEG Save

JPEGファイルの保存のみを行うノードです。プレビューや入力画像のパススルーは返しません。プレビューが必要な場合は、画像テンソルを別のPreview Imageノードへ分岐してください。

### 必須入力

- `images`: ComfyUIの `IMAGE` テンソルまたは画像バッチ
- `filename_prefix`: ファイル名の接頭辞。既定値：`image`
- `directory_pattern`: ディレクトリ構成。既定値：`prefix/date`
- `filename_date_format`: ファイル名へ付加する日付形式。既定値：`none`
- `quality`: 1～100のJPEG品質。既定値：`80`
- `subsampling`: クロマサブサンプリング。既定値：`4:2:2`
- `progressive`: プログレッシブJPEGを有効にするか。既定値：`False`

### オプション入力

- `output_dir`: 文字列ノードから接続する出力先のベースディレクトリ
- `label`: Checkpoint名など、ファイル名とディレクトリ名へ追加するラベル
- `comment`: JPEGのコメント領域へ保存する文字列

`output_dir` が未接続または空の場合は、ComfyUI標準のoutputディレクトリを使用します。相対パスは標準outputディレクトリの配下として解決され、絶対パスはその場所を直接使用します。親ディレクトリへの移動（`..`）を含む相対パスは拒否されます。

## JPEGコメントの処理

空でない `comment` が指定された場合、バッチごとにUTF-8の一時ファイルを1つ作り、GraphicsMagickへ `-comment @<ファイル>` の形式で渡します。これにより、GraphicsMagickのコマンドライン引数長制限や、Windowsの文字コード変換・コマンドライン長の問題を回避します。

- 一時ファイルはUTF-8、BOMなしで書き込みます。
- BOM文字、NUL文字、不要な制御文字、不正なUnicodeサロゲート文字を除去します。
- タブ、LF、CR、日本語、アクセント付き文字、絵文字は保持します。
- コメントはUTF-8で最大65,000バイトとし、正しい文字境界で切り詰めます。
- 同じバッチの全画像で同じ一時ファイルを再利用します。
- 正常終了、失敗、タイムアウトのいずれでも削除を試みます。
- コメントが未設定、空、または正規化後に空となる場合は一時ファイルを作りません。

GraphicsMagickはファイルから読み込んだコメントの改行をCRLFへ正規化し、末尾にもCRLFを追加します。行構造は保持されますが、入力とJPEG内コメントの完全なバイト一致は保証されません。

詳細な決定事項は [`.spec/comment-handling.md`](.spec/comment-handling.md) に記録しています。

## ディレクトリパターン

`directory_pattern` は、`output_dir` の下に作成するディレクトリ構成を指定します。日付ディレクトリは常に `yyyyMMdd` 形式です。

選択可能なパターン：

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

入力例：

```text
output_dir: D:\ComfyJPEG
filename_prefix: image
label: meinamix_v11
date: 20260601
```

生成されるディレクトリ：

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

`label` を含むパターンを使用する場合は、空でない `label` 入力が必要です。

## ファイル名の日付形式

`filename_date_format` は、ディレクトリパターンとは独立してファイル名へ追加する日付部分を指定します。

```text
none
yyyyMMdd
yyyyMMdd_HHmm
```

出力例：

```text
image_0001.jpg
image_20260601_0001.jpg
image_20260601_1423_0001.jpg
image_meinamix_v11_0001.jpg
image_meinamix_v11_20260601_1423_0001.jpg
```

日時はノード実行時に一度だけ取得するため、同じバッチ内の画像には同じ日時部分が使用されます。連番は最低4桁になるようゼロ埋めされます。

## JPEG設定

既定値は画質とファイルサイズのバランスを重視しています。

```text
quality: 80
subsampling: 4:2:2
progressive: False
```

保存・比較用途で高画質を優先する場合：

```text
quality: 95
subsampling: 4:4:4
```

大量のCheckpointを確認する際にファイルサイズを抑える場合：

```text
quality: 75～85
subsampling: 4:2:0
```

## プレビューを使用する場合

このノードは意図的にプレビューを返しません。必要な場合は保存前に画像を分岐してください。

```text
VAE Decode / IMAGE
  ├─ Preview Image
  └─ GM Image JPEG Save
```

## 開発・テスト

Python 3.10以降で次のコマンドを実行します。

```bash
python -m unittest discover -s tests -v
```

合意済みの仕様と退行防止条件は [`.spec`](.spec) ディレクトリに記録しています。

## プロジェクトの範囲

将来的にGraphicsMagickを用いた他の保存ノードを追加できるよう、プロジェクト名をGMImageSaverとしています。現在のノードは意図的に次の範囲へ絞っています。

- JPEG出力のみ
- プレビューおよび画像パススルーなし
- PNGサポートなし
- ワークフローメタデータの自動注入なし
- 外部プロジェクトへの直接依存なし

PNGで保存する場合は、ComfyUI標準のSave Imageノードを使用してください。

## ライセンス

GPL-3.0。[LICENSE](LICENSE) を参照してください。
