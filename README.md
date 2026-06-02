# ComfyUI-GMImageSaver

GraphicsMagick-based output saver nodes for ComfyUI.

The initial node, **GM Image JPEG Save**, is an output-only JPEG saver. It saves ComfyUI `IMAGE` tensors directly as JPEG using GraphicsMagick, without creating intermediate PNG files and without returning preview images.

## Node

### GM Image JPEG Save

A deliberately narrow JPEG saver node.

It does **not** try to be a general image saver.

- JPEG only
- No PNG output
- No preview output
- No `IMAGE` passthrough
- No frontend/localStorage dependency
- No HandpickerSuite dependency
- Optional JPEG comment via input pin only
- Optional `label` input pin for filename/directory naming
- Image-by-image progress bar updates

For PNG output, use ComfyUI's standard Save Image node.

## Requirements

GraphicsMagick is required.

Download GraphicsMagick from the official site:

- [GraphicsMagick Download](https://www.graphicsmagick.org/download.html)
- [Windows Installation Notes](https://www.graphicsmagick.org/INSTALL-windows.html)

GM Image JPEG Save resolves GraphicsMagick in this order:

1. `GM_PATH` environment variable
2. `gm` from PATH

If GraphicsMagick is available in PATH, no setting is needed.

### Timeout

GraphicsMagick is given a per-image timeout. The default is 300 seconds.

To change it, set this environment variable before starting ComfyUI:

```text
GM_IMAGE_SAVER_TIMEOUT=300
```

### Windows

Install GraphicsMagick and enable the option to update PATH if available. After installing, restart ComfyUI so the updated PATH is visible.

If PATH is not available, set the `GM_PATH` environment variable to the full path of `gm.exe`, for example:

```text
C:\Program Files\GraphicsMagick-1.3.45-Q16\gm.exe
```

### Linux

Install GraphicsMagick using your distribution package manager and make sure `gm` is available in PATH.

For example, on Debian / Ubuntu:

```bash
sudo apt install graphicsmagick
```

## Inputs

Required:

- `images`: ComfyUI `IMAGE`
- `filename_prefix`: filename prefix. Default `image`.
- `directory_pattern`: directory layout pattern. Default `prefix/date`.
- `filename_date_format`: optional date text in the filename. Default `none`.
- `quality`: JPEG quality, default `95`
- `subsampling`: JPEG chroma subsampling, default `4:4:4`
- `progressive`: progressive JPEG, default `False`

Optional input pins:

- `output_dir`: base output directory. Connect from a string/text node.
- `label`: optional extra naming string. You can connect `ckpt_name_safe` or any other label string.
- `comment`: JPEG comment string. Connect from a string/text node.

If `output_dir` is unconnected or empty, ComfyUI's standard output directory is used.

If `output_dir` is a relative path, it is resolved under ComfyUI's standard output directory.

If `output_dir` is an absolute path, it is used as-is.

Generated directory/file components are sanitized. Hyphens are intentionally converted to underscores.

## Directory patterns

`directory_pattern` controls folders under `output_dir`.

The `date` part is always `yyyyMMdd`.

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

Example values:

```text
output_dir: D:\ComfyJPEG
filename_prefix: image
label: meinamix_v11
date: 20260601
```

Results:

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

Patterns containing `label` require a `label` input.

## Naming compatibility

Generated path parts are sanitized for filesystem safety, but hyphens are preserved.

This keeps the `label` input compatible with tools such as HandpickerSuite's `ckpt_name_safe`, where names like `foo-model-v1` are expected to remain unchanged.

## Filename date formats

`filename_date_format` controls date text in the filename, not the directory.

Available values:

```text
none
yyyyMMdd
yyyyMMdd_HHmm
```

The counter is four digits.

Examples:

```text
image_0001.jpg
image_20260601_0001.jpg
image_20260601_1423_0001.jpg
image_meinamix_v11_0001.jpg
image_meinamix_v11_20260601_1423_0001.jpg
```

If `label` is connected, it is included in the filename automatically.

The timestamp is fixed once per node execution, so images in the same batch use the same timestamp.

## Progress

The node updates ComfyUI's progress bar once per successfully saved image.

## Preview policy

This node intentionally does not return preview images.

For previews, branch the `IMAGE` before this node and connect it to your preferred preview node.

Example:

```text
VAE Decode / IMAGE
  ├─ Preview node
  └─ GM Image JPEG Save
```

## Project scope

This repository is named **GMImageSaver** so that additional GraphicsMagick-based saver nodes can be added in the future.

However, the initial node is intentionally narrow:

- JPEG only
- no preview
- no PNG support
- no automatic metadata injection
- no external project coupling

## License

MIT
