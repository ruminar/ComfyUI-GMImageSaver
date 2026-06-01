import importlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

try:
    import folder_paths
except Exception:  # pragma: no cover - ComfyUI provides this module at runtime
    folder_paths = None


DIRECTORY_PATTERNS = [
    "none",
    "date",
    "prefix_date",
    "prefix/date",
    "ckptname_date",
    "ckptname/date",
    "prefix_ckptname_date",
    "prefix/ckptname/date",
]

DATE_FORMATS = [
    "none",
    "yyyyMMdd",
    "yyyyMMdd_HHmm",
]

SUBSAMPLING_OPTIONS = [
    "4:4:4",
    "4:2:2",
    "4:2:0",
]

# GraphicsMagick/ImageMagick-style JPEG sampling factors.
# These are safer than relying on 4:4:4 labels being accepted directly.
SUBSAMPLING_TO_GM = {
    "4:4:4": "1x1,1x1,1x1",
    "4:2:2": "2x1,1x1,1x1",
    "4:2:0": "2x2,1x1,1x1",
}

INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
WHITESPACE_RE = re.compile(r"\s+")
COUNTER_RE_CACHE: Dict[str, re.Pattern] = {}
MAX_PATH_PART_LENGTH = 120
MAX_FILENAME_STEM_LENGTH = 220
MAX_JPEG_COMMENT_BYTES = 65000

HANDPICKER_SHARED_MODULE_CANDIDATES = [
    # Recommended package-style names.
    "ComfyUI_HandpickerSuite.handpicker_shared",
    "ComfyUI_HandpickerSuite.shared",
    "HandpickerSuite.handpicker_shared",
    "HandpickerSuite.shared",
    # Some custom node loaders may register modules with a custom_nodes prefix.
    "custom_nodes.ComfyUI_HandpickerSuite.handpicker_shared",
    "custom_nodes.ComfyUI_HandpickerSuite.shared",
    "custom_nodes.HandpickerSuite.handpicker_shared",
    "custom_nodes.HandpickerSuite.shared",
]


def _get_comfy_output_directory() -> str:
    if folder_paths is None:
        raise RuntimeError("ComfyUI folder_paths module is not available.")
    return folder_paths.get_output_directory()


def _sanitize_path_part(value: Any, fallback: str = "unnamed") -> str:
    text = str(value if value is not None else "").strip()
    text = INVALID_PATH_CHARS_RE.sub("_", text)
    text = WHITESPACE_RE.sub("_", text)
    text = text.strip("._ ")
    if not text:
        text = fallback
    if len(text) > MAX_PATH_PART_LENGTH:
        text = text[:MAX_PATH_PART_LENGTH].rstrip("._ ") or fallback
    return text


def _limit_filename_stem(stem: str) -> str:
    stem = stem.strip("._ ") or "image"
    if len(stem) > MAX_FILENAME_STEM_LENGTH:
        stem = stem[:MAX_FILENAME_STEM_LENGTH].rstrip("._ ") or "image"
    return stem


def _requires_ckptname(directory_pattern: str) -> bool:
    return "ckptname" in directory_pattern


def _build_file_date_text(date_format: str, now: datetime) -> str:
    if date_format == "none":
        return ""
    if date_format == "yyyyMMdd":
        return now.strftime("%Y%m%d")
    if date_format == "yyyyMMdd_HHmm":
        return now.strftime("%Y%m%d_%H%M")
    raise ValueError(f"Unsupported date_format: {date_format}")


def _build_dir_date_text(now: datetime) -> str:
    return now.strftime("%Y%m%d")


def _resolve_base_output_dir(output_dir: Optional[str]) -> str:
    if output_dir is None:
        return _get_comfy_output_directory()

    raw = str(output_dir).strip()
    if not raw:
        return _get_comfy_output_directory()

    raw = os.path.expanduser(os.path.expandvars(raw))

    if os.path.isabs(raw):
        return os.path.normpath(raw)

    return os.path.normpath(os.path.join(_get_comfy_output_directory(), raw))


def _build_directory_parts(
    directory_pattern: str,
    prefix_safe: str,
    ckpt_name_safe: Optional[str],
    dir_date_text: str,
) -> List[str]:
    if directory_pattern not in DIRECTORY_PATTERNS:
        raise ValueError(f"Unsupported directory_pattern: {directory_pattern}")

    if _requires_ckptname(directory_pattern) and not ckpt_name_safe:
        raise RuntimeError(
            "directory_pattern uses ckptname, but HandpickerSuite checkpoint info was not available. "
            "Run a HandpickerSuite checkpoint node before GM JPEG Save, or choose a directory_pattern without ckptname."
        )

    ckpt = _sanitize_path_part(ckpt_name_safe, fallback="checkpoint") if ckpt_name_safe else None

    if directory_pattern == "none":
        return []
    if directory_pattern == "date":
        return [dir_date_text]
    if directory_pattern == "prefix_date":
        return [f"{prefix_safe}_{dir_date_text}"]
    if directory_pattern == "prefix/date":
        return [prefix_safe, dir_date_text]
    if directory_pattern == "ckptname_date":
        return [f"{ckpt}_{dir_date_text}"]
    if directory_pattern == "ckptname/date":
        return [ckpt, dir_date_text]
    if directory_pattern == "prefix_ckptname_date":
        return [f"{prefix_safe}_{ckpt}_{dir_date_text}"]
    if directory_pattern == "prefix/ckptname/date":
        return [prefix_safe, ckpt, dir_date_text]

    raise ValueError(f"Unsupported directory_pattern: {directory_pattern}")


