# Layout Frequency Calibration

Калибровка построена по исходным сканам страниц, которые проверялись через PNG-превью в `study/layout_detection_marked_pages/`.
Цветные рамки превью не используются для измерений, чтобы не вносить искусственные частоты.

- Pages: 15
- Calibrated tiles: 30085
- Tile classifier accuracy against reviewed blocks: 0.69955

## Constants

- `DEFAULT_TILE_SIZE` = `32`
- `DEFAULT_STRIDE` = `32`
- `LUMA_HIST_BINS` = `16`
- `SATURATION_HIST_BINS` = `8`
- `HUE_HIST_BINS` = `12`
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
- `TEXT_MIN_LUMA_BIMODAL` = `0.38`
- `TEXT_MAX_LUMA_MID_FRACTION` = `0.42`
- `IMAGE_MIN_LUMA_ENTROPY` = `0.52`
- `IMAGE_MIN_LUMA_MID_FRACTION` = `0.32`
- `SCHEMATIC_MAX_DARK_LIGHT_RATIO` = `0.24`
- `TEXT_MIN_DARK_LIGHT_RATIO` = `0.03`
- `TEXT_MAX_DARK_LIGHT_RATIO` = `0.34`

## Confusion Matrix

- `diagram`: {'text': 21, 'schematic/circuit': 3, 'background': 19}
- `image`: {'image': 32, 'text': 246, 'schematic/circuit': 885, 'background': 27, 'table': 2}
- `schematic/circuit`: {'schematic/circuit': 1468, 'table': 368, 'text': 3157, 'background': 1418, 'other': 3, 'image': 121}
- `table`: {'background': 31, 'text': 74, 'schematic/circuit': 21, 'table': 3}
- `text`: {'text': 19543, 'schematic/circuit': 773, 'image': 221, 'other': 2, 'background': 1481, 'table': 166}

## Feature Ranges

### diagram

- tiles: 43, pages: 2, blocks: 2

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.00000 | 0.06641 | 0.09375 | 0.05096 | 0.05477 |
| `gray_std` | 0.00996 | 0.34560 | 0.47435 | 0.23909 | 0.21299 |
| `saturation_p80` | 0.28274 | 0.30588 | 0.32941 | 0.30701 | 0.01714 |
| `saturation_high_fraction` | 0.45879 | 0.86621 | 1.00000 | 0.86140 | 0.19176 |
| `color_pixel_fraction` | 1.00000 | 1.00000 | 1.00000 | 1.00000 | 0.00000 |
| `luma_dark_fraction` | 0.00000 | 0.00000 | 0.01983 | 0.00334 | 0.00859 |
| `luma_light_fraction` | 0.87608 | 0.90918 | 1.00000 | 0.92467 | 0.15112 |
| `luma_mid_fraction` | 0.00000 | 0.07812 | 0.11699 | 0.07199 | 0.15065 |
| `luma_dark_light_ratio` | 0.00000 | 0.00000 | 0.02200 | 0.00374 | 0.00968 |
| `luma_light_dark_ratio` | 32.23524 | 100.00000 | 100.00000 | 92.09712 | 23.04533 |
| `luma_bimodal_score` | 0.00000 | 0.00000 | 0.01826 | 0.00306 | 0.00793 |
| `luma_hist_entropy` | -0.00000 | 0.15730 | 0.30706 | 0.13735 | 0.12096 |
| `saturation_hist_entropy` | -0.00000 | 0.30771 | 0.39236 | 0.19398 | 0.17858 |
| `hue_hist_entropy` | -0.00000 | -0.00000 | 0.26784 | 0.04562 | 0.08493 |
| `row_period_score` | 0.67722 | 0.97587 | 0.99457 | 0.92966 | 0.09555 |
| `column_period_score` | 0.13460 | 0.32566 | 0.76842 | 0.36371 | 0.20349 |
| `row_entropy` | 0.18790 | 0.34973 | 0.74141 | 0.40413 | 0.16633 |
| `column_entropy` | 0.21553 | 0.41796 | 0.62034 | 0.42640 | 0.15286 |
| `hline_density` | 0.00000 | 0.00000 | 0.24922 | 0.03815 | 0.11330 |
| `vline_density` | 0.00000 | 0.00000 | 0.75000 | 0.31686 | 0.33817 |
| `line_balance` | 0.00000 | 0.00000 | 0.00000 | 0.02047 | 0.09314 |
| `row_dominant_period` | 0.00000 | 0.00000 | 32.00000 | 9.30233 | 13.90254 |
| `column_dominant_period` | 0.00000 | 32.00000 | 32.00000 | 16.74419 | 15.79534 |
| `gray_row_dominant_period` | 16.00000 | 32.00000 | 32.00000 | 28.15504 | 7.02721 |
| `gray_column_dominant_period` | 16.00000 | 32.00000 | 32.00000 | 30.13953 | 5.12895 |

