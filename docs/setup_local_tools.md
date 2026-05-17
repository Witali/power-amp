# Local Tool Setup

Use the project init script after cloning the repository on a Windows machine.

```powershell
.\init.ps1
```

It installs tools locally under `local_tools/` and project caches under `node_cache/`.
Both are ignored by Git, so the repository stays small.

## What It Installs

- ngspice 46 console binary from SourceForge.
- Tesseract OCR 5.5.0 Windows package, extracted locally.
- Tesseract language data: `rus`, `eng`, and `osd`.
- Optional Hunspell spell checker plus `ru_RU` and `en_US` dictionaries for OCR text checks.
- Node.js 20.11.1 portable, only if no system `node.exe` is found.
- 7-Zip portable, only if no system `7z.exe` is found.
- Node dependencies from `package.json`, currently `@resvg/resvg-js` for SVG to PNG rendering.

## Requirements

- Windows PowerShell or PowerShell 7.

The script can use already installed Node.js and 7-Zip. If they are missing, it downloads local portable copies under `local_tools/`.

If you want to force a specific 7-Zip binary, pass it explicitly:

```powershell
.\init.ps1 -SevenZipPath "C:\path\to\7z.exe"
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
.\init.ps1 -SkipNode
```

`-Force` redownloads/reextracts tools where applicable.

By default the init script offers to install Hunspell when it is missing. Choose no to keep using the built-in OCR heuristics in `scripts/spellcheck_text.py`. Use `-InstallHunspell` for unattended installation, or `-SkipSpellcheck` to skip the Hunspell prompt.
