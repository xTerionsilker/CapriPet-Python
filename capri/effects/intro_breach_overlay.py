"""Кинематографичный полноэкранный интро-оверлей пробоя экрана (Studio Trigger Cyberpunk FX)."""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QElapsedTimer,
    QPoint,
    QPointF,
    QRect,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QScreen,
)
from PySide6.QtWidgets import QWidget

from ..ui.speech_sfx import get_speech_sfx
from .blackwall_data_stream import BlackwallDataStream
from .intro_breach_helpers import (
    GlassShard,
    SpeedLine,
    draw_arasaka_bios_terminal,
    draw_breach_lightning,
    draw_dialogue_cyber_hud,
    draw_kernel_panic_strobe,
)
from .transition_base import (
    COLOR_ACID_GREEN,
    COLOR_CRIMSON,
    COLOR_ELECTRIC_BLUE,
    COLOR_OBSIDIAN,
    COLOR_VIOLET,
    COLOR_WHITE,
    snap_pixel,
    with_alpha,
)
from .transition_painters import CyberShockwaveRing

_TOTAL_DURATION_SEC = 4.8
_BREACH_RADIUS = 230.0
_NUM_RADIAL_CRACKS = 16


@dataclass
class _GlassCrack:
    points: list[QPointF]
    color: QColor
    width: float