def _resolve_save_dir(
    output_dir: Optional[str],
    directory_pattern: str,
    prefix_safe: str,
    ckpt_name_safe: Optional[str],
    now: datetime,
) -> str:
    base_dir = _resolve_base_output_dir(output_dir)
    parts = _build_directory_parts(
        directory_pattern=directory_pattern,
        prefix_safe=prefix_safe,
        ckpt_name_safe=ckpt_name_safe,
        dir_date_text=_build_dir_date_text(now),
    )
    save_dir = os.path.join(base_dir, *parts)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def _build_filename_stem(prefix_safe: str, date_format: str, now: datetime) -> str:
    parts = [prefix_safe]
    date_text = _build_file_date_text(date_format, now)
    if date_text:
        parts.append(date_text)
    return _limit_filename_stem("_".join(parts))


def _counter_regex_for_stem(stem: str) -> re.Pattern:
    pattern = COUNTER_RE_CACHE.get(stem)
    if pattern is None:
        pattern = re.compile(rf"^{re.escape(stem)}_(\d{{4}})\.jpg$", re.IGNORECASE)
        COUNTER_RE_CACHE[stem] = pattern
    return pattern


def _find_next_counter(save_dir: str, stem: str) -> int:
    regex = _counter_regex_for_stem(stem)
    highest = 0
    try:
        names = os.listdir(save_dir)
    except FileNotFoundError:
        return 1

    for name in names:
        match = regex.match(name)
        if match:
            try:
                highest = max(highest, int(match.group(1)))
            except ValueError:
                pass

    return highest + 1


def _make_unique_output_path(save_dir: str, stem: str, start_counter: int) -> tuple[str, int]:
    counter = start_counter
    while counter <= 9999:
        filename = f"{stem}_{counter:04d}.jpg"
        path = os.path.join(save_dir, filename)
        if not os.path.exists(path):
            return path, counter
        counter += 1
    raise RuntimeError(
        f"No available 4-digit counter remains for stem '{stem}' in '{save_dir}'."
    )


def _image_tensor_to_ppm_bytes(image_tensor: Any) -> bytes:
    # ComfyUI IMAGE tensors are generally HWC float tensors in 0.0-1.0 range.
    if hasattr(image_tensor, "detach"):
        array = image_tensor.detach().cpu().numpy()
    elif hasattr(image_tensor, "cpu"):
        array = image_tensor.cpu().numpy()
    else:
        array = np.asarray(image_tensor)

    if array.ndim != 3:
        raise ValueError(f"Expected image tensor with shape HWC, got shape {array.shape!r}.")

    if array.shape[2] == 4:
        # JPEG has no alpha. ComfyUI IMAGE is normally RGB, but if an RGBA-like
        # tensor arrives, keep the RGB channels and ignore alpha.
        array = array[:, :, :3]

    if array.shape[2] != 3:
        raise ValueError(f"Expected 3 RGB channels, got shape {array.shape!r}.")

    array = np.clip(array * 255.0, 0, 255).astype(np.uint8)
    array = np.ascontiguousarray(array)

    height, width, _ = array.shape
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    return header + array.tobytes()


def _resolve_gm_command() -> str:
    gm_path = os.environ.get("GM_PATH", "").strip()
    return gm_path if gm_path else "gm"


def _validate_comment(comment: Optional[str]) -> Optional[str]:
    if comment is None:
        return None
    text = str(comment)
    if text == "":
        return None
    if "\x00" in text:
        raise ValueError("JPEG comment must not contain NUL characters.")
    if len(text.encode("utf-8")) > MAX_JPEG_COMMENT_BYTES:
        raise ValueError(
            f"JPEG comment is too long. Keep it under {MAX_JPEG_COMMENT_BYTES} bytes."
        )
    return text


def _extract_checkpoint_info_from_module(module: Any) -> Optional[Dict[str, Any]]:
    # Preferred API.
    getter = getattr(module, "get_checkpoint_info", None)
    if callable(getter):
        info = getter()
        if isinstance(info, dict):
            return info

    # Common fallback names.
    for attr_name in (
        "checkpoint_info",
        "current_checkpoint_info",
        "shared_state",
        "state",
        "HANDPICKER_STATE",
        "CHECKPOINT_INFO",
    ):
        info = getattr(module, attr_name, None)
        if isinstance(info, dict):
            return info

    return None


