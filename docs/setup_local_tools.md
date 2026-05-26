# Local Tool Setup

Use the project init script after cloning the repository on a Windows machine.

```powershell
.\init.ps1
```

It installs tools locally under `local_tools/` and project caches under `node_cache/`.
Both are ignored by Git, so the repository stays small.
The detailed inventory of downloaded tools, source URLs, local paths, and Git
policy is maintained in `docs/downloaded_tools.md`.

## What It Installs

- ngspice 46 console binary from SourceForge.
- Tesseract OCR 5.5.0 Windows package, extracted locally.
- Tesseract language data: `rus`, `eng`, and `osd`.
- Optional Hunspell spell checker plus `ru_RU` and `en_US` dictionaries for OCR text checks.
- Python packages for page-layout detection before OCR: `opencv-python-headless`, `numpy`, and `pillow`, installed into the matching versioned directory under `local_tools/python_packages/`, for example `local_tools/python_packages/py312`.
- Go 1.26.3 portable for native layout-analysis tools.
- Node.js 20.11.1 portable, only if no system `node.exe` is found.
- 7-Zip portable, only if no system `7z.exe` is found.
- Node dependencies from `package.json`, currently `@resvg/resvg-js` for SVG to PNG rendering.

## Requirements

- Windows PowerShell or PowerShell 7.

The script can use already installed Node.js and 7-Zip. If they are missing, it downloads local portable copies under `local_tools/`.
For Python layout dependencies it uses `-PythonPath`, the `PYTHON` environment
variable, or the first runnable `python.exe`/`python`/`py.exe` on `PATH`.
Compiled wheels are installed per Python minor version, so Python 3.12 and 3.14
do not overwrite each other's local packages.
Project Python scripts load only the matching versioned package directory
(`local_tools/python_packages/pyXY`) for the interpreter that is currently
running. After changing or upgrading Python, rerun `.\init.ps1` so the matching
OpenCV/numpy/pillow wheels are installed for that interpreter.

For diagnostics, `POWER_AMP_PYTHON_PACKAGES` can point at one or more explicit
package directories separated by the platform path separator. The old unversioned
`local_tools/python_packages` root is ignored by default because it can contain
compiled wheels for another Python minor version; set
`POWER_AMP_ALLOW_LEGACY_PYTHON_PACKAGES=1` only when intentionally using that
legacy layout.

If you want to force a specific 7-Zip binary, pass it explicitly:

```powershell
.\init.ps1 -SevenZipPath "C:\path\to\7z.exe"
```

If you want to force the Python used for OpenCV layout dependencies, pass:

```powershell
.\init.ps1 -PythonPath "C:\path\to\python.exe"
```

The root `init.ps1` forwards to:

```text
scripts/setup_local_tools.ps1
```

## Options

```powershell
.\init.ps1 -Force
.\init.ps1 -SkipNgspice
.\init.ps1 -SkipOcr
.\init.ps1 -SkipSpellcheck
.\init.ps1 -InstallHunspell
.\init.ps1 -SkipLayoutCv
.\init.ps1 -SkipGo
.\init.ps1 -SkipNode
.\init.ps1 -PythonPath "C:\path\to\python.exe"
```

`-Force` redownloads/reextracts tools where applicable.

By default the init script offers to install Hunspell when it is missing. Choose no to keep using the built-in OCR heuristics in `scripts/spellcheck_text.py`. Use `-InstallHunspell` for unattended installation, or `-SkipSpellcheck` to skip the Hunspell prompt.