class IntroBreachOverlay(QWidget):
    """Полноэкранный оверлей захвата экрана, раскалывания стекла и кинетического прорыва Капри."""

    finished = Signal()

    def __init__(
        self,
        screen: QScreen | None = None,
        sprite_pixmap: QPixmap | None = None,
        on_finished: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._target_screen = screen or QGuiApplication.primaryScreen()
        screen_geo = self._target_screen.geometry() if self._target_screen else QRect(0, 0, 1920, 1080)
        self.setGeometry(screen_geo)

        if self._target_screen:
            self._desktop_pixmap: QPixmap = self._target_screen.grabWindow(0)
        else:
            self._desktop_pixmap = QPixmap(self.size())
            self._desktop_pixmap.fill(COLOR_OBSIDIAN)

        self._sprite_pixmap: QPixmap | None = sprite_pixmap
        if self._sprite_pixmap is None:
            self._load_fallback_sprite()

        if on_finished:
            self.finished.connect(on_finished)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)

        self._elapsed_timer = QElapsedTimer()
        self._elapsed_sec = 0.0

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        self._center = QPointF(cx, cy)

        self._matrix_stream = BlackwallDataStream(self.width(), self.height())
        self._cracks: list[_GlassCrack] = []
        self._hole_polygon = QPolygonF()
        self._shards: list[GlassShard] = []
        self._speedlines: list[SpeedLine] = []
        self._rng = random.Random(77)

        self._dialogue_sfx_played = False
        self._is_skipping = False
        self._skip_start_sec = 0.0
        self._generate_scene()


    def _load_fallback_sprite(self) -> None:
        assets_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "var" / "idle"
        if assets_dir.is_dir():
            candidates = sorted(assets_dir.glob("*.png"))
            if candidates:
                self._sprite_pixmap = QPixmap(str(candidates[0]))
        if self._sprite_pixmap is None or self._sprite_pixmap.isNull():
            self._sprite_pixmap = QPixmap(200, 240)
            self._sprite_pixmap.fill(COLOR_CRIMSON)

    def _generate_scene(self) -> None:
        cx, cy = self._center.x(), self._center.y()
        max_dim = max(self.width(), self.height())

        # 1. Генерация радиальных трещин и полигональной бреши
        hole_points: list[QPointF] = []
        for i in range(_NUM_RADIAL_CRACKS):
            angle = (2.0 * math.pi / _NUM_RADIAL_CRACKS) * i + self._rng.uniform(-0.09, 0.09)
            pts: list[QPointF] = [QPointF(cx, cy)]
            curr_r = 0.0
            hole_r = _BREACH_RADIUS * self._rng.uniform(0.80, 1.25)
            hole_recorded = False

            while curr_r < max_dim:
                curr_r += self._rng.uniform(30.0, 75.0)
                angle += self._rng.uniform(-0.07, 0.07)
                px = cx + curr_r * math.cos(angle)
                py = cy + curr_r * math.sin(angle)
                pts.append(QPointF(px, py))

                if not hole_recorded and curr_r >= hole_r:
                    hole_points.append(QPointF(px, py))
                    hole_recorded = True

            self._cracks.append(_GlassCrack(points=pts, color=COLOR_WHITE, width=2.4))
            pts_red = [QPointF(p.x() + 3.0, p.y() - 1.5) for p in pts]
            self._cracks.append(_GlassCrack(points=pts_red, color=COLOR_CRIMSON, width=1.5))

        self._hole_polygon = QPolygonF(hole_points)

        # 2. Генерация полигональных граненых осколков
        for _ in range(48):
            r = self._rng.uniform(15.0, _BREACH_RADIUS * 1.15)
            th = self._rng.uniform(0.0, 2.0 * math.pi)
            sx = cx + r * math.cos(th)
            sy = cy + r * math.sin(th)
            poly_type = self._rng.choice((3, 4))
            v_pts: list[QPointF] = []
            for vi in range(poly_type):
                va = (2.0 * math.pi / poly_type) * vi + self._rng.uniform(-0.3, 0.3)
                vr = self._rng.uniform(8.0, 22.0)
                v_pts.append(QPointF(vr * math.cos(va), vr * math.sin(va)))

            angle_dir = math.atan2(sy - cy, sx - cx)
            speed = self._rng.uniform(140.0, 480.0)
            self._shards.append(
                GlassShard(
                    poly=v_pts,
                    x=sx,
                    y=sy,
                    vx=speed * math.cos(angle_dir) + self._rng.uniform(-60.0, 60.0),
                    vy=speed * math.sin(angle_dir) - self._rng.uniform(80.0, 220.0),
                    rot=self._rng.uniform(0.0, 360.0),
                    v_rot=self._rng.uniform(-360.0, 360.0),
                    scale=self._rng.uniform(0.7, 1.4),
                    alpha=1.0,
                    color=self._rng.choice((COLOR_WHITE, COLOR_CRIMSON, COLOR_VIOLET, COLOR_OBSIDIAN)),
                )
            )

        # 3. Кинетические экшен-линии Studio Trigger
        for _ in range(36):
            self._speedlines.append(
                SpeedLine(
                    angle=self._rng.uniform(0.0, 2.0 * math.pi),
                    length=self._rng.uniform(90.0, 260.0),
                    dist=self._rng.uniform(180.0, 480.0),
                    width=self._rng.choice((2.0, 3.0, 4.5)),
                    color=self._rng.choice((COLOR_WHITE, COLOR_CRIMSON, COLOR_ACID_GREEN)),
                )
            )

    def start(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._elapsed_timer.start()
        self._timer.start()
        get_speech_sfx().play_intro_breach()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Space):
            if not self._is_skipping:
                self._is_skipping = True
                self._skip_start_sec = self._elapsed_sec
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_tick(self) -> None:
        dt = 0.016
        self._elapsed_sec = self._elapsed_timer.elapsed() / 1000.0
        self._matrix_stream.update(dt)

        if self._is_skipping and (self._elapsed_sec - self._skip_start_sec) >= 0.30:
            self._timer.stop()
            self.finished.emit()
            self.close()
            return

        if self._elapsed_sec >= 1.8:
            for s in self._shards:
                s.update(dt)

        if self._elapsed_sec >= 2.6 and not self._dialogue_sfx_played:
            self._dialogue_sfx_played = True
            get_speech_sfx().play_voice_success()

        if self._elapsed_sec >= _TOTAL_DURATION_SEC:
            self._timer.stop()
            self.finished.emit()
            self.close()
            return

        self.update()


    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        try:
            self._render_scene(painter)
        finally:
            painter.end()

    def _render_scene(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        t = self._elapsed_sec
        cx = self._center.x()
        cy = self._center.y()

        master_alpha = 1.0
        if self._is_skipping:
            skip_p = min(1.0, (t - self._skip_start_sec) / 0.30)
            master_alpha = max(0.0, 1.0 - skip_p)
        elif t >= 3.8:
            p_fade = min(1.0, (t - 3.8) / 1.0)
            master_alpha = 1.0 - QEasingCurve(QEasingCurve.Type.OutCubic).valueForProgress(p_fade)

        painter.setOpacity(master_alpha)

        # Фаза 0: Arasaka Relic BIOS терминал (0.0 - 1.0s)
        if t < 1.0:
            draw_arasaka_bios_terminal(painter, self.rect(), t)
            return

        # Фаза 1: Сбой биочипа и стробоскоп KERNEL PANIC (1.0 - 1.8s)
        if t < 1.8:
            draw_arasaka_bios_terminal(painter, self.rect(), 1.0)
            draw_kernel_panic_strobe(painter, self.rect(), t, self._rng)
            return

        # Вспышка в момент прорыва (1.80 - 1.86s)
        if 1.80 <= t < 1.86:
            painter.fillRect(self.rect(), with_alpha(COLOR_WHITE, 240))
            return

        # 1. Захваченный рабочий стол с микро-дрожанием при разрыве
        shake_x, shake_y = 0, 0
        if 1.86 <= t < 2.4:
            shake_amp = (1.0 - (t - 1.86) / 0.54) * 8.0
            shake_x = int(self._rng.uniform(-shake_amp, shake_amp))
            shake_y = int(self._rng.uniform(-shake_amp, shake_amp))

        painter.drawPixmap(shake_x, shake_y, self._desktop_pixmap)

        # 2. Отрисовка потока Blackwall сквозь разрыв
        breach_progress = min(1.0, (t - 1.86) / 0.50)
        scale_curve = QEasingCurve(QEasingCurve.Type.OutBack).valueForProgress(breach_progress)

        scaled_hole_pts = [
            QPointF(cx + (p.x() - cx) * scale_curve, cy + (p.y() - cy) * scale_curve)
            for p in self._hole_polygon
        ]
        hole_path = QPainterPath()
        hole_path.addPolygon(QPolygonF(scaled_hole_pts))
        hole_path.closeSubpath()

        painter.save()
        painter.setClipPath(hole_path)
        self._matrix_stream.render(painter, self.rect(), alpha=master_alpha)
        painter.restore()

        # 3. Электрические разряды по краям разлома
        draw_breach_lightning(painter, QPolygonF(scaled_hole_pts), self._rng, master_alpha)

        # 4. Расходящаяся ударная волна (Shockwave Ring)
        if 1.86 <= t < 2.5:
            sw_r = int((t - 1.86) * 1400.0)
            CyberShockwaveRing.draw(
                painter,
                QPoint(int(cx), int(cy)),
                sw_r,
                with_alpha(COLOR_CRIMSON, int(220 * master_alpha)),
                thickness=4,
            )

        # 5. Отрисовка трещин расколотого стекла
        crack_alpha = int(255 * master_alpha)
        for crack in self._cracks:
            painter.setPen(QPen(with_alpha(crack.color, int(crack_alpha * 0.9)), crack.width))
            for idx in range(len(crack.points) - 1):
                painter.drawLine(crack.points[idx], crack.points[idx + 1])

        # 6. Отрисовка падающих граненых осколков
        for shard in self._shards:
            shard.draw(painter, master_alpha)

        # 7. Экшен-линии скорости Studio Trigger
        if 2.0 <= t < 3.6:
            sl_progress = min(1.0, (t - 2.0) / 0.6)
            for line in self._speedlines:
                line.draw(painter, self._center, sl_progress, master_alpha)

        # 8. Кинетическое появление Капри
        if t >= 2.0:
            self._paint_capri_entrance(painter, t, master_alpha)

    def _paint_capri_entrance(self, painter: QPainter, t: float, master_alpha: float) -> None:
        cx, cy = int(self._center.x()), int(self._center.y())
        enter_p = min(1.0, (t - 2.0) / 0.6)
        scale = QEasingCurve(QEasingCurve.Type.OutBack).valueForProgress(enter_p)

        if not self._sprite_pixmap or self._sprite_pixmap.isNull():
            return

        sw = int(self._sprite_pixmap.width() * scale)
        sh = int(self._sprite_pixmap.height() * scale)
        rect = QRect(cx - sw // 2, cy - sh // 2, sw, sh)

        # Фаза А (2.0 - 2.6s): драматичный силуэт с неоновой Crimson-аурой
        if t < 2.6:
            pulse = int(abs(math.sin(t * 16.0)) * 12.0)
            painter.setOpacity(0.50 * master_alpha)
            painter.drawPixmap(rect.adjusted(-10 - pulse, -10 - pulse, 10 + pulse, 10 + pulse), self._sprite_pixmap)
            painter.setOpacity(0.85 * master_alpha)
            painter.drawPixmap(rect, self._sprite_pixmap)
        # Фаза Б (2.6s+): яркий спрайт в полный цвет с мягкой аурой
        else:
            painter.setOpacity(0.40 * master_alpha)
            glow_offset = int(10.0 * math.sin(t * 7.0))
            painter.drawPixmap(rect.adjusted(-glow_offset, -glow_offset, glow_offset, glow_offset), self._sprite_pixmap)
            painter.setOpacity(master_alpha)
            painter.drawPixmap(rect, self._sprite_pixmap)

        # Вывод HUD-баннера реплики с печатной машинкой
        if t >= 2.6:
            chars_count = int((t - 2.6) * 45.0)
            draw_dialogue_cyber_hud(painter, cx, cy + 160, master_alpha, chars_count)
