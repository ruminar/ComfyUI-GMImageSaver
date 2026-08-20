# v0.1.2 - Reliable long JPEG comments

This patch release fixes intermittent JPEG save failures caused by passing long comments directly to GraphicsMagick as a command-line argument.

## Fixed

* JPEG comments are now passed through a temporary UTF-8 file instead of directly on the command line.
* Long prompts no longer hit GraphicsMagick's per-argument length limit or the Windows command-line length limit.
* Comments beginning with `@` are no longer interpreted as arbitrary file references.
* Temporary comment files are removed after successful saves and when GraphicsMagick raises an error or times out.
* Operating-system execution errors now include the actual error instead of always reporting that GraphicsMagick is not installed.

## Comment handling

* Temporary comment files are written as UTF-8 without a BOM.
* BOM characters, NUL characters, unsupported control characters, and invalid Unicode surrogates are removed before saving.
* Tabs, line feeds, carriage returns, Japanese text, accented characters, and emoji are preserved.
* The existing 65,000-byte JPEG comment limit remains in place, with truncation performed only at a valid UTF-8 character boundary.
* No temporary file is created when the `comment` input is not connected, empty, or empty after normalization.
* One temporary comment file is reused for every image in the same batch.

## Notes

GraphicsMagick normalizes line endings read from a comment file to CRLF and appends a trailing CRLF. Line structure is preserved, but the stored comment is not guaranteed to be byte-for-byte identical to the input.

The agreed behavior and regression requirements are documented in `.spec/comment-handling.md` and covered by automated tests.

## Documentation

* Rebuilt `README.md` as the English documentation.
* Rebuilt `README.ja.md` as the corresponding Japanese documentation.
* Added language navigation links and synchronized both documents with the current implementation.
* Corrected the project description and documentation URL in `pyproject.toml`.

## Compatibility

Existing workflows remain compatible. The node inputs, outputs, directory behavior, filename behavior, JPEG settings, and previewless output behavior are unchanged.

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
