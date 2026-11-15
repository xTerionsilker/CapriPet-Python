#!/usr/bin/env python3
"""Инструмент для замеров времени запуска приложения CapriPet (Issue #57).

Измеряет время старта в двух режимах:
- Сухая (Headless): инициализация ядра, предзагрузка моделей и SFX без создания GUI.
- С отображением (GUI): полный цикл запуска приложения до первого кадра рендеринга окна.
"""

from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
from typing import NamedTuple

DRY_SNIPPET = """
import time
t0 = time.perf_counter()

from PySide6.QtCore import QLoggingCategory
from capri.core.settings import get_config_value, init_user_agent_async
from capri.audio.sfx_player import preload_sfx_cache_async
from capri.audio.recognizer import preload_model_async

QLoggingCategory.setFilterRules("qt.multimedia*=false")
preload_sfx_cache_async()
if get_config_value("audio.voice_enabled", True):
    preload_model_async()
init_user_agent_async()

t1 = time.perf_counter()
print(f"BENCH_DRY_MS:{(t1 - t0) * 1000.0:.2f}", flush=True)
import os
os._exit(0)
"""

GUI_SNIPPET = """
import os
import sys
import time
t0 = time.perf_counter()

from PySide6.QtCore import QLoggingCategory, QTimer
from PySide6.QtWidgets import QApplication

from capri import CapriWindow
from capri.audio.recognizer import preload_model_async
from capri.core.settings import get_config_value, init_user_agent_async
from capri.audio.sfx_player import preload_sfx_cache_async
from capri.ui.theme import get_font, init_fonts

QLoggingCategory.setFilterRules("qt.multimedia*=false")
preload_sfx_cache_async()
if get_config_value("audio.voice_enabled", True):
    preload_model_async()
init_user_agent_async()

app = QApplication(sys.argv)
app.setApplicationName("Capri")
app.setQuitOnLastWindowClosed(False)
init_fonts()
app.setFont(get_font(12))
window = CapriWindow()
window.show()

def on_ready() -> None:
    t_ready = time.perf_counter()
    print(f"BENCH_GUI_MS:{(t_ready - t0) * 1000.0:.2f}", flush=True)
    window.effects.stop_all()
    window.close()
    os._exit(0)

QTimer.singleShot(0, on_ready)
app.exec()
"""


class BenchmarkResult(NamedTuple):
    """Результаты замеров серии запусков."""

    mode: str
    runs: list[float]

    @property
    def min_ms(self) -> float:
        return min(self.runs) if self.runs else 0.0

    @property
    def max_ms(self) -> float:
        return max(self.runs) if self.runs else 0.0

    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.runs) if self.runs else 0.0

    @property
    def std_ms(self) -> float:
        return statistics.stdev(self.runs) if len(self.runs) > 1 else 0.0


def run_single_measurement(snippet: str, marker: str, timeout: float = 30.0) -> float:
    """Выполняет одиночный замер запуска в изолированном процессе."""
    cmd = [sys.executable, "-c", snippet]
    proc = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            _, val = line.split(":", 1)
            return float(val.strip())
    raise RuntimeError(f"Маркер {marker} не найден в выводе: {proc.stdout}\n{proc.stderr}")


def run_benchmark_series(
    mode: str,
    iterations: int = 5,
    warmup: int = 1,
) -> BenchmarkResult:
    """Запускает серию замеров для указанного режима."""
    snippet = DRY_SNIPPET if mode == "dry" else GUI_SNIPPET
    marker = "BENCH_DRY_MS:" if mode == "dry" else "BENCH_GUI_MS:"

    # Прогревочные итерации
    if warmup > 0:
        print(f"  [прогрев {warmup} итер.]...", flush=True)
        for _ in range(warmup):
            run_single_measurement(snippet, marker)

    runs: list[float] = []
    for i in range(iterations):
        val = run_single_measurement(snippet, marker)
        runs.append(val)
        print(f"  [#{i+1}] {val:.1f} мс", flush=True)
    return BenchmarkResult(mode=mode, runs=runs)


def print_report_table(results: list[BenchmarkResult]) -> None:
    """Выводит красивую киберпанк-таблицу с результатами замеров."""
    sep = (
        "+" + "-" * 28 + "+" + "-" * 10 + "+"
        + "-" * 12 + "+" + "-" * 12 + "+"
        + "-" * 12 + "+" + "-" * 10 + "+"
    )
    print(sep)
    header = (
        f"| {'Режим запуска':<26} | {'Итераций':<8} | "
        f"{'Min (мс)':<10} | {'Avg (мс)':<10} | {'Max (мс)':<10} | {'StdDev':<8} |"
    )
    print(header)
    print(sep)
    for res in results:
        title = "Сухая (Headless ядро)" if res.mode == "dry" else "С отображением (GUI окно)"
        line = (
            f"| {title:<26} | {len(res.runs):<8} | {res.min_ms:<10.1f} | "
            f"{res.avg_ms:<10.1f} | {res.max_ms:<10.1f} | {res.std_ms:<8.1f} |"
        )
        print(line)
    print(sep)


def main() -> int:
    """Главная точка входа утилиты бенчмаркинга старта."""
    parser = argparse.ArgumentParser(description="Бенчмарк времени запуска CapriPet")
    parser.add_argument(
        "--mode",
        choices=["all", "dry", "gui"],
        default="all",
        help="Режим замера (dry: headless ядро, gui: полное окно CapriWindow, all: оба)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Количество итераций замера (по умолчанию: 5)",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Количество прогревочных запусков (по умолчанию: 1)",
    )

    args = parser.parse_args()
    modes = ["dry", "gui"] if args.mode == "all" else [args.mode]
    results: list[BenchmarkResult] = []

    print(
        f">> Запуск бенчмаркинга старта CapriPet ({len(modes)} режима(ов), итераций: {args.iterations})...",
        flush=True,
    )
    for m in modes:
        print(f">> Измерение режима: {m}...", flush=True)
        res = run_benchmark_series(m, iterations=args.iterations, warmup=args.warmup)
        results.append(res)

    print()
    print_report_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