### image

- tiles: 1192, pages: 9, blocks: 11

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.06250 | 0.79346 | 1.00000 | 0.66279 | 0.33025 |
| `gray_std` | 0.02380 | 0.43689 | 0.94600 | 0.45211 | 0.28506 |
| `saturation_p80` | 0.00000 | 0.36863 | 0.86667 | 0.40295 | 0.26403 |
| `saturation_high_fraction` | 0.00000 | 0.54541 | 1.00000 | 0.53640 | 0.37426 |
| `color_pixel_fraction` | 0.00000 | 0.84619 | 1.00000 | 0.68707 | 0.35850 |
| `luma_dark_fraction` | 0.00000 | 0.00000 | 0.57393 | 0.09302 | 0.18543 |
| `luma_light_fraction` | 0.00000 | 0.17383 | 0.91450 | 0.31536 | 0.32179 |
| `luma_mid_fraction` | 0.03765 | 0.67773 | 1.00000 | 0.59162 | 0.35288 |
| `luma_dark_light_ratio` | 0.00000 | 0.00000 | 10.00000 | 1.35808 | 3.19429 |
| `luma_light_dark_ratio` | 0.00000 | 30.60427 | 100.00000 | 50.56814 | 48.22585 |
| `luma_bimodal_score` | 0.00000 | 0.00000 | 0.22555 | 0.03233 | 0.07924 |
| `luma_hist_entropy` | 0.00627 | 0.42040 | 0.74008 | 0.40837 | 0.21781 |
| `saturation_hist_entropy` | -0.00000 | 0.44721 | 0.76604 | 0.41120 | 0.23045 |
| `hue_hist_entropy` | -0.00000 | 0.04489 | 0.42449 | 0.12944 | 0.16317 |
| `row_period_score` | 0.65524 | 0.95738 | 0.99745 | 0.90965 | 0.14470 |
| `column_period_score` | 0.05814 | 0.40089 | 0.91898 | 0.43457 | 0.27084 |
| `row_entropy` | 0.18090 | 0.42450 | 0.66999 | 0.42375 | 0.14622 |
| `column_entropy` | 0.10631 | 0.35978 | 0.65518 | 0.36523 | 0.16453 |
| `hline_density` | 0.00000 | 1.00000 | 1.00000 | 0.76010 | 0.40351 |
| `vline_density` | 0.00000 | 1.00000 | 1.00000 | 0.85798 | 0.32759 |
| `line_balance` | 0.00000 | 0.93243 | 1.00000 | 0.67091 | 0.41071 |
| `row_dominant_period` | 0.00000 | 16.00000 | 32.00000 | 17.26334 | 13.46561 |
| `column_dominant_period` | 0.00000 | 32.00000 | 32.00000 | 22.58702 | 13.28357 |
| `gray_row_dominant_period` | 8.00000 | 32.00000 | 32.00000 | 25.14989 | 9.17720 |
| `gray_column_dominant_period` | 8.00000 | 32.00000 | 32.00000 | 26.97942 | 8.86701 |

### schematic/circuit

