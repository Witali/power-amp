from __future__ import annotations

import math


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text(x: float, y: float, body: object, size: int = 14, weight: int = 400, anchor: str = "start") -> str:
    return (
        f'<text x="{x:g}" y="{y:g}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="#111">{esc(body)}</text>'
    )


def line(x1: float, y1: float, x2: float, y2: float, klass: str = "wire") -> str:
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" class="{klass}"/>'


def poly(points: list[tuple[float, float]], klass: str = "wire", fill: str = "none") -> str:
    pts = " ".join(f"{x:g},{y:g}" for x, y in points)
    return f'<polyline points="{pts}" class="{klass}" fill="{fill}"/>'


def circle(cx: float, cy: float, r: float, klass: str = "wire") -> str:
    return f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" class="{klass}"/>'


def rect(x: float, y: float, width: float, height: float, klass: str = "wire") -> str:
    return f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" class="{klass}"/>'


def base_svg(width: int, height: int, body: list[str]) -> str:
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<defs>",
            "<style>",
            ".wire{stroke:#111;stroke-width:2.6;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".thin{stroke:#a7b0bd;stroke-width:1.2;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".axis{stroke:#111;stroke-width:1.4;fill:none}",
            ".blue{stroke:#1665d8;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".green{stroke:#13795b;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".orange{stroke:#b54708;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}",
            ".node{fill:#111;stroke:none}",
            "</style>",
            "</defs>",
            '<rect width="100%" height="100%" fill="#fff"/>',
            *body,
            "</svg>",
        ]
    ) + "\n"


def resistor_h(x1: float, y: float, x2: float, label: str) -> list[str]:
    w = x2 - x1
    body_w = min(76.0, max(48.0, w * 0.56))
    left = x1 + (w - body_w) / 2.0
    right = left + body_w
    body_h = 28.0
    return [
        line(x1, y, left, y),
        rect(left, y - body_h / 2.0, body_w, body_h),
        line(right, y, x2, y),
        text((x1 + x2) / 2, y - 26, label, 14, 700, "middle"),
    ]


def resistor_v(x: float, y1: float, y2: float, label: str, side: str = "right") -> list[str]:
    h = y2 - y1
    body_h = min(76.0, max(36.0, h * 0.62))
    top = y1 + (h - body_h) / 2.0
    bottom = top + body_h
    body_w = 28.0
    dx = 24 if side == "right" else -24
    anchor = "start" if side == "right" else "end"
    return [
        line(x, y1, x, top),
        rect(x - body_w / 2.0, top, body_w, body_h),
        line(x, bottom, x, y2),
        text(x + dx, (y1 + y2) / 2 + 5, label, 14, 700, anchor),
    ]


def capacitor_v(x: float, y1: float, y2: float, label: str, side: str = "right", positive: str | None = None) -> list[str]:
    mid = (y1 + y2) / 2
    dx = 28 if side == "right" else -28
    anchor = "start" if side == "right" else "end"
    parts = [
        line(x, y1, x, mid - 14),
        line(x - 24, mid - 14, x + 24, mid - 14),
        line(x - 24, mid + 14, x + 24, mid + 14),
        line(x, mid + 14, x, y2),
        text(x + dx, mid + 5, label, 14, 700, anchor),
    ]
    if positive == "top":
        parts.append(text(x - 34, mid - 30, "+", 18, 700, "middle"))
    elif positive == "bottom":
        parts.append(text(x - 34, mid + 40, "+", 18, 700, "middle"))
    return parts


def capacitor_h(x1: float, y: float, x2: float, label: str, positive: str | None = None) -> list[str]:
    mid = (x1 + x2) / 2
    parts = [
        line(x1, y, mid - 14, y),
        line(mid - 14, y - 24, mid - 14, y + 24),
        line(mid + 14, y - 24, mid + 14, y + 24),
        line(mid + 14, y, x2, y),
        text(mid, y - 34, label, 14, 700, "middle"),
    ]
    if positive == "left":
        parts.append(text(mid - 30, y - 17, "+", 18, 700, "middle"))
    elif positive == "right":
        parts.append(text(mid + 30, y - 17, "+", 18, 700, "middle"))
    return parts


