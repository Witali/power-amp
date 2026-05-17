# Radio.ru OCR Reference Sources, 1997-2000

This note lists online text/OCR references that can be used to calibrate local OCR of `archive.radio.ru` scans. Do not commit downloaded full article texts. Keep them under `.tmp/ocr_reference_texts/` and commit only links, commands and comparison metrics.

## Downloaded Calibration References

| Article | Local scan pages used | Reference URL | Notes |
|---|---|---|---|
| S. Ageev, "Сверхлинейный УМЗЧ с глубокой ООС" | `b.1999-10.014`, `b.1999-10.015`, `b.1999-10.016`, continuations | https://www.diagram.com.ua/list/sound/sound64.shtml | Long HTML article. Good for identifying Ageev pages and comparing OCR profile choices, but it may be a reprint/edited copy rather than a page-perfect transcript. |
| V. Levitsky, "УМЗЧ с индуктивной коррекцией" | `b.1999-10.017`, `b.1999-10.018` | https://www.diagram.com.ua/list/sound/sound65.shtml | Good clean reference for the article start. Useful for testing whether `psm 4` or `psm 6` better handles text plus schematic fragments. |
| M. Sapozhnikov, "УМЗЧ с однополярным источником питания" | `b.1999-06.015`, `b.1999-06.016` | https://www.martok.narod.ru/audio/usil2.htm | Old site with certificate-name mismatch; download with PowerShell 7 `-SkipCertificateCheck` if needed. |

## Comparison Commands

Download references into the ignored temporary folder:

```powershell
New-Item -ItemType Directory -Force -Path .tmp\ocr_reference_texts | Out-Null
Invoke-WebRequest -Uri "https://www.diagram.com.ua/list/sound/sound64.shtml" -OutFile .tmp\ocr_reference_texts\ageev_superlinear_diagram.html -UseBasicParsing
Invoke-WebRequest -Uri "https://www.diagram.com.ua/list/sound/sound65.shtml" -OutFile .tmp\ocr_reference_texts\levitsky_inductive_diagram.html -UseBasicParsing
Invoke-WebRequest -Uri "https://www.martok.narod.ru/audio/usil2.htm" -OutFile .tmp\ocr_reference_texts\sapozhnikov_single_supply_martok.html -UseBasicParsing -SkipCertificateCheck
```

Compare existing OCR candidates against those references:

```powershell
python scripts\compare_ocr_reference.py `
  --reference .tmp\ocr_reference_texts\ageev_superlinear_diagram.html `
  --reference .tmp\ocr_reference_texts\levitsky_inductive_diagram.html `
  --reference .tmp\ocr_reference_texts\sapozhnikov_single_supply_martok.html `
  --candidate-root .tmp\radio_ru_1997_2000\article_ocr_fixed2 `
  --glob "merged*.txt" `
  --out .tmp\ocr_reference_texts\comparison_1999_2000.tsv
```

## Calibration Result

I tested three representative pages with forced two-column OCR:

- `b.1999-06.015` against the Sapozhnikov reference.
- `b.1999-10.014` against the Ageev reference.
- `b.1999-10.017` against the Levitsky reference.

The best tested profile for these article pages was:

```text
Column split: fixed 2 columns
Tesseract PSM: 4
OCR profile: prose or technical
Text correction: usually neutral to slightly helpful
```

Observed top matches from `.tmp/ocr_reference_texts/tuning_trials.tsv`:

| Page | Reference | Best local variant | Candidate token match |
|---|---|---|---:|
| `b.1999-06.015` | Sapozhnikov single-supply UMZCH | `columns2/merged.prose.psm4.corrected.txt` | `0.539` |
| `b.1999-10.017` | Levitsky inductive correction UMZCH | `columns2/merged.prose.psm4.corrected.txt` | `0.540` |
| `b.1999-10.014` | Ageev superlinear UMZCH | `columns2/merged.prose.psm4.txt` | `0.539` |

`psm 6` produced more tokens on some pages, but matched the references worse. For mixed article pages with normal prose plus schematic fragments, prefer `psm 4` and keep `psm 6` as a fallback for uniform contents columns or simple article-list pages.

## Interpretation Limits

- Online reprints are not always page-perfect copies; they may omit captions, tables or figure text.
- A single scan page is compared against a full article, so absolute scores around `0.5` can still be a good match.
- The metric is for profile selection and article identification, not for proving that every OCR word is correct.
- Keep using `LongLines = 0`, spellcheck reports and manual page inspection alongside reference matching.
