# ComfyUI-GMImageSaver

GraphicsMagick-based image saver nodes for ComfyUI.

The first node, **GM Image JPEG Save**, is intentionally narrow:

- JPEG only
- no preview output
- no IMAGE output
- no intermediate PNG file
- direct raw RGB stream to GraphicsMagick
- 4-digit counters like `0001`, `0002`, ...
- optional external `output_dir` input pin
- optional generic `label` input pin
- optional JPEG `comment` input pin

For PNG output, use ComfyUI's standard Save Image node.

## Node

### GM Image JPEG Save

Category:

```text
image/GMImageSaver
```

Required inputs:

```text
images
filename_prefix
directory_pattern
filename_date_format
quality
subsampling
progressive
```

Optional input pins:

```text
output_dir
label
comment
```

The node is output-only and does not return preview images. For preview workflows, branch the IMAGE before this node and connect it to your preferred preview node.

## GraphicsMagick resolution

GraphicsMagick is required.

The node resolves GraphicsMagick in this order:

1. `GM_PATH` environment variable
2. `gm` from PATH

On Windows, install GraphicsMagick and enable the option to update PATH if available. After installing, restart ComfyUI so the updated PATH is visible.

If you do not want to edit PATH, set `GM_PATH` to the full path of `gm.exe`, for example:

```text
C:\Program Files\GraphicsMagick-1.3.45-Q16\gm.exe
```

## output_dir

`output_dir` is optional.

- unconnected or empty: ComfyUI `output` directory
- absolute path: used as-is
- relative path: resolved under ComfyUI `output`

Examples:

```text
output_dir unconnected
-> ComfyUI/output

output_dir = GMImageSaver
-> ComfyUI/output/GMImageSaver

output_dir = D:\images\jpeg
-> D:\images\jpeg
```

## label

`label` is a generic optional STRING input. The node does not know or import HandpickerSuite.

You can connect any string, for example:

- `ckpt_name_safe` from ComfyUI-CheckpointHandpickerSuite
- experiment name
- version label
- any other workflow-generated text

If `directory_pattern` uses `label`, the `label` input must be connected.

## directory_pattern

Directory dates are always `yyyyMMdd`.

Assume:

```text
output_dir = D:\images
filename_prefix = sample
label = meinamix_v11
date = 20260601
```

Patterns:

| directory_pattern | output directory |
|---|---|
| `none` | `D:\images` |
| `date` | `D:\images\20260601` |
| `prefix` | `D:\images\sample` |
| `prefix_date` | `D:\images\sample_20260601` |
| `prefix/date` | `D:\images\sample\20260601` |
| `label` | `D:\images\meinamix_v11` |
| `label_date` | `D:\images\meinamix_v11_20260601` |
| `label/date` | `D:\images\meinamix_v11\20260601` |
| `prefix_label` | `D:\images\sample_meinamix_v11` |
| `prefix_label_date` | `D:\images\sample_meinamix_v11_20260601` |
| `prefix/label` | `D:\images\sample\meinamix_v11` |
| `prefix/label/date` | `D:\images\sample\meinamix_v11\20260601` |

## filename_date_format

The filename is built like this:

```text
{filename_prefix}_{label?}_{filename_date?}_{counter:04}.jpg
```

Available filename date formats:

| filename_date_format | example filename |
|---|---|
| `none` | `sample_meinamix_v11_0001.jpg` |
| `yyyyMMdd` | `sample_meinamix_v11_20260601_0001.jpg` |
| `yyyyMMdd_HHmm` | `sample_meinamix_v11_20260601_1423_0001.jpg` |

The date text is determined once per node execution, so all images in the same batch use the same timestamp.

## JPEG settings

Recommended defaults:

```text
quality = 95
subsampling = 4:4:4
progressive = False
```

`progressive` is disabled by default because this node is aimed at local batch generation, later inventory, and contact-sheet workflows rather than web-first progressive display.

## Naming safety

Generated filename and directory components are sanitized for cross-platform use. Path separators, Windows-invalid characters, control characters, and hyphen/minus are replaced with underscores.

The base `output_dir` itself is not sanitized because it may be a full filesystem path.

## HandpickerSuite independence

This project does not import HandpickerSuite and does not read shared state from it.

To include checkpoint-safe names, connect HandpickerSuite's existing `ckpt_name_safe` STRING output to the optional `label` input.
