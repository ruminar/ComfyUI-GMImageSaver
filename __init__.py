from .nodes import GMImageJpegSave

NODE_CLASS_MAPPINGS = {
    "GMImageJpegSave": GMImageJpegSave,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GMImageJpegSave": "GM Image JPEG Save",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
