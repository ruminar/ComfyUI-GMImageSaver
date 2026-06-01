# ComfyUI-GMImageSaver

GraphicsMagick-based output saver nodes for ComfyUI.

The initial node, **GM JPEG Save**, is an output-only JPEG saver. It saves ComfyUI `IMAGE` tensors directly as JPEG using GraphicsMagick, without creating intermediate PNG files and without returning preview images.

## Node

### GM JPEG Save

A deliberately narrow JPEG saver node.

It does **not** try to be a general image saver.

- JPEG only
- No PNG output
- No preview output
- No `IMAGE` passthrough
- No frontend/localStorage dependency
- No automatic prompt or LoRA text in filenames
- Optional JPEG comment via input pin only
- Optional HandpickerSuite checkpoint directory patterns via lazy import

For PNG output, use ComfyUI's standard Save Image node.

## Requirements

GraphicsMagick is required.

GM JPEG Save resolves GraphicsMagick in this order:

1. `GM_PATH` environment variable
2. `gm` from PATH

If GraphicsMagick is available in PATH, no setting is needed.

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
- `filename_prefix`: filename prefix
- `directory_pattern`: directory layout pattern
- `date_format`: optional date text in the filename
- `quality`: JPEG quality, default `95`
- `subsampling`: JPEG chroma subsampling, default `4:4:4`
- `progressive`: progressive JPEG, default `False`

Optional input pins:

- `output_dir`: base output directory. Connect from a string/text node.
- `comment`: JPEG comment string. Connect from a string/text node.

If `output_dir` is unconnected or empty, ComfyUI's standard output directory is used.

If `output_dir` is a relative path, it is resolved under ComfyUI's standard output directory.

If `output_dir` is an absolute path, it is used as-is.

## Directory patterns

`directory_pattern` controls folders under `output_dir`.

The `date` part is always `yyyyMMdd`.

Available patterns:

```text
none
date
prefix_date
prefix/date
ckptname_date
ckptname/date
prefix_ckptname_date
prefix/ckptname/date
```

Example values:

```text
output_dir: D:\ComfyJPEG
filename_prefix: sample
ckpt_name_safe: meinamix_v11
date: 20260601
```

Results:

```text
none                         -> D:\ComfyJPEG
date                         -> D:\ComfyJPEG\20260601
prefix_date                  -> D:\ComfyJPEG\sample_20260601
prefix/date                  -> D:\ComfyJPEG\sample\20260601
ckptname_date                -> D:\ComfyJPEG\meinamix_v11_20260601
ckptname/date                -> D:\ComfyJPEG\meinamix_v11\20260601
prefix_ckptname_date         -> D:\ComfyJPEG\sample_meinamix_v11_20260601
prefix/ckptname/date         -> D:\ComfyJPEG\sample\meinamix_v11\20260601
```

Patterns containing `ckptname` require HandpickerSuite checkpoint information. Internally, `ckptname` uses `ckpt_name_safe`.

Patterns without `ckptname` do not import HandpickerSuite and work standalone.

## Filename date formats

`date_format` controls date text in the filename, not the directory.

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
```

The timestamp is fixed once per node execution, so images in the same batch use the same timestamp.

## Preview policy

This node intentionally does not return preview images.

For previews, branch the `IMAGE` before this node and connect it to your preferred preview node.

Example:

```text
VAE Decode / IMAGE
  ├─ Preview node
  └─ GM JPEG Save
```

## HandpickerSuite integration

This node is independent from HandpickerSuite.

HandpickerSuite is not required unless `directory_pattern` contains `ckptname`.

When a `ckptname` pattern is selected, GM JPEG Save lazy-imports HandpickerSuite shared checkpoint information and reads `ckpt_name_safe`. If the information is unavailable, the node raises an error.

Recommended shared API on the HandpickerSuite side:

```python
def get_checkpoint_info():
    return {
        "ckpt_name_str": "data/foo_model.safetensors",
        "ckpt_name_safe": "data_foo_model",
    }
```

## JPEG settings

Recommended local batch/archive defaults:

```text
quality: 95
subsampling: 4:4:4
progressive: False
```

`progressive=True` is useful mainly for web display. For local batch generation, later inventory, and contact-sheet creation, the default is `False`.

## Install

Place this folder under `ComfyUI/custom_nodes/`:

```text
ComfyUI/custom_nodes/ComfyUI-GMImageSaver/
```

Restart ComfyUI.
