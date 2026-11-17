"""Тесты нового генератора векторной молнии в стиле Studio Trigger (Issue #79)."""

from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from capri.effects.transition_fx import CyberVectorBolt


class TestCyberVectorBolt(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if QApplication.instance() is None:
            cls._app = QApplication([])
        else:
            cls._app = QApplication.instance()

    def test_cyber_vector_bolt_initialization_and_polygon(self) -> None:
        p1 = QPoint(100, 100)
        p2 = QPoint(400, 500)
        bolt = CyberVectorBolt(p1, p2, base_width=18.0, tip_width=2.0)

        self.assertGreaterEqual(len(bolt.spine_points), 3)
        self.assertGreater(bolt.polygon.count(), 4)
        # Проверка, что первая и последняя точки хребта соответствуют стартам/финишам
        self.assertAlmostEqual(bolt.spine_points[0].x(), 100.0, delta=2.0)
        self.assertAlmostEqual(bolt.spine_points[0].y(), 100.0, delta=2.0)
        self.assertAlmostEqual(bolt.spine_points[-1].x(), 400.0, delta=2.0)
        self.assertAlmostEqual(bolt.spine_points[-1].y(), 500.0, delta=2.0)

    def test_cyber_vector_bolt_jitter(self) -> None:
        bolt = CyberVectorBolt(QPoint(50, 50), QPoint(200, 200))
        pts_before = [QPointF(p) for p in bolt.spine_points]
        bolt.jitter(force=True)
        pts_after = [QPointF(p) for p in bolt.spine_points]
        # Изломы должны перегенерироваться
        self.assertNotEqual([p.toPoint() for p in pts_before], [p.toPoint() for p in pts_after])

    def test_cyber_vector_bolt_draw_renders_without_crash(self) -> None:
        img = QImage(600, 600, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            bolt = CyberVectorBolt(QPoint(50, 50), QPoint(500, 450))
            bolt.draw(painter, progress=0.5)
            bolt.draw(painter, progress=1.0)
        finally:
            painter.end()

    def test_cyber_trigger_crosshair_draw(self) -> None:
        from capri.effects.transition_painters import CyberTriggerCrosshair

        img = QImage(200, 200, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        try:
            CyberTriggerCrosshair.draw(painter, QPoint(100, 100), progress=1.0, tension=0.5, rotation=1.2)
        finally:
            painter.end()

    def test_lightning_tether_overlay_lifecycle(self) -> None:
        from capri.effects.lightning_tether import LightningTetherOverlay
        overlay = LightningTetherOverlay()
        overlay.activate(QPoint(100, 100), QPoint(300, 300))
        self.assertGreater(len(overlay._bolts), 0)
        overlay.update_target(QPoint(350, 400))
        self.assertGreater(len(overlay._bolts), 0)
        overlay.deactivate()
        self.assertEqual(len(overlay._bolts), 0)
        overlay.close()


if __name__ == "__main__":
    unittest.main()
