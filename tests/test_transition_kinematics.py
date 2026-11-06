from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint

from capri.effects.transition_fx import (
    evaluate_bezier,
    evaluate_manhattan_path,
    evaluate_vortex,
)


class TestTransitionKinematics(unittest.TestCase):
    def test_evaluate_bezier_endpoints(self) -> None:
        p0 = QPoint(0, 0)
        p1 = QPoint(50, 100)
        p2 = QPoint(100, 200)

        start = evaluate_bezier(p0, p1, p2, 0.0)
        end = evaluate_bezier(p0, p1, p2, 1.0)
        self.assertEqual(start, p0)
        self.assertEqual(end, p2)

    def test_evaluate_manhattan_path_endpoints(self) -> None:
        p0 = QPoint(10, 20)
        p2 = QPoint(200, 300)

        start = evaluate_manhattan_path(p0, p2, 0.5, 0.0, 0)
        end = evaluate_manhattan_path(p0, p2, 0.5, 1.0, 0)
        self.assertEqual(start, p0)
        self.assertEqual(end, p2)

        start_alt = evaluate_manhattan_path(p0, p2, 0.5, 0.0, 1)
        end_alt = evaluate_manhattan_path(p0, p2, 0.5, 1.0, 1)
        self.assertEqual(start_alt, p0)
        self.assertEqual(end_alt, p2)

    def test_evaluate_vortex_endpoints(self) -> None:
        p0 = QPoint(100, 100)
        p2 = QPoint(400, 500)

        start = evaluate_vortex(p0, p2, 0.0, 2.0, 50.0)
        end = evaluate_vortex(p0, p2, 1.0, 2.0, 50.0)
        self.assertEqual(start, p0)
        self.assertEqual(end, p2)
