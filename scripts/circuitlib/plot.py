from __future__ import annotations

import math
from pathlib import Path

from .analysis import read_rows, scale_label, waveform_y_limit
from .common import write_text_lf
from .svg import base_svg, esc, line, text


class Plot:
    def __init__(self, width: int, height: int, title: str, x_label: str, y_label: str, x_log: bool = False):
        self.width = width
        self.height = height
        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.x_log = x_log
        self.left = 76
        self.right = 32
        self.top = 60
        self.bottom = 64

    def sx(self, x: float, xmin: float, xmax: float) -> float:
        if self.x_log:
            x, xmin, xmax = math.log10(x), math.log10(xmin), math.log10(xmax)
        return self.left + (x - xmin) / (xmax - xmin) * (self.width - self.left - self.right)

    def sy(self, y: float, ymin: float, ymax: float) -> float:
        return self.height - self.bottom - (y - ymin) / (ymax - ymin) * (self.height - self.top - self.bottom)

    def render(
        self,
        series: list[tuple[str, list[tuple[float, float]], str]],
        path: Path,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        x_ticks: list[float],
        y_ticks: list[float],
    ) -> None:
        body = [
            text(self.left, 36, self.title, 22, 700),
            f'<rect x="{self.left}" y="{self.top}" width="{self.width - self.left - self.right}" height="{self.height - self.top - self.bottom}" fill="#fff" stroke="#111" stroke-width="1.4"/>',
        ]
        for tick in x_ticks:
            x = self.sx(tick, xmin, xmax)
            body.append(line(x, self.top, x, self.height - self.bottom, "thin"))
            label = f"{tick:g}" if tick < 1000 else f"{tick/1000:g}k"
            body.append(text(x, self.height - self.bottom + 23, label, 12, 400, "middle"))
        for tick in y_ticks:
            y = self.sy(tick, ymin, ymax)
            body.append(line(self.left, y, self.width - self.right, y, "thin"))
            body.append(text(self.left - 10, y + 4, f"{tick:g}", 12, 400, "end"))
        for _, points, color in series:
            coords = " ".join(
                f"{self.sx(x, xmin, xmax):.2f},{self.sy(y, ymin, ymax):.2f}"
                for x, y in points
                if xmin <= x <= xmax and ymin <= y <= ymax
            )
            body.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')

        legend_w = max(190, max(len(name) for name, _, _ in series) * 7 + 74)
        legend_h = 18 + 26 * len(series)
        lx = self.width - self.right - legend_w - 16
        ly0 = 78
        body.append(
            f'<rect x="{lx - 12:g}" y="{ly0 - 16:g}" width="{legend_w:g}" height="{legend_h:g}" '
            'rx="4" ry="4" fill="#fff" fill-opacity="0.82" stroke="#111" stroke-width="1"/>'
        )
        for index, (name, _, color) in enumerate(series):
            ly = ly0 + 26 * index
            body.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 36}" y2="{ly}" stroke="{color}" stroke-width="3"/>')
            body.append(text(lx + 46, ly + 5, name, 13))
        body.append(text(self.width / 2, self.height - 18, self.x_label, 14, 400, "middle"))
        body.append(
            f'<text x="22" y="{self.height / 2:g}" font-family="Arial, Helvetica, sans-serif" font-size="14" '
            f'text-anchor="middle" fill="#111" transform="rotate(-90 22 {self.height / 2:g})">{esc(self.y_label)}</text>'
        )
        write_text_lf(path, base_svg(self.width, self.height, body))


def render_sine_plot(csv_path: Path, output_svg: Path, title: str) -> None:
    rows = read_rows(csv_path)
    t0 = rows[0][0]
    duration_ms = 4.0
    time_ms = [(row[0] - t0) * 1000.0 for row in rows]
    vin_raw_mv = [row[3] * 1000.0 for row in rows]
    amp_out = [row[7] for row in rows]
    load = [row[9] for row in rows]
    amp_out_mean = sum(amp_out) / len(amp_out)
    load_mean = sum(load) / len(load)
    amp_out_mv = [(value - amp_out_mean) * 1000.0 for value in amp_out]
    load_mv = [(value - load_mean) * 1000.0 for value in load]
    output_max_abs = max(max(abs(value) for value in load_mv), max(abs(value) for value in amp_out_mv))
    vin_max_abs = max(abs(value) for value in vin_raw_mv)
    vin_scale = output_max_abs / vin_max_abs if vin_max_abs > 0 else 1.0
    vin_mv = [value * vin_scale for value in vin_raw_mv]
    visible_values = [
        value
        for t, values in zip(time_ms, zip(load_mv, amp_out_mv, vin_mv))
        if 0 <= t <= duration_ms
        for value in values
    ]
    max_abs = max(abs(value) for value in visible_values)
    ymax = waveform_y_limit(max_abs)
    y_ticks = [-ymax, -ymax / 2.0, 0, ymax / 2.0, ymax]
    Plot(
        920,
        520,
        title,
        "Time after 40 ms settling, ms",
        "AC voltage, mV",
    ).render(
        [
            ("amp out AC", list(zip(time_ms, amp_out_mv)), "#13795b"),
            ("load output", list(zip(time_ms, load_mv)), "#1665d8"),
            (f"input x{scale_label(vin_scale)}", list(zip(time_ms, vin_mv)), "#b54708"),
        ],
        output_svg,
        0,
        duration_ms,
        -ymax,
        ymax,
        [0, 1, 2, 3, 4],
        y_ticks,
    )
