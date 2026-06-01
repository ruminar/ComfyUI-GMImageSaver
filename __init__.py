from .nodes import GMJpegSave

NODE_CLASS_MAPPINGS = {
    "GMJpegSave": GMJpegSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GMJpegSave": "GM JPEG Save",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