- tiles: 6535, pages: 10, blocks: 11

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.00000 | 0.10938 | 0.30762 | 0.12443 | 0.10255 |
| `gray_std` | 0.00658 | 0.56011 | 0.86293 | 0.48866 | 0.28973 |
| `saturation_p80` | 0.00000 | 0.00000 | 0.31373 | 0.05972 | 0.10941 |
| `saturation_high_fraction` | 0.00000 | 0.00000 | 0.86748 | 0.09476 | 0.25067 |
| `color_pixel_fraction` | 0.00000 | 0.00000 | 1.00000 | 0.18891 | 0.38295 |
| `luma_dark_fraction` | 0.00000 | 0.03418 | 0.16504 | 0.05021 | 0.05679 |
| `luma_light_fraction` | 0.66016 | 0.87500 | 1.00000 | 0.86001 | 0.11352 |
| `luma_mid_fraction` | 0.00000 | 0.08594 | 0.21582 | 0.08979 | 0.07233 |
| `luma_dark_light_ratio` | 0.00000 | 0.04082 | 0.23905 | 0.06849 | 0.09118 |
| `luma_light_dark_ratio` | 4.18328 | 24.50000 | 100.00000 | 47.33039 | 41.32754 |
| `luma_bimodal_score` | 0.00000 | 0.03062 | 0.14053 | 0.04348 | 0.04815 |
| `luma_hist_entropy` | -0.00000 | 0.35449 | 0.70528 | 0.35383 | 0.21534 |
| `saturation_hist_entropy` | -0.00000 | -0.00000 | 0.44020 | 0.06669 | 0.14503 |
| `hue_hist_entropy` | -0.00000 | 0.00000 | 0.21973 | 0.02476 | 0.07097 |
| `row_period_score` | 0.57492 | 0.90410 | 0.99518 | 0.84952 | 0.15581 |
| `column_period_score` | 0.08712 | 0.65439 | 0.94158 | 0.59061 | 0.27484 |
| `row_entropy` | 0.11482 | 0.50875 | 0.78704 | 0.49958 | 0.20615 |
| `column_entropy` | 0.14985 | 0.56825 | 0.77437 | 0.52918 | 0.19557 |
| `hline_density` | 0.00000 | 0.00000 | 0.85938 | 0.22816 | 0.31758 |
| `vline_density` | 0.00000 | 0.00000 | 0.95312 | 0.24386 | 0.33467 |
| `line_balance` | 0.00000 | 0.00000 | 0.80966 | 0.12269 | 0.26448 |
| `row_dominant_period` | 0.00000 | 16.00000 | 32.00000 | 19.31952 | 13.60243 |
| `column_dominant_period` | 0.00000 | 16.00000 | 32.00000 | 16.63900 | 13.33788 |
| `gray_row_dominant_period` | 8.00000 | 32.00000 | 32.00000 | 25.51262 | 9.13326 |
| `gray_column_dominant_period` | 6.40000 | 32.00000 | 32.00000 | 22.88109 | 10.45562 |

### table

- tiles: 129, pages: 3, blocks: 4

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.00000 | 0.15137 | 0.51172 | 0.15972 | 0.14350 |
| `gray_std` | 0.00000 | 0.66899 | 0.90013 | 0.51489 | 0.31425 |
| `saturation_p80` | 0.00000 | 0.00000 | 0.32627 | 0.05677 | 0.11341 |
| `saturation_high_fraction` | 0.00000 | 0.00000 | 0.27403 | 0.04850 | 0.10639 |
| `color_pixel_fraction` | 0.00000 | 0.00000 | 0.52910 | 0.09156 | 0.16872 |
| `luma_dark_fraction` | 0.00000 | 0.01562 | 0.17207 | 0.04872 | 0.06026 |
| `luma_light_fraction` | 0.46875 | 0.84375 | 1.00000 | 0.82913 | 0.14842 |
| `luma_mid_fraction` | 0.00000 | 0.09375 | 0.38340 | 0.12215 | 0.12932 |
| `luma_dark_light_ratio` | 0.00000 | 0.01816 | 0.29560 | 0.06895 | 0.09599 |
| `luma_light_dark_ratio` | 3.38451 | 55.07692 | 100.00000 | 55.60672 | 44.15198 |
| `luma_bimodal_score` | 0.00000 | 0.01239 | 0.13446 | 0.04193 | 0.05178 |
| `luma_hist_entropy` | -0.00000 | 0.25808 | 0.61828 | 0.26654 | 0.19797 |
| `saturation_hist_entropy` | -0.00000 | -0.00000 | 0.57790 | 0.11490 | 0.19627 |
| `hue_hist_entropy` | 0.00000 | 0.00000 | 0.27817 | 0.05984 | 0.10799 |
| `row_period_score` | 0.00000 | 0.90735 | 0.99204 | 0.84343 | 0.23754 |
| `column_period_score` | 0.00000 | 0.41935 | 0.95009 | 0.47273 | 0.29648 |
| `row_entropy` | 0.00000 | 0.42003 | 0.74638 | 0.43778 | 0.22677 |
| `column_entropy` | 0.00000 | 0.46077 | 0.72955 | 0.44532 | 0.19698 |
| `hline_density` | 0.00000 | 0.75000 | 1.00000 | 0.56680 | 0.46173 |
| `vline_density` | 0.00000 | 0.00000 | 1.00000 | 0.17145 | 0.35795 |
| `line_balance` | 0.00000 | 0.00000 | 0.94141 | 0.11779 | 0.30027 |
| `row_dominant_period` | 0.00000 | 16.00000 | 32.00000 | 19.01809 | 12.80560 |
| `column_dominant_period` | 0.00000 | 0.00000 | 32.00000 | 10.04238 | 13.01967 |
| `gray_row_dominant_period` | 0.00000 | 32.00000 | 32.00000 | 24.76486 | 9.80046 |
| `gray_column_dominant_period` | 0.00000 | 32.00000 | 32.00000 | 24.50853 | 11.11846 |