def _resolve_handpicker_info() -> Dict[str, Any]:
    import_errors: List[str] = []

    for module_name in HANDPICKER_SHARED_MODULE_CANDIDATES:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            import_errors.append(f"{module_name}: {exc}")
            continue

        info = _extract_checkpoint_info_from_module(module)
        if info:
            return info

    # Last resort: scan already-loaded modules. This keeps GM ImageSaver as a
    # soft dependency and avoids importing HandpickerSuite unless needed.
    for module_name, module in list(sys.modules.items()):
        lower_name = module_name.lower()
        if "handpicker" not in lower_name:
            continue
        info = _extract_checkpoint_info_from_module(module)
        if info:
            return info

    raise RuntimeError(
        "directory_pattern uses ckptname, but HandpickerSuite checkpoint info could not be resolved. "
        "Expected a shared module exposing get_checkpoint_info() or a dict containing ckpt_name_safe. "
        "Choose a directory_pattern without ckptname, or ensure HandpickerSuite has run before GM JPEG Save."
    )


def _resolve_ckpt_name_safe() -> str:
    info = _resolve_handpicker_info()
    ckpt_name_safe = info.get("ckpt_name_safe")
    if not ckpt_name_safe:
        raise RuntimeError(
            "HandpickerSuite checkpoint info was found, but ckpt_name_safe was missing or empty."
        )
    return _sanitize_path_part(ckpt_name_safe, fallback="checkpoint")


def _save_one_jpeg_with_gm(
    image_tensor: Any,
    out_path: str,
    quality: int,
    subsampling: str,
    progressive: bool,
    comment: Optional[str],
) -> None:
    gm_cmd = _resolve_gm_command()
    ppm_bytes = _image_tensor_to_ppm_bytes(image_tensor)
    sampling_factor = SUBSAMPLING_TO_GM.get(subsampling)
    if sampling_factor is None:
        raise ValueError(f"Unsupported subsampling: {subsampling}")

    cmd = [
        gm_cmd,
        "convert",
        "ppm:-",
        "-sampling-factor",
        sampling_factor,
        "-quality",
        str(int(quality)),
    ]

    if progressive:
        cmd += ["-interlace", "Plane"]

    validated_comment = _validate_comment(comment)
    if validated_comment is not None:
        cmd += ["-comment", validated_comment]

    cmd.append(out_path)

    try:
        result = subprocess.run(
            cmd,
            input=ppm_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        gm_hint = shutil.which("gm")
        extra = "" if gm_hint else " 'gm' was not found in PATH."
        raise RuntimeError(
            "GraphicsMagick executable was not found. "
            "Set the GM_PATH environment variable, or make sure 'gm' is available in PATH."
            + extra
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        stdout = result.stdout.decode("utf-8", errors="replace")
        raise RuntimeError(
            "GraphicsMagick failed while saving JPEG.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
        )


class GMJpegSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "image"}),
                "directory_pattern": (DIRECTORY_PATTERNS, {"default": "date"}),
                "date_format": (DATE_FORMATS, {"default": "none"}),
                "quality": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1}),
                "subsampling": (SUBSAMPLING_OPTIONS, {"default": "4:4:4"}),
                "progressive": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                # Connect from a STRING/text node. If unconnected or empty,
                # ComfyUI's standard output directory is used.
                "output_dir": ("STRING", {"forceInput": True}),
                # Connect from a STRING/text node. If unconnected or empty,
                # no JPEG comment is embedded.
                "comment": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image/save"

    def save_images(
        self,
        images,
        filename_prefix,
        directory_pattern,
        date_format,
        quality,
        subsampling,
        progressive,
        output_dir=None,
        comment=None,
    ):
        now = datetime.now()
        prefix_safe = _sanitize_path_part(filename_prefix, fallback="image")

        ckpt_name_safe = None
        if _requires_ckptname(directory_pattern):
            ckpt_name_safe = _resolve_ckpt_name_safe()

        save_dir = _resolve_save_dir(
            output_dir=output_dir,
            directory_pattern=directory_pattern,
            prefix_safe=prefix_safe,
            ckpt_name_safe=ckpt_name_safe,
            now=now,
        )

        stem = _build_filename_stem(prefix_safe, date_format, now)
        next_counter = _find_next_counter(save_dir, stem)

        for image in images:
            out_path, used_counter = _make_unique_output_path(save_dir, stem, next_counter)
            _save_one_jpeg_with_gm(
                image_tensor=image,
                out_path=out_path,
                quality=quality,
                subsampling=subsampling,
                progressive=progressive,
                comment=comment,
            )
            next_counter = used_counter + 1

        # Intentionally no preview, no IMAGE output, no UI image list.
        return {}
