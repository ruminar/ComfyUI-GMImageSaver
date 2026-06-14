# v0.1.1 - Registry scan compatibility update

This release updates GraphicsMagick executable resolution and documentation to reduce Comfy Registry scanner warnings.

## Changed

* Removed `GM_PATH` support.
* Removed `GM_IMAGE_SAVER_TIMEOUT` support.
* GraphicsMagick is now resolved via `shutil.which("gm")`.
* The save timeout is now fixed at 300 seconds.
* Updated error messages to avoid environment-variable-based executable configuration wording.
* Updated README installation instructions.
* Updated GraphicsMagick links in README.

## Notes

GraphicsMagick must be installed separately.

Please make sure the `gm` command can be executed from the environment where ComfyUI is launched.

You can check it with:

```bash
gm version
```

After installing GraphicsMagick, restart ComfyUI.

## Compatibility

Existing workflows should continue to work as before, except environments that depended on `GM_PATH` must now make `gm` available to the ComfyUI process directly.

The node behavior remains the same:

* Direct ComfyUI `IMAGE` tensor to GraphicsMagick JPEG output
* No intermediate PNG file
* JPEG-only
* Previewless output node
* `label` input for checkpoint names or experiment labels
* Directory pattern based output organization
* Per-image progress bar updates