### text

- tiles: 22186, pages: 15, blocks: 135

| Feature | p05 | median | p95 | mean | stdev |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ink_density` | 0.00000 | 0.23633 | 0.36816 | 0.21916 | 0.10804 |
| `gray_std` | 0.01101 | 0.73188 | 0.87170 | 0.65819 | 0.22697 |
| `saturation_p80` | 0.00000 | 0.00000 | 0.27451 | 0.05049 | 0.10069 |
| `saturation_high_fraction` | 0.00000 | 0.00000 | 0.21973 | 0.03686 | 0.08726 |
| `color_pixel_fraction` | 0.00000 | 0.00000 | 1.00000 | 0.17054 | 0.34298 |
| `luma_dark_fraction` | 0.00000 | 0.06152 | 0.17871 | 0.07290 | 0.06427 |
| `luma_light_fraction` | 0.59277 | 0.73926 | 1.00000 | 0.75634 | 0.12102 |
| `luma_mid_fraction` | 0.00000 | 0.17969 | 0.30273 | 0.17076 | 0.09077 |
| `luma_dark_light_ratio` | 0.00000 | 0.08357 | 0.28759 | 0.11164 | 0.18210 |
| `luma_light_dark_ratio` | 3.47233 | 11.95651 | 100.00000 | 29.37936 | 34.62693 |
| `luma_bimodal_score` | 0.00000 | 0.04967 | 0.14602 | 0.05904 | 0.05313 |
| `luma_hist_entropy` | -0.00000 | 0.56469 | 0.73399 | 0.50254 | 0.20622 |
| `saturation_hist_entropy` | -0.00000 | -0.00000 | 0.53080 | 0.09337 | 0.18748 |
| `hue_hist_entropy` | -0.00000 | 0.00000 | 0.25420 | 0.02931 | 0.07821 |
| `row_period_score` | 0.71414 | 0.89916 | 0.97958 | 0.87715 | 0.11446 |
| `column_period_score` | 0.20034 | 0.82037 | 0.95623 | 0.73724 | 0.22983 |
| `row_entropy` | 0.21036 | 0.48754 | 0.68522 | 0.48045 | 0.13533 |
| `column_entropy` | 0.27258 | 0.65139 | 0.78170 | 0.61224 | 0.15615 |
| `hline_density` | 0.00000 | 0.00000 | 0.31250 | 0.04601 | 0.16162 |
| `vline_density` | 0.00000 | 0.00000 | 0.55469 | 0.07591 | 0.20305 |
| `line_balance` | 0.00000 | 0.00000 | 0.00000 | 0.02579 | 0.12834 |
| `row_dominant_period` | 0.00000 | 32.00000 | 32.00000 | 25.90963 | 9.99612 |
| `column_dominant_period` | 0.00000 | 6.40000 | 32.00000 | 12.55423 | 10.87590 |
| `gray_row_dominant_period` | 16.00000 | 32.00000 | 32.00000 | 27.94035 | 7.48862 |
| `gray_column_dominant_period` | 5.33333 | 8.00000 | 32.00000 | 14.25686 | 11.23548 |
