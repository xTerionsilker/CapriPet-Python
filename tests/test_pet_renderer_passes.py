from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication

from capri.ui.pet_renderer import PetRenderState
from capri.ui.renderers.hud_telemetry import HudTelemetryPainter


class TestHudTelemetryPainter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_determine_tag_name(self) -> None:
        state = PetRenderState()
        state.is_consuming = True
        self.assertEqual(
            HudTelemetryPainter.get_telemetry_tag(state),
            "[CONSUME//BLACKWALL]",
        )

        state.is_consuming = False
        state.is_target_acquired = True
        self.assertEqual(
            HudTelemetryPainter.get_telemetry_tag(state),
            "[CONSUME_TARGET_ACQUIRED]",
        )

        state.is_target_acquired = False
        state.is_dragging = True
        self.assertEqual(
            HudTelemetryPainter.get_telemetry_tag(state),
            "[DRAG//RELOCATE]",
        )

    def test_draw_telemetry_invokes_painter(self) -> None:
        mock_painter = MagicMock(spec=QPainter)
        state = PetRenderState()
        state.is_speaking = True
        HudTelemetryPainter.draw_telemetry(mock_painter, 128, 128, severity=0.5, state=state)
        mock_painter.fillRect.assert_called_once()
        mock_painter.drawText.assert_called_once()
