# Layout Detection Test Pages

This file lists useful `archive.radio.ru` pages for checking page-block detection on mixed magazine layouts. The current local preview overlays are generated under `.tmp/layout_candidate_layouts/`; the source scans can be re-downloaded with `scripts/download_radio_ru_pages.ps1` and are cached by issue under `.tmp/archive_radio_ru/<year>/<month>/` until they are explicitly removed.

## Best mixed pages

| Page | Source scan | Why it is useful |
| --- | --- | --- |
| `2000-11-013` | https://archive.radio.ru/web/img/2000/b.2000-11.013.jpg | Strong mixed test: large circuit fragments, a photo/advert-like image block, tables, text columns, and vertical page-margin labels. Current preview shows `image`, `schematic`, `table`, and `text`. |
| `2000-02-036` | https://archive.radio.ru/web/img/2000/b.2000-02.036.jpg | Dense switched-mode power-supply article page with several schematic fragments, tables, and narrow labels. Good stress test for not merging all drawings into one huge block. |
| `1999-10-017` | https://archive.radio.ru/web/img/1999/b.1999-10.017.jpg | UMZCH article start with big title text, two schematics, normal prose columns, and right-side vertical margin material. Good for display-text vs schematic separation. |
| `2000-10-014` | https://archive.radio.ru/web/img/2000/b.2000-10.014.jpg | Text-heavy amplifier article with a large circuit near the bottom. Useful for checking whether a schematic embedded below text is separated cleanly. |
| `2000-11-011` | https://archive.radio.ru/web/img/2000/b.2000-11.011.jpg | Practical power-amplifier article with title, a drawing/antenna-like illustration, text columns, and margin labels. Useful for image/diagram distinction. |

## Secondary pages

| Page | Source scan | Why it is useful |
| --- | --- | --- |
| `1997-04-018` | https://archive.radio.ru/web/img/1997/b.1997-04.018.jpg | Compact transistor amplifier article; current detector sees a small diagram/table-like area plus text. |
| `1999-10-018` | https://archive.radio.ru/web/img/1999/b.1999-10.018.jpg | Continuation page with a large schematic block and mixed advertisements. |
| `2000-02-037` | https://archive.radio.ru/web/img/2000/b.2000-02.037.jpg | Continuation of the SMPS article; useful for narrow technical drawings and small figure captions. |
| `2000-09-011` | https://archive.radio.ru/web/img/2000/b.2000-09.011.jpg | Bridge UMZCH with BSIT article start; mostly text, but contains a figure/table region. |
| `2000-10-015` | https://archive.radio.ru/web/img/2000/b.2000-10.015.jpg | Continuation page with a large lower schematic and vertical margin labels. |

## Local check command

```powershell
pwsh -File scripts/download_radio_ru_pages.ps1 `
  -Pages 2000-11-013,2000-02-036,1999-10-017,2000-10-014,2000-11-011

Get-ChildItem -LiteralPath .tmp\archive_radio_ru -Recurse -Filter *.jpg |
  Where-Object { $_.Name -in @(
    "b.2000-11.013.jpg",
    "b.2000-02.036.jpg",
    "b.1999-10.017.jpg",
    "b.2000-10.014.jpg",
    "b.2000-11.011.jpg"
  ) } |
  ForEach-Object {
    python scripts\detect_page_layout.py `
      --image $_.FullName `
      --out-dir .tmp\layout_candidate_layouts `
      --preview-width 900
  }
```
