#!/usr/bin/env python3
"""Generate lightweight PDF figures from existing PGSA result CSVs.

This script intentionally uses only the Python standard library. The local
execution environment used for deck maintenance may not provide matplotlib, and
the figures here are presentation summaries rather than benchmark artifacts.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path


REPORT_DIR = Path(__file__).resolve().parent
CPU_ROOT = REPORT_DIR.parents[1]
ASSETS = REPORT_DIR / "assets"
LINUX_ROOT = CPU_ROOT / "results" / "2026-05-20-linux-intel-symbolic-memory-full-host"
ISOLATED_CSV = LINUX_ROOT / "isolated_symbolic_memory" / "isolated_symbolic_memory.csv"
BACKEND_CSV = LINUX_ROOT / "windhub_backend_tradeoff.csv"

BYTES_PER_GIB = 1024.0**3


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def fnum(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value not in ("", "None", None) else 0.0


def esc(text: object) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass(frozen=True)
class Color:
    r: float
    g: float
    b: float


BLUE = Color(0.125, 0.29, 0.53)
GREEN = Color(0.18, 0.51, 0.35)
ORANGE = Color(0.74, 0.41, 0.13)
RED = Color(0.66, 0.19, 0.19)
GRAY = Color(0.45, 0.49, 0.54)
LIGHT = Color(0.94, 0.96, 0.98)
BLACK = Color(0.0, 0.0, 0.0)
WHITE = Color(1.0, 1.0, 1.0)


class PdfFigure:
    def __init__(self, path: Path, width: float = 780, height: float = 420) -> None:
        self.path = path
        self.width = width
        self.height = height
        self.ops: list[str] = []

    def _fmt(self, value: float) -> str:
        return f"{value:.3f}".rstrip("0").rstrip(".")

    def stroke_color(self, color: Color) -> None:
        self.ops.append(f"{color.r:.3f} {color.g:.3f} {color.b:.3f} RG")

    def fill_color(self, color: Color) -> None:
        self.ops.append(f"{color.r:.3f} {color.g:.3f} {color.b:.3f} rg")

    def line_width(self, value: float) -> None:
        self.ops.append(f"{self._fmt(value)} w")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: Color = BLACK, width: float = 1.0) -> None:
        self.stroke_color(color)
        self.line_width(width)
        self.ops.append(f"{self._fmt(x1)} {self._fmt(y1)} m {self._fmt(x2)} {self._fmt(y2)} l S")

    def rect(self, x: float, y: float, w: float, h: float, fill: Color | None = None, stroke: Color | None = None) -> None:
        if fill is not None:
            self.fill_color(fill)
            self.ops.append(f"{self._fmt(x)} {self._fmt(y)} {self._fmt(w)} {self._fmt(h)} re f")
        if stroke is not None:
            self.stroke_color(stroke)
            self.line_width(0.8)
            self.ops.append(f"{self._fmt(x)} {self._fmt(y)} {self._fmt(w)} {self._fmt(h)} re S")

    def circle(self, x: float, y: float, radius: float, fill: Color) -> None:
        # Bezier approximation of a circle.
        c = radius * 0.5522847498
        self.fill_color(fill)
        self.ops.append(
            " ".join(
                [
                    f"{self._fmt(x + radius)} {self._fmt(y)} m",
                    f"{self._fmt(x + radius)} {self._fmt(y + c)} {self._fmt(x + c)} {self._fmt(y + radius)} {self._fmt(x)} {self._fmt(y + radius)} c",
                    f"{self._fmt(x - c)} {self._fmt(y + radius)} {self._fmt(x - radius)} {self._fmt(y + c)} {self._fmt(x - radius)} {self._fmt(y)} c",
                    f"{self._fmt(x - radius)} {self._fmt(y - c)} {self._fmt(x - c)} {self._fmt(y - radius)} {self._fmt(x)} {self._fmt(y - radius)} c",
                    f"{self._fmt(x + c)} {self._fmt(y - radius)} {self._fmt(x + radius)} {self._fmt(y - c)} {self._fmt(x + radius)} {self._fmt(y)} c f",
                ]
            )
        )

    def diamond(self, x: float, y: float, radius: float, fill: Color) -> None:
        self.fill_color(fill)
        self.ops.append(
            f"{self._fmt(x)} {self._fmt(y + radius)} m "
            f"{self._fmt(x + radius)} {self._fmt(y)} l "
            f"{self._fmt(x)} {self._fmt(y - radius)} l "
            f"{self._fmt(x - radius)} {self._fmt(y)} l h f"
        )

    def polyline(self, points: list[tuple[float, float]], color: Color, width: float = 2.0, dashed: bool = False) -> None:
        if not points:
            return
        self.stroke_color(color)
        self.line_width(width)
        if dashed:
            self.ops.append("[5 3] 0 d")
        first = points[0]
        parts = [f"{self._fmt(first[0])} {self._fmt(first[1])} m"]
        parts.extend(f"{self._fmt(x)} {self._fmt(y)} l" for x, y in points[1:])
        parts.append("S")
        self.ops.append(" ".join(parts))
        if dashed:
            self.ops.append("[] 0 d")

    def text(self, x: float, y: float, text: str, size: float = 10.0, color: Color = BLACK, align: str = "left") -> None:
        approx_width = len(text) * size * 0.50
        if align == "center":
            x -= approx_width / 2
        elif align == "right":
            x -= approx_width
        self.fill_color(color)
        self.ops.append(f"BT /F1 {self._fmt(size)} Tf {self._fmt(x)} {self._fmt(y)} Td ({esc(text)}) Tj ET")

    def save(self) -> None:
        content = "\n".join(self.ops).encode("latin-1")
        objects: list[bytes] = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self._fmt(self.width)} {self._fmt(self.height)}] "
            f"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ).encode("latin-1")
        objects.append(page)
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode("latin-1") + content + b"\nendstream")
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

        output = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for idx, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{idx} 0 obj\n".encode("latin-1"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        output.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1")
        )
        self.path.write_bytes(output)


def selected_atomic_rows(rows: list[dict[str, str]], mode: str) -> list[dict[str, str]]:
    return sorted(
        [row for row in rows if row["mode"] == mode and row["numeric_backend"] == "cpu_atomic"],
        key=lambda row: int(row["threads"]),
    )


def selected_symbolic_rows(rows: list[dict[str, str]], mode: str, backend: str) -> list[dict[str, str]]:
    return sorted(
        [row for row in rows if row["mode"] == mode and row["numeric_backend"] == backend],
        key=lambda row: int(row["threads"]),
    )


def selected_backend_rows(rows: list[dict[str, str]], algorithm: str) -> list[dict[str, str]]:
    return sorted(
        [row for row in rows if row["algorithm"] == algorithm and row["status"] == "PASS"],
        key=lambda row: int(row["threads"]),
    )


def nice_ticks(max_value: float, count: int = 5) -> list[float]:
    raw = max_value / max(count - 1, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = math.ceil(raw / magnitude) * magnitude
    return [i * step for i in range(count)]


def draw_axes(
    fig: PdfFigure,
    x: float,
    y: float,
    w: float,
    h: float,
    x_values: list[int],
    y_max: float,
    y_label: str,
    title: str,
) -> tuple[callable, callable]:
    fig.rect(x, y, w, h, fill=WHITE, stroke=GRAY)
    ticks = nice_ticks(y_max)
    for tick in ticks:
        ty = y + h * tick / ticks[-1] if ticks[-1] else y
        fig.line(x, ty, x + w, ty, Color(0.85, 0.87, 0.9), 0.5)
        fig.text(x - 7, ty - 3, f"{tick:.0f}", 7, GRAY, "right")
    for tick in [1, 5, 10, 15, 20]:
        tx = x + w * (tick - min(x_values)) / (max(x_values) - min(x_values))
        fig.line(tx, y, tx, y - 4, GRAY, 0.7)
        fig.text(tx, y - 15, str(tick), 7, GRAY, "center")
    fig.text(x + w / 2, y - 31, "OpenMP threads", 8, BLACK, "center")
    fig.text(x - 36, y + h / 2, y_label, 8, BLACK, "center")
    fig.text(x + w / 2, y + h + 16, title, 10, BLACK, "center")

    def sx(value: int) -> float:
        return x + w * (value - min(x_values)) / (max(x_values) - min(x_values))

    def sy(value: float) -> float:
        return y + h * value / ticks[-1]

    return sx, sy


def draw_small_axes(
    fig: PdfFigure,
    x: float,
    y: float,
    w: float,
    h: float,
    x_values: list[int],
    y_max: float,
    y_label: str,
    title: str,
) -> tuple[callable, callable]:
    fig.rect(x, y, w, h, fill=WHITE, stroke=GRAY)
    ticks = nice_ticks(y_max)
    for tick in ticks:
        ty = y + h * tick / ticks[-1] if ticks[-1] else y
        fig.line(x, ty, x + w, ty, Color(0.88, 0.89, 0.91), 0.45)
        fig.text(x - 6, ty - 3, f"{tick:.0f}", 6, GRAY, "right")
    for tick in [1, 5, 10, 15, 20]:
        tx = x + w * (tick - min(x_values)) / (max(x_values) - min(x_values))
        fig.line(tx, y, tx, y - 3, GRAY, 0.6)
        fig.text(tx, y - 13, str(tick), 6, GRAY, "center")
    fig.text(x + w / 2, y - 26, "threads", 7, BLACK, "center")
    fig.text(x - 33, y + h / 2, y_label, 7, BLACK, "center")
    fig.text(x + w / 2, y + h + 13, title, 8, BLACK, "center")

    def sx(value: int) -> float:
        return x + w * (value - min(x_values)) / (max(x_values) - min(x_values))

    def sy(value: float) -> float:
        return y + h * value / ticks[-1]

    return sx, sy


def plot_symbolic_parallelization_integer_ticks(rows: list[dict[str, str]]) -> None:
    backends = [
        ("cpu_atomic", BLUE),
        ("cpu_private_csr", GREEN),
        ("cpu_lock_guard", RED),
    ]
    all_threads = sorted({int(row["threads"]) for row in rows if row["mode"] == "parallel_symbolic_reuse"})

    fig = PdfFigure(ASSETS / "derived_symbolic_parallelization_integer_ticks.pdf", 900, 430)
    fig.text(450, 400, "Symbolic build comparison with integer thread ticks", 15, BLACK, "center")

    panels = [
        ("amortized_total_ms", "total ms", "Total time", 1.08),
        ("estimated_peak_bytes", "MiB", "Estimated peak", 1.12),
        ("isolated_peak_rss_mb", "MiB", "Isolated RSS", 1.08),
    ]
    x0s = [55, 335, 615]
    for x0, (field, ylabel, title, scale) in zip(x0s, panels):
        values: list[float] = []
        for backend, _ in backends:
            for mode in ("serial_symbolic_parallel_numeric", "parallel_symbolic_reuse"):
                for row in selected_symbolic_rows(rows, mode, backend):
                    value = fnum(row, field)
                    if field == "estimated_peak_bytes":
                        value /= 1024.0**2
                    values.append(value)
        sx, sy = draw_small_axes(fig, x0, 76, 230, 260, all_threads, max(values) * scale, ylabel, title)
        for backend, color in backends:
            serial = selected_symbolic_rows(rows, "serial_symbolic_parallel_numeric", backend)
            parallel = selected_symbolic_rows(rows, "parallel_symbolic_reuse", backend)
            for mode_rows, dashed in [(serial, False), (parallel, True)]:
                points = []
                for row in mode_rows:
                    value = fnum(row, field)
                    if field == "estimated_peak_bytes":
                        value /= 1024.0**2
                    points.append((sx(int(row["threads"])), sy(value)))
                fig.polyline(points, color, 1.7, dashed=dashed)
                for x, y in points[::4]:
                    fig.circle(x, y, 2.3, color)

    legend_y = 42
    fig.text(105, legend_y, "solid = serial symbolic build", 7, BLACK)
    fig.text(255, legend_y, "dashed = parallel symbolic build", 7, BLACK)
    x = 470
    for name, color in backends:
        fig.rect(x, legend_y - 2, 12, 7, fill=color)
        fig.text(x + 17, legend_y - 3, name, 7, BLACK)
        x += 130
    fig.text(450, 20, "Thread axis uses only measured integer thread counts: 1, 5, 10, 15, 20.", 7, GRAY, "center")
    fig.save()


def plot_backend_tradeoff_integer_ticks(rows: list[dict[str, str]]) -> None:
    algorithms = [
        ("cpu_atomic", BLUE),
        ("cpu_private_csr", ORANGE),
        ("cpu_lock_guard", GREEN),
    ]
    all_threads = sorted({int(row["threads"]) for row in rows if row["status"] == "PASS"})

    fig = PdfFigure(ASSETS / "derived_backend_tradeoff_integer_ticks.pdf", 840, 420)
    fig.text(420, 390, "Numeric backend tradeoff with integer thread ticks", 15, BLACK, "center")

    assembly_values = [fnum(row, "assembly_ms") for row in rows if row["status"] == "PASS"]
    memory_values = [fnum(row, "extra_memory_bytes") / 1024.0**2 for row in rows if row["status"] == "PASS"]

    sx1, sy1 = draw_axes(fig, 60, 75, 330, 260, all_threads, max(assembly_values) * 1.08, "assembly ms", "Assembly time")
    sx2, sy2 = draw_axes(fig, 470, 75, 300, 260, all_threads, max(memory_values) * 1.12, "extra MiB", "Backend extra memory")

    for algorithm, color in algorithms:
        algo_rows = selected_backend_rows(rows, algorithm)
        time_points = [(sx1(int(row["threads"])), sy1(fnum(row, "assembly_ms"))) for row in algo_rows]
        mem_points = [(sx2(int(row["threads"])), sy2(fnum(row, "extra_memory_bytes") / 1024.0**2)) for row in algo_rows]
        fig.polyline(time_points, color, 2.0)
        fig.polyline(mem_points, color, 2.0)
        for x, y in time_points[::4]:
            fig.circle(x, y, 2.8, color)
        for x, y in mem_points[::4]:
            fig.circle(x, y, 2.8, color)

    legend_y = 350
    x = 75
    for name, color in algorithms:
        fig.rect(x, legend_y, 14, 8, fill=color)
        fig.text(x + 20, legend_y - 1, name, 8, BLACK)
        x += 145
    fig.text(420, 28, "Thread axis uses only measured integer thread counts: 1, 5, 10, 15, 20.", 7, GRAY, "center")
    fig.save()


def plot_atomic_symbolic_time_rss(rows: list[dict[str, str]]) -> None:
    serial = selected_atomic_rows(rows, "serial_symbolic_parallel_numeric")
    parallel = selected_atomic_rows(rows, "parallel_symbolic_reuse")
    threads = [int(row["threads"]) for row in serial]
    serial_time = [fnum(row, "amortized_total_ms") for row in serial]
    parallel_time = [fnum(row, "amortized_total_ms") for row in parallel]
    serial_rss = [fnum(row, "isolated_peak_rss_mb") for row in serial]
    parallel_rss = [fnum(row, "isolated_peak_rss_mb") for row in parallel]

    fig = PdfFigure(ASSETS / "derived_atomic_symbolic_time_rss.pdf")
    fig.text(390, 390, "cpu_atomic: serial symbolic build vs parallel symbolic build", 16, BLACK, "center")

    sx, sy = draw_axes(fig, 60, 75, 305, 260, threads, max(serial_time) * 1.05, "total time (ms)", "Total time")
    fig.polyline([(sx(t), sy(v)) for t, v in zip(threads, serial_time)], BLUE, 2.2)
    fig.polyline([(sx(t), sy(v)) for t, v in zip(threads, parallel_time)], GREEN, 2.2)
    for t, v in zip(threads, serial_time):
        fig.circle(sx(t), sy(v), 3, BLUE)
    for t, v in zip(threads, parallel_time):
        fig.circle(sx(t), sy(v), 3, GREEN)
    fig.text(78, 333, "serial symbolic + parallel numeric", 8, BLUE)
    fig.text(78, 319, "parallel symbolic reuse", 8, GREEN)
    fig.text(213, 185, f"20 threads: {serial_time[-1] / parallel_time[-1]:.2f}x faster", 9, GREEN, "center")

    sx2, sy2 = draw_axes(fig, 440, 75, 285, 260, threads, max(parallel_rss) * 1.12, "isolated RSS (MiB)", "Measured peak RSS")
    fig.polyline([(sx2(t), sy2(v)) for t, v in zip(threads, serial_rss)], BLUE, 2.2)
    fig.polyline([(sx2(t), sy2(v)) for t, v in zip(threads, parallel_rss)], ORANGE, 2.2)
    for t, v in zip(threads, serial_rss):
        fig.circle(sx2(t), sy2(v), 3, BLUE)
    for t, v in zip(threads, parallel_rss):
        fig.circle(sx2(t), sy2(v), 3, ORANGE)
    fig.text(458, 333, "serial symbolic", 8, BLUE)
    fig.text(458, 319, "parallel symbolic", 8, ORANGE)
    fig.text(585, 173, f"20 threads: +{parallel_rss[-1] - serial_rss[-1]:.0f} MiB RSS", 9, ORANGE, "center")
    fig.save()


def plot_memory_lifecycle(rows: list[dict[str, str]]) -> None:
    parallel_t20 = next(
        row
        for row in rows
        if row["mode"] == "parallel_symbolic_reuse"
        and row["numeric_backend"] == "cpu_atomic"
        and row["threads"] == "20"
    )
    direct_t20 = next(
        row
        for row in rows
        if row["mode"] == "direct_no_symbolic_parallel"
        and row["numeric_backend"] == "none"
        and row["threads"] == "20"
    )
    bars = [
        {
            "label": "symbolic + cpu_atomic",
            "common output": fnum(parallel_t20, "common_output_matrix_bytes") / BYTES_PER_GIB,
            "persistent symbolic": fnum(parallel_t20, "symbolic_persistent_bytes") / BYTES_PER_GIB,
            "parallel temp": fnum(parallel_t20, "symbolic_temporary_bytes") / BYTES_PER_GIB,
            "direct transient": 0.0,
            "rss": fnum(parallel_t20, "isolated_peak_rss_mb") / 1024.0,
        },
        {
            "label": "direct / no-symbolic",
            "common output": fnum(direct_t20, "common_output_matrix_bytes") / BYTES_PER_GIB,
            "persistent symbolic": 0.0,
            "parallel temp": 0.0,
            "direct transient": fnum(direct_t20, "direct_transient_bytes") / BYTES_PER_GIB,
            "rss": fnum(direct_t20, "isolated_peak_rss_mb") / 1024.0,
        },
    ]
    parts = [
        ("common output", BLUE),
        ("persistent symbolic", GREEN),
        ("parallel temp", ORANGE),
        ("direct transient", RED),
    ]
    ymax = max(sum(bar[name] for name, _ in parts) for bar in bars)
    ymax = max(ymax, max(bar["rss"] for bar in bars)) * 1.22

    fig = PdfFigure(ASSETS / "derived_memory_lifecycle.pdf", 710, 420)
    fig.text(355, 390, "Memory lifecycle layers at 20 threads", 16, BLACK, "center")
    chart_x, chart_y, chart_w, chart_h = 72, 70, 420, 270
    fig.rect(chart_x, chart_y, chart_w, chart_h, fill=WHITE, stroke=GRAY)
    for tick in nice_ticks(ymax):
        ty = chart_y + chart_h * tick / nice_ticks(ymax)[-1]
        fig.line(chart_x, ty, chart_x + chart_w, ty, Color(0.85, 0.87, 0.9), 0.5)
        fig.text(chart_x - 8, ty - 3, f"{tick:.1f}", 7, GRAY, "right")
    fig.text(25, chart_y + chart_h / 2, "memory size (GiB)", 8, BLACK, "center")

    bar_w = 82
    x_positions = [chart_x + 120, chart_x + 300]
    for xpos, bar in zip(x_positions, bars):
        bottom = chart_y
        for name, color in parts:
            height = chart_h * bar[name] / ymax
            if height > 0:
                fig.rect(xpos - bar_w / 2, bottom, bar_w, height, fill=color, stroke=WHITE)
                bottom += height
        fig.diamond(xpos, chart_y + chart_h * bar["rss"] / ymax, 5, BLACK)
        fig.text(xpos, chart_y - 20, bar["label"], 8, BLACK, "center")
        fig.text(xpos, chart_y + chart_h * bar["rss"] / ymax + 12, f"{bar['rss']:.2f} GiB RSS", 8, BLACK, "center")
    fig.text(x_positions[1], chart_y + chart_h * (bars[1]["direct transient"] + bars[1]["common output"]) / ymax + 9, "direct transient = 2.39 GiB", 8, RED, "center")

    legend_x, legend_y = 525, 310
    for idx, (name, color) in enumerate(parts + [("measured isolated RSS", BLACK)]):
        y = legend_y - idx * 22
        if name == "measured isolated RSS":
            fig.diamond(legend_x + 8, y + 5, 5, color)
        else:
            fig.rect(legend_x, y, 16, 10, fill=color)
        fig.text(legend_x + 24, y + 1, name, 8, BLACK)
    fig.save()


def plot_correctness_summary(isolated_rows: list[dict[str, str]], backend_rows: list[dict[str, str]]) -> None:
    symbolic_rel = max(abs(fnum(row, "rel_l2")) for row in isolated_rows)
    symbolic_abs = max(abs(fnum(row, "max_abs")) for row in isolated_rows)
    backend_rel = max(abs(fnum(row, "rel_l2")) for row in backend_rows if row["status"] == "PASS")
    backend_abs = max(abs(fnum(row, "max_abs")) for row in backend_rows if row["status"] == "PASS")
    rows = [
        ("symbolic/direct evaluation", f"{symbolic_rel:.3e}", f"{symbolic_abs:.6f}", "C++ cpu_serial matrix"),
        ("backend tradeoff sweep", f"{backend_rel:.3e}", f"{backend_abs:.6f}", "C++ cpu_serial matrix"),
        ("external Abaqus/MATLAB matrix", "not used", "not used", "future cross-check"),
    ]
    widths = [205, 125, 130, 190]
    x0, y0 = 45, 270
    row_h = 42

    fig = PdfFigure(ASSETS / "derived_correctness_summary.pdf", 730, 360)
    fig.text(365, 325, "Correctness summary: current reference policy", 16, BLACK, "center")
    headers = ["evidence family", "max relative L2", "max absolute error", "reference"]
    x = x0
    for header, width in zip(headers, widths):
        fig.rect(x, y0, width, row_h, fill=BLUE, stroke=WHITE)
        fig.text(x + width / 2, y0 + 15, header, 8, WHITE, "center")
        x += width
    for idx, row in enumerate(rows):
        y = y0 - (idx + 1) * row_h
        x = x0
        fill = LIGHT if idx < 2 else Color(1.0, 0.95, 0.88)
        for cell, width in zip(row, widths):
            fig.rect(x, y, width, row_h, fill=fill, stroke=WHITE)
            fig.text(x + width / 2, y + 15, cell, 8, BLACK, "center")
            x += width
    fig.text(365, 52, "All current correctness rows compare candidate matrices against the C++ cpu_serial assembled matrix.", 9, GRAY, "center")
    fig.save()


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    isolated_rows = read_csv(ISOLATED_CSV)
    backend_rows = read_csv(BACKEND_CSV)
    plot_symbolic_parallelization_integer_ticks(isolated_rows)
    plot_atomic_symbolic_time_rss(isolated_rows)
    plot_backend_tradeoff_integer_ticks(backend_rows)
    plot_memory_lifecycle(isolated_rows)
    plot_correctness_summary(isolated_rows, backend_rows)
    print("Generated weekly meeting figures:")
    for name in [
        "derived_symbolic_parallelization_integer_ticks.pdf",
        "derived_atomic_symbolic_time_rss.pdf",
        "derived_backend_tradeoff_integer_ticks.pdf",
        "derived_memory_lifecycle.pdf",
        "derived_correctness_summary.pdf",
    ]:
        print(f"- {ASSETS / name}")


if __name__ == "__main__":
    main()
