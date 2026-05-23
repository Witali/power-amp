# Downloaded Local Tools

Last updated: 2026-05-23.

This project keeps downloaded binaries, installers, package caches, and generated
tool output outside Git. Prefer `.tmp/tools/` for newly downloaded portable
tools such as OCR runtimes; existing tools may still live under `local_tools/`.
The default ignored locations are `.tmp/`, `local_tools/`, `node_cache/`, and
`node_modules/`.

When a new tool is added to the project workflow, update this file with the tool
name, version, source URL, local path, purpose, and whether it is committed.

## Inventory

| Tool | Version or package | Source | Local path | Purpose | Git policy |
| --- | --- | --- | --- | --- | --- |
| Go | `go1.26.3.windows-amd64.zip` | `https://go.dev/dl/go1.26.3.windows-amd64.zip` | `local_tools/go` | Build and test native Go layout-analysis tools. | Ignored. |
| Go build output | project-built binaries | Built by `scripts/build_go_tools.ps1` | `local_tools/bin` | Local compiled tools such as `layoutscan.exe`. | Ignored. |
| ngspice | `ngspice-46_64.7z` | `https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/46/ngspice-46_64.7z` | `local_tools/ngspice` | SPICE simulation backend for circuit checks. | Ignored. |
| Tesseract OCR | `tesseract.5.5.0.20241111.nupkg` | `https://community.chocolatey.org/api/v2/package/tesseract/5.5.0.20241111` | `local_tools/Tesseract-extracted` | OCR for Russian and English magazine pages. | Ignored. |
| Tesseract Russian data | `rus.traineddata` from `tessdata_fast` | `https://github.com/tesseract-ocr/tessdata_fast/raw/main/rus.traineddata` | `local_tools/Tesseract-extracted/tessdata` | Russian OCR language model. | Ignored. |
| Tesseract English data | `eng.traineddata` from `tessdata_fast` | `https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata` | `local_tools/Tesseract-extracted/tessdata` | English OCR language model. | Ignored. |
| Tesseract orientation data | `osd.traineddata` from `tessdata_fast` | `https://github.com/tesseract-ocr/tessdata_fast/raw/main/osd.traineddata` | `local_tools/Tesseract-extracted/tessdata` | Orientation and script detection for OCR preprocessing. | Ignored. |
| Hunspell | `hunspell.portable.1.7.0.nupkg` | `https://community.chocolatey.org/api/v2/package/hunspell.portable/1.7.0` | `local_tools/hunspell` | Optional spell checker for OCR text validation. | Ignored. |
| Hunspell fallback binary | `hunspell-msvc-Release-x64.zip` | `https://github.com/mlt/hunspell/releases/download/appveyor_v1.7.0/hunspell-msvc-Release-x64.zip` | `local_tools/hunspell` | Fallback executable if the portable package does not expose `hunspell.exe`. | Ignored. |
| Hunspell Russian dictionary | `ru_RU.aff`, `ru_RU.dic` | `https://raw.githubusercontent.com/LibreOffice/dictionaries/master/ru_RU/` | `local_tools/hunspell-dictionaries` | Russian spelling checks for OCR output. | Ignored. |
| Hunspell English dictionary | `en_US.aff`, `en_US.dic` | `https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/` | `local_tools/hunspell-dictionaries` | English spelling checks for OCR output. | Ignored. |
| Python layout packages | `opencv-python-headless`, `numpy`, `pillow` | PyPI via selected Python: `python -m pip install --target local_tools/python_packages/pyXY` | `local_tools/python_packages/pyXY` | OpenCV page segmentation, previews, and image processing. | Ignored. |
| Node.js | `node-v20.11.1-win-x64.zip` | `https://nodejs.org/dist/v20.11.1/node-v20.11.1-win-x64.zip` | `local_tools/node` | Portable Node runtime when system Node is unavailable. | Ignored. |
| npm dependencies | `@resvg/resvg-js` | npm registry from `package.json` | `node_modules/` and `node_cache/` | SVG rendering/linting support. | Ignored. |
| 7-Zip | `7zip.portable.nupkg` | `https://community.chocolatey.org/api/v2/package/7zip.portable` | `local_tools/7zip-portable` | Archive extraction for `.7z`, `.nupkg`, and installer payloads when system 7-Zip is unavailable. | Ignored. |

## Setup Scripts

- `init.ps1` forwards to `scripts/setup_local_tools.ps1`.
- `scripts/setup_local_tools.ps1` downloads and extracts the tools above when
  they are missing, unless the matching `-Skip...` option is used.
- Python layout packages are installed per Python minor version. Use
  `.\init.ps1 -PythonPath C:\path\to\python.exe` when the project scripts should
  use a specific interpreter.
- `scripts/build_go_tools.ps1` uses Go from `local_tools/go`, writes Go caches
  into `.tmp`, and builds local binaries into `local_tools/bin`.

## Download Policy

- On Windows, when a new software tool is needed, first look for a Microsoft
  Store package and offer that installation path before downloading portable
  archives or installers.
- Prefer official project sources for compilers and runtimes, for example
  `go.dev` for Go and `nodejs.org` for Node.js.
- Keep downloaded binary distributions and installers under ignored paths,
  preferring `.tmp/tools/` for new local tool payloads.
- Commit small, reproducible scripts and documentation, not downloaded tool
  payloads.
- Record new downloads in this file in the same change that introduces them.
