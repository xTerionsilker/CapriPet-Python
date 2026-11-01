from __future__ import annotations

import math
import random
import time
from typing import List

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .transition_fx import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_OBSIDIAN,
    COLOR_WHITE,
    PIXEL_SIZE,
    CyberKiroshiReticle,
    CyberPixelBolt,
    CyberPixelSpark,
    with_alpha,
)
from ..ui.speech_sfx import get_speech_sfx


def get_virtual_screen_geometry() -> QRect:
    """Возвращает объединенную геометрию всех экранов."""
    screens = QGuiApplication.screens()
    if not screens:
        return QRect(0, 0, 1920, 1080)
    rect = screens[0].geometry()
    for scr in screens[1:]:
        rect = rect.united(scr.geometry())
    return rect


class LightningTetherOverlay(QWidget):
    """
    Полноэкранный прозрачный оверлей для визуализации прицеливания телепортации:
    - От питомца (start_pos) до текущего положения курсора (target_pos) тянутся рваные красные кибер-молнии.
    - В точке курсора отображается тактический прицел захвата координат (Kiroshi Reticle) и HUD-дальномер.
    - Вокруг разряда и прицела летят пиксельные искры.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._start_pos = QPoint(0, 0)
        self._target_pos = QPoint(0, 0)
        self._origin_rect = QRect(0, 0, 0, 0)

        self._bolts: List[CyberPixelBolt] = []
        self._sparks: List[CyberPixelSpark] = []
        self._tick_count = 0
        self._start_time = 0.0

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)  # 50 FPS
        self._anim_timer.timeout.connect(self._on_tick)

        self._sfx_timer = QTimer(self)
        self._sfx_timer.setInterval(110)
        self._sfx_timer.timeout.connect(self._on_sfx_tick)

    def activate(self, start_pos: QPoint, target_pos: QPoint, origin_rect: QRect | None = None) -> None:
        """Активирует оверлей и начинает отрисовку молнии."""
        geo = get_virtual_screen_geometry()
        self.setGeometry(geo)

        self._start_pos = start_pos
        self._target_pos = target_pos
        self._origin_rect = origin_rect or QRect(start_pos.x() - 40, start_pos.y() - 40, 80, 80)
        self._tick_count = 0
        self._start_time = time.monotonic()
        self._sparks.clear()

        self._rebuild_bolts()

        self.raise_()
        self.show()
        self._anim_timer.start()
        self._sfx_timer.start()
        try:
            get_speech_sfx().play_lightning_zap()
        except Exception:
            pass
        self.update()

    def update_target(self, target_pos: QPoint) -> None:
        """Обновляет конечную точку молнии (курсор)."""
        if self._target_pos != target_pos:
            self._target_pos = target_pos
            self._rebuild_bolts()
            self.update()

    def update_start(self, start_pos: QPoint, origin_rect: QRect | None = None) -> None:
        """Обновляет начальную точку (например, центр питомца)."""
        self._start_pos = start_pos
        if origin_rect is not None:
            self._origin_rect = origin_rect
        self._rebuild_bolts()
        self.update()

    def deactivate(self) -> None:
        """Скрывает оверлей и останавливает анимацию."""
        self._anim_timer.stop()
        self._sfx_timer.stop()
        self.hide()
        self._bolts.clear()
        self._sparks.clear()

    def _rebuild_bolts(self) -> None:
        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        self._bolts.clear()

        dx = local_target.x() - local_start.x()
        dy = local_target.y() - local_start.y()
        dist = math.hypot(dx, dy)
        if dist < 8:
            return

        # Основной центральный ствол молнии
        self._bolts.append(
            CyberPixelBolt(
                local_start,
                local_target,
                color_scheme="crimson",
                branch_chance=0.28,
            )
        )

        # Дополнительный вихревой разряд для объема
        if dist > 35:
            jitter_start = local_start + QPoint(random.randint(-12, 12), random.randint(-12, 12))
            jitter_target = local_target + QPoint(random.randint(-8, 8), random.randint(-8, 8))
            self._bolts.append(
                CyberPixelBolt(
                    jitter_start,
                    jitter_target,
                    color_scheme="crimson",
                    branch_chance=0.35,
                )
            )

    def _on_tick(self) -> None:
        self._tick_count += 1
        offset = self.geometry().topLeft()
        local_target = self._target_pos - offset

        # Мерцание и перестройка молний
        for bolt in self._bolts:
            bolt.jitter()

        # Рождение пиксельных искр вокруг цели
        if random.random() < 0.65:
            angle = random.uniform(0, math.tau)
            speed = random.uniform(40.0, 160.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            kind = random.choice(("spark", "bit", "bar"))
            self._sparks.append(
                CyberPixelSpark(
                    local_target.x(),
                    local_target.y(),
                    vx,
                    vy,
                    color=random.choice((COLOR_CRIMSON, COLOR_WHITE, COLOR_ACID_GREEN)),
                    size=PIXEL_SIZE,
                    life=random.uniform(0.15, 0.40),
                    kind=kind,
                )
            )

        # Обновление существующих искр (step возвращает True пока искра жива)
        dt = 0.02
        self._sparks = [s for s in self._sparks if s.step(dt)]

        self.update()

    def _on_sfx_tick(self) -> None:
        if random.random() < 0.45:
            try:
                get_speech_sfx().play_lightning_zap()
            except Exception:
                pass

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        offset = self.geometry().topLeft()
        local_start = self._start_pos - offset
        local_target = self._target_pos - offset

        # 1. Отрисовка всех молний
        for bolt in self._bolts:
            bolt.draw(painter, progress=1.0)

        # 2. Отрисовка искр
        for spark in self._sparks:
            spark.draw(painter)

        # 3. Тактический прицел Kiroshi в точке курсора
        reticle_size = 64
        reticle_rect = QRect(
            local_target.x() - reticle_size // 2,
            local_target.y() - reticle_size // 2,
            reticle_size,
            reticle_size,
        )
        elapsed = time.monotonic() - self._start_time
        rotation = elapsed * math.tau * 0.9

        CyberKiroshiReticle.draw(
            painter,
            reticle_rect,
            progress=1.0,
            color=COLOR_CRIMSON,
            bracket_offset=int(abs(math.sin(elapsed * 6.0)) * 6),
            rotation=rotation,
            label="TELEPORT // LOCK",
            locked=True,
        )

        # 4. Вспомогательная телеметрия: вектор направления и дистанция
        dx = self._target_pos.x() - self._start_pos.x()
        dy = self._target_pos.y() - self._start_pos.y()
        dist = int(math.hypot(dx, dy))

        font = QFont("Press Start 2P")
        font.setPixelSize(8)
        painter.setFont(font)

        tag = f"DIST: {dist:04d}px // VECTOR:[{dx:+04d},{dy:+04d}]"
        tag_rect = QRect(local_target.x() + 38, local_target.y() - 8, 220, 16)
        painter.fillRect(tag_rect, with_alpha(COLOR_OBSIDIAN, 220))
        painter.setPen(QPen(COLOR_CRIMSON, 1))
        painter.drawRect(tag_rect)
        painter.setPen(COLOR_WHITE)
        painter.drawText(
            tag_rect.adjusted(4, 0, 0, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            tag,
        )

        # Точка привязки к Капри (микро-крестик)
        anchor_rect = QRect(local_start.x() - 6, local_start.y() - 6, 12, 12)
        painter.setPen(QPen(COLOR_ACID_GREEN, 1))
        painter.drawRect(anchor_rect)
        painter.drawLine(local_start.x() - 10, local_start.y(), local_start.x() + 10, local_start.y())
        painter.drawLine(local_start.x(), local_start.y() - 10, local_start.x(), local_start.y() + 10)

        painter.end()
