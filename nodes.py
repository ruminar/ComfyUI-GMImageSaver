import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import PurePath
from typing import Any, List, Optional, Tuple

import numpy as np

try:
    import folder_paths
except Exception:  # pragma: no cover - ComfyUI provides this module at runtime
    folder_paths = None

try:
    from comfy.utils import ProgressBar
except Exception:  # pragma: no cover - ComfyUI provides this module at runtime
    ProgressBar = None


DIRECTORY_PATTERNS = [
    "none",
    "date",
    "prefix",
    "prefix_date",
    "prefix/date",
    "label",
    "label_date",
    "label/date",
    "prefix_label",
    "prefix/label",
    "prefix_label_date",
    "prefix/label/date",
    "prefix_date_label",
    "prefix/date/label",
]

FILENAME_DATE_FORMATS = [
    "none",
    "yyyyMMdd",
    "yyyyMMdd_HHmm",
]

SUBSAMPLING_OPTIONS = ["4:4:4", "4:2:2", "4:2:0"]
SUBSAMPLING_TO_GM = {
    "4:4:4": "1x1,1x1,1x1",
    "4:2:2": "2x1,1x1,1x1",
    "4:2:0": "2x2,1x1,1x1",
}

INVALID_NAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WHITESPACE_RE = re.compile(r"\s+")
MAX_NAME_COMPONENT_LENGTH = 120
MAX_FILENAME_STEM_LENGTH = 220
MAX_JPEG_COMMENT_BYTES = 65000
JPEG_EXTENSION = ".jpg"
GM_TIMEOUT_SECONDS = 300

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


class _NoopProgressBar:
    def update(self, amount: int = 1):
        return None


def _make_progress_bar(total: int):
    if ProgressBar is None:
        return _NoopProgressBar()
    try:
        return ProgressBar(total)
    except Exception:
        return _NoopProgressBar()


def _get_comfy_output_directory() -> str:
    if folder_paths is None:
        raise RuntimeError("ComfyUI folder_paths module is not available.")
    return folder_paths.get_output_directory()


def _resolve_gm_command() -> str:
    gm_exec = shutil.which("gm")
    if gm_exec is None:
        raise RuntimeError(
            "GraphicsMagick executable 'gm' was not found. "
            "Please install GraphicsMagick and restart ComfyUI."
        )
    return gm_exec


