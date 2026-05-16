# Plot Drawing Rules

These rules are used for generated simulation plots and should be reused for new circuit result scripts.

## Scaling

- Choose plotted signal scale multipliers from the 1-2-5 series: `1`, `2`, `5`, `10`, `20`, `50`, and so on.
- Use the nearest 1-2-5 multiplier when a small reference signal is overlaid on a larger signal, for example `input x2` or `input x5`.
- Choose automatic Y-axis limits from the same 1-2-5 series after applying the target occupancy margin.
- For time-domain waveform plots, target about 70% vertical occupancy for the largest visible signal before rounding the limit to the 1-2-5 series.
- Do not force large fixed units when the data is small. Switch units so the curve is readable, for example from `mW` to `uW`.

## Layout

- Keep plot dimensions stable across regenerated runs unless there is a specific reason to change them.
- Use a white background and high-contrast axes.
- Use a white semi-transparent legend background with a visible border so traces remain readable under the legend.
- Keep legends inside the plot area only when they do not hide important data; otherwise move them or adjust the plot.
- Preserve generated SVG as the editable source and PNG as the convenient preview artifact.

## Labels

- Plot titles should include the variant name, measured quantity, and important test condition such as input level or load.
- Axis labels must include units.
- If a trace is scaled for readability, show the multiplier in the legend.
- Use consistent names for repeated traces: `load output`, `amp out AC`, `input xN`, `gain`, `THD`, and `Pout`.

# Правила отрисовки графиков

Эти правила применяются к сгенерированным графикам моделирования и должны использоваться в новых скриптах результатов.

## Масштабирование

- Коэффициенты масштабирования сигналов выбирать из ряда `1-2-5`: `1`, `2`, `5`, `10`, `20`, `50` и далее.
- Для наложения малого опорного сигнала на больший сигнал использовать ближайший коэффициент из ряда `1-2-5`, например `input x2` или `input x5`.
- Автоматические пределы оси Y выбирать из этого же ряда после учета запаса по высоте.
- Для временных диаграмм стремиться к заполнению примерно 70% высоты крупнейшим видимым сигналом до округления предела к ряду `1-2-5`.
- Не фиксировать слишком крупные единицы измерения для малых данных. Единицы нужно переключать так, чтобы кривая была читаемой, например с `mW` на `uW`.

## Компоновка

- Размеры графиков должны оставаться стабильными между повторными генерациями, если нет явной причины их менять.
- Фон графика белый, оси контрастные.
- Легенда должна иметь белый полупрозрачный фон и видимую рамку, чтобы линии под ней не мешали чтению.
- Легенду можно держать внутри поля графика только если она не закрывает важные данные; иначе ее нужно переносить или менять компоновку.
- SVG хранится как редактируемый источник, PNG как удобный файл для просмотра.

## Подписи

- Заголовок должен содержать вариант схемы, измеряемую величину и важное условие расчета, например входной уровень или нагрузку.
- Подписи осей должны содержать единицы измерения.
- Если сигнал масштабирован для читаемости, коэффициент должен быть указан в легенде.
- Для повторяющихся кривых использовать единые имена: `load output`, `amp out AC`, `input xN`, `gain`, `THD`, `Pout`.
