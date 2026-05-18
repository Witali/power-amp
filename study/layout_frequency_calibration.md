# Layout Frequency Calibration

Калибровка построена по исходным сканам страниц, которые проверялись через PNG-превью в `study/layout_detection_marked_pages/`.
Цветные рамки превью не используются для измерений, чтобы не вносить искусственные частоты.

- Pages: 15
- Calibrated tiles: 2920
- Tile classifier accuracy against reviewed blocks: 0.84144

## Constants

- `TEXT_ROW_PERIOD_BAND` = `(8.0, 44.0)`
- `TEXT_COLUMN_PERIOD_BAND` = `(4.0, 28.0)`
- `BACKGROUND_MAX_INK` = `0.01`
- `BACKGROUND_MAX_GRAY_STD` = `0.08`
- `STRONG_TEXT_ROW_PERIOD` = `0.68`
- `STRONG_TEXT_ROW_ENTROPY_MAX` = `0.66`
- `LINE_ART_MAX_INK` = `0.26`
- `LINE_ART_MIN_ENTROPY` = `0.56`
- `LINE_ART_MIN_LINE_DENSITY` = `0.045`
- `LINE_ART_MIN_BALANCE` = `0.12`
- `IMAGE_STRONG_SATURATION` = `0.24`

## Confusion Matrix

- `image`: {'image': 33, 'schematic/circuit': 16}
- `schematic/circuit`: {'schematic/circuit': 470, 'text': 118, 'image': 75, 'other': 6, 'table': 45, 'background': 1}
- `text`: {'text': 1954, 'image': 58, 'schematic/circuit': 128, 'background': 8, 'other': 2, 'table': 6}

## Feature Ranges

### image

- tiles: 49, pages: 5, blocks: 6

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.20432 | 0.51554 | 0.82678 | 0.50773 | 0.20529 |
| `gray_std` | 0.57006 | 0.74639 | 1.00000 | 0.78180 | 0.13560 |
| `saturation_p80` | 0.07059 | 0.38431 | 0.78274 | 0.43377 | 0.21041 |
| `row_period_score` | 0.03821 | 0.23456 | 0.85993 | 0.27374 | 0.21231 |
| `column_period_score` | 0.03409 | 0.22059 | 0.85187 | 0.36064 | 0.30339 |
| `row_entropy` | 0.17292 | 0.42687 | 0.52266 | 0.38690 | 0.11362 |
| `column_entropy` | 0.16130 | 0.45585 | 0.76247 | 0.45155 | 0.19429 |
| `hline_density` | 0.00000 | 1.00000 | 1.00000 | 0.79808 | 0.38101 |
| `vline_density` | 0.00000 | 1.00000 | 1.00000 | 0.78351 | 0.39581 |
| `line_balance` | 0.00000 | 0.77980 | 0.99215 | 0.65657 | 0.35481 |
| `row_dominant_period` | 27.42857 | 64.00000 | 64.00000 | 54.91467 | 12.91283 |
| `column_dominant_period` | 6.07742 | 48.00000 | 64.00000 | 43.46392 | 22.67230 |
| `gray_row_dominant_period` | 24.00000 | 48.00000 | 64.00000 | 46.33469 | 15.66183 |
| `gray_column_dominant_period` | 5.78824 | 48.00000 | 64.00000 | 42.59715 | 23.90862 |

### schematic/circuit

- tiles: 715, pages: 10, blocks: 10

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.04640 | 0.12874 | 0.20506 | 0.12629 | 0.04878 |
| `gray_std` | 0.36847 | 0.60201 | 0.77531 | 0.58792 | 0.12631 |
| `saturation_p80` | 0.00000 | 0.00000 | 0.31098 | 0.05745 | 0.10601 |
| `row_period_score` | 0.34372 | 0.55605 | 0.72694 | 0.54842 | 0.12054 |
| `column_period_score` | 0.30759 | 0.70481 | 0.87597 | 0.66844 | 0.17381 |
| `row_entropy` | 0.53042 | 0.73947 | 0.82412 | 0.71520 | 0.09864 |
| `column_entropy` | 0.50790 | 0.76000 | 0.83054 | 0.73265 | 0.10329 |
| `hline_density` | 0.00000 | 0.11111 | 0.31792 | 0.13318 | 0.10483 |
| `vline_density` | 0.00000 | 0.11806 | 0.31105 | 0.13377 | 0.10206 |
| `line_balance` | 0.00000 | 0.39769 | 0.92459 | 0.41349 | 0.30678 |
| `row_dominant_period` | 10.66667 | 24.00000 | 64.00000 | 32.01387 | 17.40451 |
| `column_dominant_period` | 8.00000 | 32.00000 | 64.00000 | 32.59724 | 18.55333 |
| `gray_row_dominant_period` | 9.46286 | 24.00000 | 64.00000 | 32.10876 | 18.02977 |
| `gray_column_dominant_period` | 6.62069 | 27.42857 | 64.00000 | 30.75423 | 19.34127 |

### text

- tiles: 2156, pages: 15, blocks: 78

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.09407 | 0.22377 | 0.28719 | 0.21409 | 0.06227 |
| `gray_std` | 0.49679 | 0.72484 | 0.80538 | 0.69865 | 0.10850 |
| `saturation_p80` | 0.00000 | 0.00000 | 0.25980 | 0.05456 | 0.09895 |
| `row_period_score` | 0.48230 | 0.83088 | 0.87864 | 0.76919 | 0.13995 |
| `column_period_score` | 0.23688 | 0.67150 | 0.87269 | 0.61268 | 0.21170 |
| `row_entropy` | 0.33327 | 0.42220 | 0.71548 | 0.45479 | 0.11425 |
| `column_entropy` | 0.49562 | 0.72899 | 0.81272 | 0.69358 | 0.11168 |
| `hline_density` | 0.00000 | 0.00000 | 0.14025 | 0.02845 | 0.11813 |
| `vline_density` | 0.00000 | 0.00000 | 0.16461 | 0.03027 | 0.12487 |
| `line_balance` | 0.00000 | 0.00000 | 0.41130 | 0.04343 | 0.16621 |
| `row_dominant_period` | 19.20000 | 21.33333 | 38.40000 | 22.94070 | 8.72217 |
| `column_dominant_period` | 5.33333 | 10.10526 | 64.00000 | 26.35783 | 24.31255 |
| `gray_row_dominant_period` | 19.20000 | 21.33333 | 48.00000 | 23.35958 | 9.16788 |
| `gray_column_dominant_period` | 5.18919 | 8.93507 | 64.00000 | 26.71346 | 24.55619 |
