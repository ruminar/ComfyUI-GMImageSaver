# v0.1.0 - Initial release

Initial public release of ComfyUI-GMImageSaver.

## Added
- GM Image JPEG Save node
- Direct ComfyUI IMAGE tensor to GraphicsMagick JPEG output
- JPEG-only, previewless output node
- Optional output_dir, label, and comment input pins
- directory_pattern based output organization
- filename_date_format support
- ProgressBar update per saved image
- GM_PATH / PATH based GraphicsMagick resolution
- Timeout support via GM_IMAGE_SAVER_TIMEOUT
- Loose coupling with HandpickerSuite via label input
