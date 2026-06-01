import datetime
import os
import re
import subprocess
from typing import List, Optional

import numpy as np
import folder_paths


_NODE_NAME = "GM Image JPEG Save"
_ENV_GM_PATH = "GM_PATH"
_JPEG_EXT = ".jpg"
_COUNTER_WIDTH = 4
_MAX_PART_LEN = 120
_GM_TIMEOUT_SECONDS = 120

_DIRECTORY_PATTERNS = [
    "none",
    "date",
    "prefix",
    "prefix_date",
    "prefix/date",
    "label",
    "label_date",
    "label/date",
    "prefix_label",
    "prefix_label_date",
    "prefix/label",
    "prefix/label/date",
]

_FILENAME_DATE_FORMATS = [
    "none",
    "yyyyMMdd",
    "yyyyMMdd_HHmm",
]

_SUBSAMPLING_VALUES = [
    "4:4:4",
    "4:2:2",
    "4:2:0",
]

_WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Windows-invalid characters, path separators, ASCII control chars, and hyphen/minus.
# The node intentionally uses underscores for generated names and does not emit '-' separators.
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f\-]+')
_MULTI_UNDERSCORE = re.compile(r'_+')
_COUNTER_RE_CACHE = {}


def _resolve_gm_command() -> str:
    """Resolve GraphicsMagick command.

    Priority:
    1. GM_PATH environment variable
    2. gm from PATH
    """
    gm_path = os.environ.get(_ENV_GM_PATH, "").strip().strip('"')
    return gm_path if gm_path else "gm"


def _sanitize_name(value: object, default: str, max_len: int = _MAX_PART_LEN) -> str:
    """Sanitize one filename/directory component.

    This is intentionally conservative for cross-platform ComfyUI workflows:
    - replaces Windows-forbidden characters and path separators
    - replaces hyphen/minus with underscore
    - trims trailing dots/spaces, which are problematic on Windows
    - protects Windows reserved device names
    """
    text = "" if value is None else str(value)
    text = text.strip()
    text = _INVALID_NAME_CHARS.sub("_", text)
    text = re.sub(r"\s+", "_", text)
    text = _MULTI_UNDERSCORE.sub("_", text)
    text = text.strip(" _.\t\r\n")

    if not text:
        text = default

    if len(text) > max_len:
        text = text[:max_len].rstrip(" _.\t\r\n") or default

    if text.upper() in _WINDOWS_RESERVED_NAMES:
        text = f"{text}_"

    return text


def _sanitize_output_dir(raw: object) -> Optional[str]:
    if raw is None:
        return None
    text = str(raw).strip().strip('"')
    return text if text else None


def _resolve_base_output_dir(output_dir: Optional[str]) -> str:
    """Resolve base output directory.

    - None/empty: ComfyUI output directory
    - absolute path: used as-is
    - relative path: under ComfyUI output directory
    """
    raw = _sanitize_output_dir(output_dir)
    if not raw:
        return folder_paths.get_output_directory()

    raw = os.path.expanduser(os.path.expandvars(raw))
    if os.path.isabs(raw):
        return os.path.normpath(raw)

    return os.path.normpath(os.path.join(folder_paths.get_output_directory(), raw))


def _filename_date_text(now: datetime.datetime, filename_date_format: str) -> str:
    if filename_date_format == "none":
        return ""
    if filename_date_format == "yyyyMMdd":
        return now.strftime("%Y%m%d")
    if filename_date_format == "yyyyMMdd_HHmm":
        return now.strftime("%Y%m%d_%H%M")
    raise ValueError(f"[{_NODE_NAME}] Unsupported filename_date_format: {filename_date_format}")


def _directory_parts(
    directory_pattern: str,
    prefix_safe: str,
    label_safe: str,
    dir_date_text: str,
) -> List[str]:
    uses_label = "label" in directory_pattern
    if uses_label and not label_safe:
        raise ValueError(
            f"[{_NODE_NAME}] directory_pattern uses label, but no label string was provided. "
            "Connect a STRING node to the optional label input, or choose a pattern without label."
        )

    if directory_pattern == "none":
        return []
    if directory_pattern == "date":
        return [dir_date_text]

    if directory_pattern == "prefix":
        return [prefix_safe]
    if directory_pattern == "prefix_date":
        return [f"{prefix_safe}_{dir_date_text}"]
    if directory_pattern == "prefix/date":
        return [prefix_safe, dir_date_text]

    if directory_pattern == "label":
        return [label_safe]
    if directory_pattern == "label_date":
        return [f"{label_safe}_{dir_date_text}"]
    if directory_pattern == "label/date":
        return [label_safe, dir_date_text]

    if directory_pattern == "prefix_label":
        return [f"{prefix_safe}_{label_safe}"]
    if directory_pattern == "prefix_label_date":
        return [f"{prefix_safe}_{label_safe}_{dir_date_text}"]
    if directory_pattern == "prefix/label":
        return [prefix_safe, label_safe]
    if directory_pattern == "prefix/label/date":
        return [prefix_safe, label_safe, dir_date_text]

    raise ValueError(f"[{_NODE_NAME}] Unsupported directory_pattern: {directory_pattern}")


def _build_filename_stem(prefix_safe: str, label_safe: str, filename_date: str) -> str:
    parts = [prefix_safe]
    if label_safe:
        parts.append(label_safe)
    if filename_date:
        parts.append(filename_date)
    return "_".join(parts)


