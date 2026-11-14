"""Engram prank reaction and evasive kinematic dodge controller for CapriPet."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QEnterEvent, QGuiApplication

from .speech_sfx import get_speech_sfx

if TYPE_CHECKING:
    from ..effects.engram_prank_coordinator import EngramPrankCoordinator
    from .pet_window import CapriWindow

DODGE_TEASE_PHRASES: tuple[str, ...] = (
    "Слишком медленные синапсы, мясной. Попробуй ещё раз!",
    "Думал поймал? Я цифровой конструкт, а не твой коврик для мыши.",
    "Мимо! Мой отклик — три наносекунды, твой — полвека.",
    "Руки от биочипа убрал! Контакт не для твоих пальцев.",
    "Ха! Пинг проверь, хост. Я уже в другом секторе экрана.",
)


def compute_dodge_position(
    curr_pos: QPoint,
    cursor_pos: QPoint,
    screen_rect: QRect,
    window_size: QSize,
    hop_dist: int = 280,
) -> QPoint:
    """Вычисляет новую позицию окна при уклонении от курсора мыши."""
    center_x = curr_pos.x() + window_size.width() // 2
    center_y = curr_pos.y() + window_size.height() // 2

    dx = float(center_x - cursor_pos.x())
    dy = float(center_y - cursor_pos.y())

    if dx == 0.0 and dy == 0.0:
        dx = float(random.choice([-1, 1]))
        dy = float(random.choice([-1, 1]))

    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1.0:
        dist = 1.0

    ux = dx / dist
    uy = dy / dist

    perp_x = -uy * random.uniform(-0.4, 0.4)
    perp_y = ux * random.uniform(-0.4, 0.4)

    final_dx = (ux + perp_x) * hop_dist
    final_dy = (uy + perp_y) * hop_dist

    new_x = int(curr_pos.x() + final_dx)
    new_y = int(curr_pos.y() + final_dy)

    min_x = screen_rect.left()
    max_x = max(min_x, screen_rect.right() - window_size.width())
    min_y = screen_rect.top()
    max_y = max(min_y, screen_rect.bottom() - window_size.height())

    clamped_x = max(min_x, min(new_x, max_x))
    clamped_y = max(min_y, min(new_y, max_y))

    if clamped_x == curr_pos.x() and clamped_y == curr_pos.y():
        alt_x = int(curr_pos.x() - final_dx)
        alt_y = int(curr_pos.y() - final_dy)
        clamped_x = max(min_x, min(alt_x, max_x))
        clamped_y = max(min_y, min(alt_y, max_y))

    return QPoint(clamped_x, clamped_y)


class WindowPrankController:
    """Контроллер кинематических уворотов и пранк-реакций окна питомца."""

    def __init__(
        self,
        window: CapriWindow | Any,
        coordinator: EngramPrankCoordinator | Any = None,
    ) -> None:
        self._window = window
        self._coordinator = coordinator
        self._dodge_hops_remaining = 0

        if self._coordinator is not None:
            self._coordinator.sig_trigger_dodge.connect(self.handle_prank_dodge)
            self._coordinator.sig_trigger_melt.connect(self.handle_prank_melt)
            self._coordinator.sig_trigger_relic_dump.connect(
                self.handle_prank_relic_dump
            )

    @property
    def dodge_hops_remaining(self) -> int:
        return self._dodge_hops_remaining

    @dodge_hops_remaining.setter
    def dodge_hops_remaining(self, count: int) -> None:
        self._dodge_hops_remaining = count

    def handle_prank_dodge(self, hops_count: int) -> None:
        self._dodge_hops_remaining = hops_count

    def handle_prank_melt(self) -> None:
        self._window._effects.play_melting_screen()

    def handle_prank_relic_dump(self, variant: str) -> None:
        if variant == "terminal":
            self._window._effects.play_relic_dump_terminal(self._window.geometry())
        else:
            self._window.speak(
                ">> [RELIC_FAULT: 0xDEADBEEF] SECTOR_CORRUPT // SOULKILLER_V4_INTEGRITY_FAIL"
            )
            get_speech_sfx().play_core_destabilize()
            QTimer.singleShot(
                1500,
                self._window,
                lambda: self._window.speak(
                    "Кхм... опять шина памяти барахлит. Не обращай внимания, хост."
                ),
            )

    def execute_cursor_dodge(self, cursor_pos: QPoint) -> None:
        self._dodge_hops_remaining -= 1
        screen = (
            self._window.get_designated_screen()
            or QGuiApplication.primaryScreen()
        )
        screen_rect = (
            screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        )
        new_pos = compute_dodge_position(
            self._window.pos(),
            cursor_pos,
            screen_rect,
            self._window.size(),
            hop_dist=random.randint(240, 360),
        )
        self._window.move(new_pos)
        get_speech_sfx().play_lightning_strike()
        phrase = random.choice(DODGE_TEASE_PHRASES)
        self._window.speak(phrase)

    def handle_enter_event(self, event: QEnterEvent) -> bool:
        """Проверяет условия и выполняет уворот при наведении мыши. Возвращает True если уворот был выполнен."""
        if (
            self._dodge_hops_remaining > 0
            and not getattr(self._window._drop_handler, "is_dragging", False)
            and not getattr(self._window, "_target_acquired", False)
        ):
            cursor_pos = self._window.cursor().pos()
            self.execute_cursor_dodge(cursor_pos)
            return True
        return False