def diode_v(x: float, y1: float, y2: float, label: str) -> list[str]:
    mid = (y1 + y2) / 2
    return [
        line(x, y1, x, mid - 24),
        poly([(x - 22, mid - 24), (x + 22, mid - 24), (x, mid + 8), (x - 22, mid - 24)], "wire"),
        line(x - 22, mid + 14, x + 22, mid + 14),
        line(x, mid + 14, x, y2),
        text(x + 34, mid + 4, label, 14, 700),
    ]


def ground(x: float, y: float) -> list[str]:
    return [
        line(x, y, x, y + 14),
        line(x - 26, y + 14, x + 26, y + 14),
        line(x - 17, y + 27, x + 17, y + 27),
        line(x - 8, y + 40, x + 8, y + 40),
    ]


def speaker_v(x: float, y1: float, y2: float, label: str) -> list[str]:
    top = y1 + 34
    bottom = y1 + 110
    return [
        line(x, y1, x, top),
        rect(x - 18, top, 36, bottom - top),
        poly([(x + 18, top + 8), (x + 76, top - 16), (x + 76, bottom + 16), (x + 18, bottom - 8)]),
        line(x, bottom, x, y2),
        text(x + 40, bottom + 46, label, 14, 700, "middle"),
    ]


def arrowhead(
    start: tuple[float, float],
    end: tuple[float, float],
    direction: str,
    fraction: float,
    length: float = 15,
    half_width: float = 5.5,
) -> str:
    sx, sy = start
    ex, ey = end
    vx = ex - sx
    vy = ey - sy
    mag = math.hypot(vx, vy)
    ux = vx / mag
    uy = vy / mag
    nx = -uy
    ny = ux
    tip = (sx + vx * fraction, sy + vy * fraction)
    if direction == "out":
        base = (tip[0] - ux * length, tip[1] - uy * length)
    else:
        base = (tip[0] + ux * length, tip[1] + uy * length)
    p1 = (base[0] + nx * half_width, base[1] + ny * half_width)
    p2 = (base[0] - nx * half_width, base[1] - ny * half_width)
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in [tip, p1, p2])
    return f'<polygon points="{pts}" fill="#111" stroke="none"/>'


def npn(cx: float, cy: float, label: str) -> list[str]:
    base_top = (cx - 16, cy - 24)
    base_bottom = (cx - 16, cy + 24)
    top = (cx + 30, cy - 45)
    bottom = (cx + 30, cy + 45)
    return [
        circle(cx, cy, 54),
        line(cx - 54, cy, cx - 16, cy),
        line(cx - 16, cy - 34, cx - 16, cy + 34),
        line(base_top[0], base_top[1], top[0], top[1]),
        line(base_bottom[0], base_bottom[1], bottom[0], bottom[1]),
        arrowhead(base_bottom, bottom, "out", 0.70),
        text(cx - 44, cy + 82, label, 14, 700, "middle"),
    ]


def pnp(cx: float, cy: float, label: str) -> list[str]:
    base_top = (cx - 16, cy - 24)
    base_bottom = (cx - 16, cy + 24)
    top = (cx + 30, cy - 45)
    bottom = (cx + 30, cy + 45)
    return [
        circle(cx, cy, 54),
        line(cx - 54, cy, cx - 16, cy),
        line(cx - 16, cy - 34, cx - 16, cy + 34),
        line(base_top[0], base_top[1], top[0], top[1]),
        line(base_bottom[0], base_bottom[1], bottom[0], bottom[1]),
        arrowhead(base_top, top, "in", 0.42),
        text(cx - 44, cy + 82, label, 14, 700, "middle"),
    ]
