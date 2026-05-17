# Radio.ru OCR Workflow

Use this note for `archive.radio.ru` scans, especially December annual contents pages. The word "contents" means the printed yearly `Содержание журнала "Радио" за ... год` pages.

## Main lesson

Do not OCR a whole contents page as a single text block when it has multiple newspaper-style columns. Tesseract often joins the left and right halves of the page into one line, which produces fluent-looking but meaningless text. Crop the page into columns first, then OCR each column from top to bottom.

## Current local tool

Script:

```powershell
scripts\ocr_radio_ru_page_columns.ps1
```

Useful sample command:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath .tmp\pre1971\annual_contents\1970-12\f.1970-12.064.jpg -AutoColumns -AutoOnly -PsmModes 6 -OcrProfiles prose,technical,sauvola -Refresh
```

The script crops margins, can try fixed 1, 2, and 3 column layouts, and can also find column breaks automatically with `-AutoColumns`. It runs Tesseract on each column and writes merged text variants under `.tmp\ocr_column_trials\...`.

Before running OCR, the script can also call the OpenCV page-layout detector:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath <scan.jpg> -DetectLayout -ColumnCounts 2 -PsmModes 4 -OcrProfiles prose,technical
```

This writes a preliminary page split to `.tmp\page_layout\<page>\layout.json`, block crops under `.tmp\page_layout\<page>\blocks\`, and a preview overlay `.tmp\page_layout\<page>\preview.png`. Human-facing preview labels include `text`, `image`, `schematic`, `diagram`, `table`, and `other`; the stored JSON class name for schematics is kept unchanged for compatibility with existing scripts. Text blocks also include an `orientation` field (`horizontal`, `vertical`, `diagonal`, or `unknown`) so large titles, sideways margin labels and rotated captions can be handled separately from normal prose columns. Text blocks that are almost entirely nested inside a larger text block are suppressed to avoid duplicate OCR regions and duplicate preview labels. Visual blocks may also include rectilinear `outline` polygons for pages where prose flows around a schematic or photograph: the detector starts from a rectangular visual block and subtracts only larger text blocks touching its edges, which keeps previews readable and avoids lumpy contours around every drawn line. Visual blocks also get `caption_candidates` pointing to nearby small text blocks that may contain labels such as `Рис. 2`; if a schematic or diagram has no separate caption text block, the detector adds a conservative lower-left internal caption probe for later OCR. Caption candidate areas are highlighted in the preview with a transparent yellow overlay. Text blocks that fall inside a schematic outline are suppressed after classification, because component labels and values should remain part of the schematic instead of becoming OCR prose crops. When `ocr_radio_ru_page_columns.ps1` runs with `-DetectLayout`, it OCRs those caption candidates separately, writes `figure_links.md` and machine-readable `figure_links.json`, then appends the same figure-link table to merged OCR outputs. The detector is a lightweight hybrid: OpenCV extracts candidate rectangles, splits likely margin strips at internal vertical gaps or colored side bands, and a small OpenCV `ANN_MLP` classifies blocks from visual features. Use the preview image as a quick sanity check before trusting an OCR run.

Tesseract runs are parallelized by default. If `-MaxParallelOcr` is not set, the scripts use half of the available logical CPU threads, rounded down but never below one process. Each Tesseract process is started with `OMP_THREAD_LIMIT=1` by default, so the external process count is the main load limiter. Override it when needed:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath <scan.jpg> -AutoColumns -AutoOnly -PsmModes 4,6 -MaxParallelOcr 2 -TesseractThreadLimit 1
```

For a very slow machine, reduce `-MaxParallelOcr` to `1` or `2`. For a strong desktop, increase it cautiously; Tesseract is CPU and memory hungry on full-page magazine scans.

The December contents search script uses the same `-MaxParallelOcr` and `-TesseractThreadLimit` parameters:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\search_radio_ru_annual_contents.ps1 -FromYear 1970 -ToYear 1960 -TailPages 16 -MaxParallelOcr 2 -OcrProfile technical
```

For `archive.radio.ru`, the search script follows the preview page to the full-size scan viewer and prefers `b.YYYY-MM.NNN.jpg` images. It falls back to `f.*` and then `p.*` scans when the high-quality page is not available.

By default the script now also writes corrected OCR text:

- raw OCR: `merged.<profile>.psm6.txt`;
- corrected OCR: `merged.<profile>.psm6.corrected.txt`;
- correction log: `merged.<profile>.psm6.corrections.tsv`.

Search the corrected file first, but keep the raw file and scan as the authority for questionable rows.

## OCR profiles

The column OCR script can run several Tesseract profiles against the same crop:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath <scan.jpg> -AutoColumns -AutoOnly -PsmModes 4,6 -OcrProfiles prose,technical,sauvola
```