def _next_counter(save_dir: str, stem: str) -> int:
    """Find next 4-digit counter for files named stem_NNNN.jpg."""
    cache_key = stem
    pattern = _COUNTER_RE_CACHE.get(cache_key)
    if pattern is None:
        pattern = re.compile(rf"^{re.escape(stem)}_(\d{{{_COUNTER_WIDTH},}})\.jpe?g$", re.IGNORECASE)
        _COUNTER_RE_CACHE[cache_key] = pattern

    max_seen = 0
    try:
        for name in os.listdir(save_dir):
            match = pattern.match(name)
            if match:
                try:
                    max_seen = max(max_seen, int(match.group(1)))
                except ValueError:
                    pass
    except FileNotFoundError:
        return 1

    return max_seen + 1


def _tensor_to_rgb_bytes(image) -> tuple[bytes, int, int]:
    """Convert one ComfyUI IMAGE tensor [H, W, C] float 0..1 to raw RGB bytes."""
    if hasattr(image, "detach"):
        image = image.detach()
    if hasattr(image, "cpu"):
        image = image.cpu()

    arr = image.numpy() if hasattr(image, "numpy") else np.asarray(image)
    arr = np.asarray(arr)

    if arr.ndim != 3:
        raise ValueError(f"[{_NODE_NAME}] Expected IMAGE tensor with shape [H, W, C], got shape {arr.shape}.")

    h, w, c = arr.shape
    if c == 1:
        arr = np.repeat(arr, 3, axis=2)
    elif c >= 3:
        arr = arr[:, :, :3]
    else:
        raise ValueError(f"[{_NODE_NAME}] Expected at least 1 channel, got {c}.")

    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    arr = np.ascontiguousarray(arr)
    return arr.tobytes(), w, h


def _run_graphicsmagick(
    gm_cmd: str,
    raw_rgb: bytes,
    width: int,
    height: int,
    output_path: str,
    quality: int,
    subsampling: str,
    progressive: bool,
    comment: Optional[str],
) -> None:
    cmd = [
        gm_cmd,
        "convert",
        "-size",
        f"{width}x{height}",
        "-depth",
        "8",
        "rgb:-",
        "-sampling-factor",
        subsampling,
        "-quality",
        str(int(quality)),
    ]

    if progressive:
        # Plane interlace produces progressive JPEG output for JPEG encoders that support it.
        cmd.extend(["-interlace", "Plane"])

    if comment is not None:
        comment_text = str(comment)
        if comment_text:
            cmd.extend(["-comment", comment_text])

    cmd.append(output_path)

    try:
        completed = subprocess.run(
            cmd,
            input=raw_rgb,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=_GM_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"[{_NODE_NAME}] GraphicsMagick executable was not found. "
            f"Set the {_ENV_GM_PATH} environment variable, or make sure 'gm' is available in PATH. "
            f"Resolved command: {gm_cmd!r}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"[{_NODE_NAME}] GraphicsMagick process timed out after {_GM_TIMEOUT_SECONDS} seconds."
        ) from exc

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        details = stderr or stdout or "No output from GraphicsMagick."
        raise RuntimeError(
            f"[{_NODE_NAME}] GraphicsMagick failed with exit code {completed.returncode}: {details}"
        )


class GMImageJpegSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "image"}),
                "directory_pattern": (_DIRECTORY_PATTERNS, {"default": "date"}),
                "filename_date_format": (_FILENAME_DATE_FORMATS, {"default": "none"}),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1}),
                "subsampling": (_SUBSAMPLING_VALUES, {"default": "4:4:4"}),
                "progressive": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                # Optional base output directory. Leave unconnected for ComfyUI/output.
                # Absolute paths are used as-is. Relative paths are resolved under ComfyUI/output.
                "output_dir": ("STRING", {"forceInput": True}),
                # Optional generic label string. Connect ckpt_name_safe, experiment name, or any label.
                "label": ("STRING", {"forceInput": True}),
                # Optional JPEG comment. No text field; connect from a STRING node if needed.
                "comment": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image/GMImageSaver"

    def save_images(
        self,
        images,
        filename_prefix,
        directory_pattern,
        filename_date_format,
        quality,
        subsampling,
        progressive,
        output_dir=None,
        label=None,
        comment=None,
    ):
        now = datetime.datetime.now()
        dir_date = now.strftime("%Y%m%d")
        filename_date = _filename_date_text(now, filename_date_format)

        prefix_safe = _sanitize_name(filename_prefix, default="image")
        label_raw = None if label is None else str(label).strip()
        label_safe = _sanitize_name(label_raw, default="label") if label_raw else ""

        base_dir = _resolve_base_output_dir(output_dir)
        dir_parts = _directory_parts(directory_pattern, prefix_safe, label_safe, dir_date)
        save_dir = os.path.normpath(os.path.join(base_dir, *dir_parts))
        os.makedirs(save_dir, exist_ok=True)

        filename_stem = _build_filename_stem(prefix_safe, label_safe, filename_date)
        counter = _next_counter(save_dir, filename_stem)
        gm_cmd = _resolve_gm_command()

        for image in images:
            raw_rgb, width, height = _tensor_to_rgb_bytes(image)

            while True:
                filename = f"{filename_stem}_{counter:0{_COUNTER_WIDTH}d}{_JPEG_EXT}"
                output_path = os.path.join(save_dir, filename)
                counter += 1
                if not os.path.exists(output_path):
                    break

            _run_graphicsmagick(
                gm_cmd=gm_cmd,
                raw_rgb=raw_rgb,
                width=width,
                height=height,
                output_path=output_path,
                quality=quality,
                subsampling=subsampling,
                progressive=progressive,
                comment=comment,
            )

        return {}


NODE_CLASS_MAPPINGS = {
    "GMImageJpegSave": GMImageJpegSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GMImageJpegSave": "GM Image JPEG Save",
}
