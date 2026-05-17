# OCR Tools

Local OCR setup for Russian and English text recognition.

Installed locally in this project:

- `local_tools/Tesseract-extracted/tesseract.exe`
- `local_tools/Tesseract-extracted/tessdata/rus.traineddata`
- `local_tools/Tesseract-extracted/tessdata/eng.traineddata`
- `local_tools/Tesseract-extracted/tessdata/osd.traineddata`

## Usage

OCR a local image:

```powershell
.\ocr_tools\ocr_image.ps1 -InputPath .\.tmp\some_page.jpg -Lang rus+eng -Psm 6
```

OCR an image URL:

```powershell
.\ocr_tools\ocr_image.ps1 -Url "https://example.com/page.jpg" -Lang rus+eng -Psm 6
```

Outputs are saved under `ocr_tools/output`.

Useful `--psm` modes:

- `3`: automatic page segmentation.
- `4`: single column of text.
- `6`: uniform block of text.
- `11`: sparse text.

For magazine pages, `-Psm 4` or `-Psm 6` usually works better than fully automatic mode.