The annual contents search script uses one profile per run:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\search_radio_ru_annual_contents.ps1 -FromYear 2000 -ToYear 1990 -TailPages 16 -OcrProfile technical
```

Profiles:

- `prose`: general Russian magazine text with English symbols; dictionaries stay enabled.
- `technical`: part designators, transistor names and tables; Tesseract system/frequency dictionaries are disabled so `VT1`, `КТ315`, `УНЧ` and similar tokens are less aggressively "corrected".
- `sauvola`: local thresholding for uneven scans, yellowed paper and difficult dark/light backgrounds.

All profiles use the local word list `ocr_tools\radio_ru_user_words.txt`. Add amplifier terms, part designators and transistor names there when recurring OCR mistakes appear.

Column OCR output includes both profile and page segmentation mode in the file name, for example `merged.technical.psm6.txt`. The summary table also reports `Profile` and `Psm`, so compare variants by score before reading the best text.

## Reference-text calibration

When an article has an online text reprint, use it only as a temporary OCR calibration reference. Keep downloaded reference HTML files under `.tmp\ocr_reference_texts\`, not in the repository. The helper script compares local OCR variants with reference text and writes a TSV report:

```powershell
python scripts\compare_ocr_reference.py `
  --reference .tmp\ocr_reference_texts\ageev_superlinear_diagram.html `
  --candidate-root .tmp\radio_ru_1997_2000\article_ocr_fixed2 `
  --glob "merged*.txt" `
  --out .tmp\ocr_reference_texts\comparison.tsv
```

For the checked 1999 amplifier pages, fixed two-column OCR with `psm 4` matched online references better than `psm 6`. Use this as the default for normal article pages:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath <scan.jpg> -ColumnCounts 2 -PsmModes 4 -OcrProfiles prose,technical -MaxParallelOcr 2 -TesseractThreadLimit 1
```

See `study/amp_no_feedback_study/radio_ru_ocr_reference_sources_1997_2000.md` for the current source list and calibration notes.

## Automatic column detection

Use:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath <scan.jpg> -AutoColumns -AutoOnly -PsmModes 6
```

The automatic mode:

- crops page margins;
- builds a foreground mask with an Otsu threshold;
- treats the smaller luminance class as foreground, so both dark text on light paper and light text on a dark background can be detected;
- builds a vertical foreground-density projection;
- smooths the projection and selects wide low-density runs as column gaps;
- writes `auto_layout.tsv` with threshold, foreground polarity, density limit and split coordinates;
- writes `auto_density.tsv` for debugging the detected gap profile.

Dark crops are automatically inverted before OCR so white text on a dark background becomes dark text on light background. Disable this only for testing with `-NoAutoInvert`.

## Mode guidance

- For two-column annual contents pages, `columns2/merged.technical.psm6.txt` or `columns2/merged.prose.psm6.txt` is usually the first candidate to inspect.
- For three-column pages, inspect `columns3/merged.technical.psm6.txt` and `columns3/merged.prose.psm4.txt`.
- For mixed scans, start with `-AutoColumns -AutoOnly -PsmModes 6`; if the split is wrong, inspect `auto_density.tsv`, then try fixed `-ColumnCounts 2,3`.
- `psm 6` works well when a cropped column is a uniform block of entries.
- `psm 4` can be better when a column has separated section headings and irregular spacing.
- `psm 3` is a useful fallback, but on the tested 1970 contents page it was generally noisier.

Disable text correction only when debugging the raw OCR:

```powershell
& 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File scripts\ocr_radio_ru_page_columns.ps1 -InputPath <scan.jpg> -AutoColumns -AutoOnly -PsmModes 6 -NoTextCorrection
```

## Spell/OCR Quality Check

After OCR, run the text checker on the output folder:

```powershell
python scripts\project_tasks.py spellcheck .tmp\ocr_column_trials --out .tmp\spellcheck_report.tsv
```

The checker uses Hunspell with `ru_RU` if it is installed. Without Hunspell it falls back to OCR-focused heuristics: mixed Cyrillic/Latin words, digits inside Russian words, and unusually long Cyrillic tokens that often indicate a bad column split. Technical terms are allowed through `ocr_tools\radio_ru_user_words.txt`.

## Text Correction

The correction pass is heuristic and conservative enough for search, not for final quotation. It currently fixes:

- Latin/Cyrillic lookalikes in mixed words and single-letter initials;
- common `Радио`/`радиостанция`/`радиоприемник` errors;
- amplifier search terms such as `транзисторный`, `усилитель`, `НЧ`, `УНЧ`;
- common annual contents headings;
- some recurring author/title fragments seen in 1960s-1970s pages.

For example, on `f.1970-12.064.jpg` the corrected text recovers lines like `транзисторный усилитель НЧ`, `бестрансформаторный УНЧ`, `универсальный усилитель НЧ`, `Выходной усилитель НЧ`, and `транзисторные усилители с непосредственной связью`.

## Test result

On `Радио`, 1970 No. 12, printed page 59 (`f.1970-12.064.jpg`), whole-page OCR mixed the left and right page columns. Automatic splitting found the column gap at `x=498`, and `auto_columns2/merged.psm6.txt` matched the manually selected two-column result. The text still contains OCR mistakes, but article rows like transistor/audio amplifier entries remain separable enough for manual verification against the scan.

Synthetic dark-background test: `synthetic_light_on_dark_3cols_wide_gaps.png` used three columns of white text on a dark background. Automatic mode classified foreground as bright and found two splits at `x=299,644`, producing `auto_columns3/merged.psm6.txt`. This verifies the column detector and crop inversion path for light text on dark backgrounds.

## Search terms for older amplifier material

Older issues often do not use the abbreviation `УМЗЧ`. Search for these in the column OCR output:

- `усилитель НЧ`
- `усилители НЧ`
- `усилитель низкой частоты`
- `низкочастотный усилитель`
- `мощности`
- `стереофонический усилитель`
- `электроакустика`
- `звуковоспроизведение`
- `транзисторный усилитель`