def _sanitize_path_part(value: Any, fallback: str = "unnamed") -> str:
    text = str(value if value is not None else "").strip()
    text = INVALID_NAME_CHARS_RE.sub("_", text)
    text = WHITESPACE_RE.sub("_", text)
    text = text.strip("._ ")
    while "__" in text:
        text = text.replace("__", "_")

    if not text:
        text = fallback

    if text in (".", ".."):
        text = fallback

    stem = text.split(".", 1)[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        text = f"_{text}"

    if len(text) > MAX_NAME_COMPONENT_LENGTH:
        text = text[:MAX_NAME_COMPONENT_LENGTH].rstrip("._ ") or fallback

    return text


def _limit_filename_stem(stem: str) -> str:
    stem = stem.strip("._ ") or "image"
    if len(stem) > MAX_FILENAME_STEM_LENGTH:
        stem = stem[:MAX_FILENAME_STEM_LENGTH].rstrip("._ ") or "image"
    return stem


def _build_file_date_text(filename_date_format: str, now: datetime) -> str:
    if filename_date_format == "none":
        return ""
    if filename_date_format == "yyyyMMdd":
        return now.strftime("%Y%m%d")
    if filename_date_format == "yyyyMMdd_HHmm":
        return now.strftime("%Y%m%d_%H%M")
    raise ValueError(f"Unsupported filename_date_format: {filename_date_format}")


def _build_dir_date_text(now: datetime) -> str:
    return now.strftime("%Y%m%d")


def _is_relative_traversal(path_text: str) -> bool:
    parts = PurePath(path_text.replace("\\", "/")).parts
    return any(part == ".." for part in parts)


def _resolve_base_output_dir(output_dir: Optional[str]) -> str:
    if output_dir is None:
        return _get_comfy_output_directory()

    raw = str(output_dir).strip()
    if not raw:
        return _get_comfy_output_directory()

    if os.path.isabs(raw):
        return os.path.normpath(raw)

    if _is_relative_traversal(raw):
        raise RuntimeError(
            "Relative output_dir must not contain parent-directory traversal."
        )

    return os.path.normpath(os.path.join(_get_comfy_output_directory(), raw))


def _requires_label(directory_pattern: str) -> bool:
    return "label" in directory_pattern


def _build_directory_parts(
    directory_pattern: str,
    prefix_safe: str,
    label_safe: Optional[str],
    dir_date_text: str,
) -> List[str]:
    if directory_pattern not in DIRECTORY_PATTERNS:
        raise ValueError(f"Unsupported directory_pattern: {directory_pattern}")

    if _requires_label(directory_pattern) and not label_safe:
        raise RuntimeError(
            "directory_pattern uses label, but no label string was provided. "
            "Connect a STRING node to the label input, or choose a pattern without label."
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
    if directory_pattern == "prefix/label":
        return [prefix_safe, label_safe]
    if directory_pattern == "prefix_label_date":
        return [f"{prefix_safe}_{label_safe}_{dir_date_text}"]
    if directory_pattern == "prefix/label/date":
        return [prefix_safe, label_safe, dir_date_text]
    if directory_pattern == "prefix_date_label":
        return [f"{prefix_safe}_{dir_date_text}_{label_safe}"]
    if directory_pattern == "prefix/date/label":
        return [prefix_safe, dir_date_text, label_safe]

    raise ValueError(f"Unsupported directory_pattern: {directory_pattern}")


def _build_save_dir(
    output_dir: Optional[str],
    directory_pattern: str,
    prefix_safe: str,
    label_safe: Optional[str],
    dir_date_text: str,
) -> str:
    base_dir = _resolve_base_output_dir(output_dir)
    parts = _build_directory_parts(directory_pattern, prefix_safe, label_safe, dir_date_text)
    save_dir = os.path.join(base_dir, *parts) if parts else base_dir
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def _build_filename_stem(
    prefix_safe: str,
    label_safe: Optional[str],
    file_date_text: str,
) -> str:
    parts = [prefix_safe]
    if label_safe:
        parts.append(label_safe)
    if file_date_text:
        parts.append(file_date_text)
    return _limit_filename_stem("_".join(parts))


def _next_counter(save_dir: str, stem: str) -> int:
    prefix = f"{stem}_"
    max_counter = 0

    try:
        names = os.listdir(save_dir)
    except FileNotFoundError:
        return 1

    for name in names:
        lower_name = name.lower()
        if not lower_name.endswith(JPEG_EXTENSION):
            continue
        if not name.startswith(prefix):
            continue
        tail = name[len(prefix):-len(JPEG_EXTENSION)]
        if len(tail) == 4 and tail.isdigit():
            max_counter = max(max_counter, int(tail))

    return max_counter + 1


def _tensor_to_rgb_bytes_and_size(image_tensor) -> Tuple[bytes, int, int]:
    img = image_tensor.detach().cpu().numpy()
    img = np.clip(img * 255.0, 0, 255).astype(np.uint8)

    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, axis=2)

    if img.ndim != 3:
        raise RuntimeError(
            f"Expected image tensor with 2 or 3 dimensions, got shape {img.shape}."
        )

    height, width, channels = img.shape

    if channels == 1:
        img = np.repeat(img, 3, axis=2)
    elif channels == 3:
        pass
    elif channels == 4:
        img = img[:, :, :3]
    else:
        raise RuntimeError(
            f"Expected 1, 3, or 4 channels, got shape {img.shape}."
        )

    img = np.ascontiguousarray(img)
    return img.tobytes(), width, height


def _normalize_comment(comment: Optional[str]) -> Optional[str]:
    if comment is None:
        return None
    text = str(comment)
    if not text:
        return None

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_JPEG_COMMENT_BYTES:
        encoded = encoded[:MAX_JPEG_COMMENT_BYTES]
        text = encoded.decode("utf-8", errors="ignore")

    return text


class GMImageJpegSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "image"}),
                "directory_pattern": (DIRECTORY_PATTERNS, {"default": "prefix/date"}),
                "filename_date_format": (FILENAME_DATE_FORMATS, {"default": "none"}),
                "quality": ("INT", {"default": 80, "min": 1, "max": 100, "step": 1}),
                "subsampling": (SUBSAMPLING_OPTIONS, {"default": "4:2:2"}),
                "progressive": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "output_dir": ("STRING", {"forceInput": True}),
                "label": ("STRING", {"forceInput": True}),
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
        now = datetime.now()
        prefix_safe = _sanitize_path_part(filename_prefix, fallback="image")

        label_safe = None
        if label is not None and str(label).strip():
            label_safe = _sanitize_path_part(label, fallback="label")

        dir_date_text = _build_dir_date_text(now)
        file_date_text = _build_file_date_text(filename_date_format, now)

        save_dir = _build_save_dir(
            output_dir=output_dir,
            directory_pattern=directory_pattern,
            prefix_safe=prefix_safe,
            label_safe=label_safe,
            dir_date_text=dir_date_text,
        )

        stem = _build_filename_stem(prefix_safe, label_safe, file_date_text)
        counter = _next_counter(save_dir, stem)

        gm_cmd = _resolve_gm_command()
        sampling_factor = SUBSAMPLING_TO_GM[subsampling]
        comment_text = _normalize_comment(comment)
        pbar = _make_progress_bar(len(images))

        for image in images:
            filename = f"{stem}_{counter:04}{JPEG_EXTENSION}"
            out_path = os.path.join(save_dir, filename)
            rgb_bytes, width, height = _tensor_to_rgb_bytes_and_size(image)

            cmd = [
                gm_cmd,
                "convert",
                "-size",
                f"{width}x{height}",
                "-depth",
                "8",
                "rgb:-",
                "-sampling-factor",
                sampling_factor,
                "-quality",
                str(int(quality)),
            ]

            if progressive:
                cmd += ["-interlace", "Plane"]

            if comment_text:
                cmd += ["-comment", comment_text]

            cmd.append(out_path)

            try:
                result = subprocess.run(
                    cmd,
                    input=rgb_bytes,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=GM_TIMEOUT_SECONDS,
                    shell=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"GraphicsMagick timed out after {GM_TIMEOUT_SECONDS} seconds "
                    f"while saving '{out_path}'."
                ) from exc
            except OSError as exc:
                raise RuntimeError(
                    "Failed to execute GraphicsMagick. "
                    "Please install GraphicsMagick and restart ComfyUI."
                ) from exc

            if result.returncode != 0:
                stderr_text = result.stderr.decode(errors="ignore").strip()
                raise RuntimeError(
                    f"GraphicsMagick failed while saving '{out_path}'.\n"
                    f"stderr: {stderr_text}"
                )

            counter += 1
            pbar.update(1)

        return {}
