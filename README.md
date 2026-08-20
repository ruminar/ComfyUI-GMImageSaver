# ComfyUI-GMImageSaver

[English](README.md) | [日本語](README.ja.md)

GraphicsMagick-based image saving nodes for ComfyUI.

The first included node, **GM Image JPEG Save**, is a focused JPEG output node. It streams ComfyUI `IMAGE` tensors directly to GraphicsMagick without creating intermediate PNG files. It intentionally returns no preview or image passthrough output.

## Features

- Direct tensor-to-JPEG conversion through GraphicsMagick
- No intermediate PNG files
- JPEG-only, previewless output node
- Configurable JPEG quality, chroma subsampling, and progressive encoding
- Optional labels in filenames and directory names
- Flexible date-, prefix-, and label-based directory layouts
- Custom output directory support
- UTF-8 JPEG comments, including long prompts
- Per-image ComfyUI progress updates
- No frontend, localStorage, or direct HandpickerSuite dependency

The optional `label` input can accept checkpoint names such as `ckpt_name_safe`, making the node suitable for loosely coupled HandpickerSuite workflows without requiring HandpickerSuite itself.

## Requirements

GraphicsMagick must be installed separately, and the `gm` executable must be available on the `PATH` used to launch ComfyUI.

Verify the installation with:

```text
gm version
```

Restart ComfyUI after installing GraphicsMagick or changing `PATH`.

### Windows

Install GraphicsMagick with its command-line tools enabled. Open PowerShell or Command Prompt in the same environment used to launch ComfyUI and confirm that `gm version` succeeds.

### Linux

Install GraphicsMagick through your distribution's package manager. For Debian or Ubuntu:

```bash
sudo apt install graphicsmagick
gm version
```

## Installation

Clone this repository into the ComfyUI `custom_nodes` directory, then restart ComfyUI.

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ruminar/ComfyUI-GMImageSaver.git
```

## Node: GM Image JPEG Save

The node saves JPEG files only. It does not return a preview or pass the input image through. If a preview is required, branch the image tensor to a separate Preview Image node.

### Required inputs

- `images`: ComfyUI `IMAGE` tensor or image batch
- `filename_prefix`: Filename prefix; default: `image`
- `directory_pattern`: Directory layout; default: `prefix/date`
- `filename_date_format`: Optional date component in the filename; default: `none`
- `quality`: JPEG quality from 1 to 100; default: `80`
- `subsampling`: Chroma subsampling; default: `4:2:2`
- `progressive`: Enable progressive JPEG encoding; default: `False`

### Optional inputs

- `output_dir`: Base output directory supplied by a connected string node
- `label`: Additional filename and directory label, such as a checkpoint name
- `comment`: Text stored in the JPEG comment field

If `output_dir` is not connected or is empty, the standard ComfyUI output directory is used. Relative paths are resolved below the standard output directory. Absolute paths are used directly. Relative paths containing parent-directory traversal (`..`) are rejected.

## JPEG comment handling

When a non-empty `comment` is provided, the node writes one temporary UTF-8 file for the batch and passes it to GraphicsMagick with `-comment @<file>`. This avoids GraphicsMagick command-line argument limits and Windows command-line encoding and length issues.

- Temporary files are UTF-8 without a BOM.
- BOM characters, NUL characters, unsupported control characters, and invalid Unicode surrogates are removed.
- Tabs, line feeds, carriage returns, Japanese text, accented characters, and emoji are preserved.
- Comments are limited to 65,000 UTF-8 bytes and truncated only at a valid character boundary.
- The same temporary file is reused for every image in the batch.
- Cleanup is attempted after success, failure, or timeout.
- No temporary file is created when the comment is missing or empty after normalization.

GraphicsMagick normalizes file-based comment line endings to CRLF and appends a trailing CRLF. Line structure is preserved, but the stored comment is not guaranteed to be byte-for-byte identical to the input.

The detailed decision record is available in [`.spec/comment-handling.md`](.spec/comment-handling.md).

## Directory patterns

`directory_pattern` controls the directories created below `output_dir`. Date directory components always use `yyyyMMdd`.

Available patterns:

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

Example inputs:

```text
output_dir: D:\ComfyJPEG
filename_prefix: image
label: meinamix_v11
date: 20260601
```

Resulting directories:

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

A pattern containing `label` requires a non-empty `label` input.

## Filename date formats

`filename_date_format` controls the date component added to the filename independently of the directory pattern.

```text
none
yyyyMMdd
yyyyMMdd_HHmm
```

Examples:

```text
image_0001.jpg
image_20260601_0001.jpg
image_20260601_1423_0001.jpg
image_meinamix_v11_0001.jpg
image_meinamix_v11_20260601_1423_0001.jpg
```

The timestamp is captured once per node execution, so every image in a batch uses the same date and time component. Counters are zero-padded to at least four digits.

## JPEG settings

Default settings provide a balance between quality and file size:

```text
quality: 80
subsampling: 4:2:2
progressive: False
```

For higher-quality archival or comparison output:

```text
quality: 95
subsampling: 4:4:4
```

For smaller files during large checkpoint reviews:

```text
quality: 75-85
subsampling: 4:2:0
```

## Preview workflow

This node intentionally returns no preview. Branch the image before saving when a preview is needed:

```text
VAE Decode / IMAGE
  ├─ Preview Image
  └─ GM Image JPEG Save
```

## Development

Run the regression tests with Python 3.10 or later:

```bash
python -m unittest discover -s tests -v
```

Agreed behavior and regression requirements are recorded in the [`.spec`](.spec) directory.

## Project scope

The project name allows additional GraphicsMagick-based saving nodes to be added in the future. The current node intentionally remains focused:

- JPEG output only
- No preview or image passthrough
- No PNG support
- No automatic workflow metadata injection
- No direct dependency on external projects

For PNG output, use ComfyUI's standard Save Image node.

## License

GPL-3.0. See [LICENSE](LICENSE).
