from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QBitmap, QImage, QPixmap, QRegion

from ..core.settings import get_config_value, set_config_value

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
VAR_DIR = ASSETS_DIR / "var"
IDLE_DIR = VAR_DIR / "idle"
OTHER_DIR = VAR_DIR / "other"
THINKING_DIR = VAR_DIR / "thinking"

ALLOWED_SCALES = (50, 75, 100, 125, 150)

class SpriteManager:
    

    def __init__(self, on_pose_changed: Callable[[QPixmap, QImage, str], None] | None = None) -> None:
        self._on_pose_changed = on_pose_changed
        self._scale_percent: int = 100
        self._current_pose: str = "idle"
        self._current_pixmap: QPixmap = QPixmap()
        self._cached_hit_image: QImage | None = None
        self._cached_mask_region: QRegion | None = None

        self._raw_pixmaps: dict[str, QPixmap] = {}
        self._pixmaps: dict[str, QPixmap] = {}
        self._pose_variants: dict[str, list[str]] = {
            "idle": [],
            "other": [],
            "thinking": [],
        }

        self._load_saved_scale()
        self.load_all_poses()

    @property
    def scale_percent(self) -> int:
        return self._scale_percent

    @property
    def current_pose(self) -> str:
        return self._current_pose

    @property
    def current_pixmap(self) -> QPixmap:
        return self._current_pixmap

    @property
    def cached_hit_image(self) -> QImage | None:
        return self._cached_hit_image

    @property
    def cached_mask_region(self) -> QRegion | None:
        return self._cached_mask_region

    def _load_saved_scale(self) -> None:
        saved_scale = get_config_value("appearance.scale", 100)
        try:
            scale_val = int(saved_scale)
            if scale_val in ALLOWED_SCALES:
                self._scale_percent = scale_val
        except (ValueError, TypeError):
            self._scale_percent = 100

    def load_pixmap(self, name: str, path: Path) -> QPixmap:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            pixmap = QPixmap(420, 420)
        self._raw_pixmaps[name] = pixmap
        return self._apply_scale_for_pose(name)

    def _apply_scale_for_pose(self, name: str) -> QPixmap:
        raw = self._raw_pixmaps.get(name)
        if raw is None or raw.isNull():
            raw = QPixmap(420, 420)
            self._raw_pixmaps[name] = raw

        base_width = max(1, int(raw.width() / 1.5))
        base_height = max(1, int(raw.height() / 1.5))
        scale_factor = self._scale_percent / 100.0
        target_width = max(1, int(base_width * scale_factor))
        target_height = max(1, int(base_height * scale_factor))

        scaled = raw.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._pixmaps[name] = scaled
        return scaled

    def _update_cached_image_and_mask(self) -> None:
        
        if self._current_pixmap.isNull():
            self._cached_hit_image = None
            self._cached_mask_region = None
            return

        self._cached_hit_image = self._current_pixmap.toImage()
        w, h = self._cached_hit_image.width(), self._cached_hit_image.height()
        alpha8 = self._cached_hit_image.convertToFormat(QImage.Format.Format_Alpha8)
        raw_bytes = bytearray(alpha8.constBits()[:alpha8.sizeInBytes()])
        table = bytes([0 if i <= 20 else 255 for i in range(256)])
        thresh_bytes = raw_bytes.translate(table)
        thresh_img = QImage(thresh_bytes, w, h, alpha8.bytesPerLine(), QImage.Format.Format_Alpha8)
        mask_bitmap = QBitmap.fromImage(thresh_img.createMaskFromColor(0, Qt.MaskMode.MaskInColor))
        self._cached_mask_region = QRegion(mask_bitmap)

    def set_sprite_scale(self, percent: int) -> bool:
        
        if percent not in ALLOWED_SCALES or self._scale_percent == percent:
            return False

        self._scale_percent = percent
        set_config_value("appearance.scale", percent)
        for name in list(self._raw_pixmaps.keys()):
            self._apply_scale_for_pose(name)

        if self._current_pose in self._pixmaps:
            self._current_pixmap = self._pixmaps[self._current_pose]
            self._update_cached_image_and_mask()
            if self._on_pose_changed:
                self._on_pose_changed(self._current_pixmap, self._cached_hit_image, self._current_pose)
        return True

    def load_all_poses(self) -> None:
        pose_dirs = {
            "idle": IDLE_DIR,
            "other": OTHER_DIR,
            "thinking": THINKING_DIR,
        }
        self._pose_variants = {
            "idle": [],
            "other": [],
            "thinking": [],
        }

        for pose_name, pose_dir in pose_dirs.items():
            if pose_dir.is_dir():
                for file in sorted(pose_dir.glob("*.png")):
                    variant_key = f"{pose_name}:{file.stem}"
                    self.load_pixmap(variant_key, file)
                    self._pose_variants[pose_name].append(variant_key)

        self._pose_variants["sit"] = self._pose_variants["idle"]
        self._pose_variants["stay"] = self._pose_variants["thinking"]
        self._pose_variants["crouch"] = self._pose_variants["other"]

        for category in ("idle", "other", "thinking", "sit", "stay", "crouch"):
            variants = self._pose_variants.get(category)
            if variants:
                first_variant = variants[0]
                self._raw_pixmaps[category] = self._raw_pixmaps[first_variant]
                self._pixmaps[category] = self._pixmaps[first_variant]

        if not self._pixmaps:
            fallback = QPixmap(420, 420)
            fallback.fill(Qt.GlobalColor.transparent)
            self._raw_pixmaps["sit"] = fallback
            self._apply_scale_for_pose("sit")

    def set_pose(self, pose: str) -> bool:
        
        canonical_pose = {
            "sit": "idle",
            "crouch": "other",
            "stay": "thinking",
        }.get(pose, pose)

        variants = self._pose_variants.get(canonical_pose) or self._pose_variants.get(pose)
        if variants:
            chosen_key = random.choice(variants)
            chosen_pixmap = self._pixmaps.get(chosen_key)
        else:
            chosen_key = pose
            chosen_pixmap = self._pixmaps.get(pose)

        if chosen_pixmap is not None:
            old_pose = self._current_pose
            self._current_pose = canonical_pose
            self._current_pixmap = chosen_pixmap
            self._update_cached_image_and_mask()
            if self._on_pose_changed:
                self._on_pose_changed(self._current_pixmap, self._cached_hit_image, self._current_pose)
            return old_pose != canonical_pose
        return False

    def set_pose_image(self, pose_name: str, path: Path) -> bool:
        self.load_pixmap(pose_name, path)
        return self.set_pose(pose_name)

    def is_point_on_sprite(self, pos_x: int, pos_y: int) -> bool:
        
        img = self._cached_hit_image
        if img is None or img.isNull():
            return True
        if not (0 <= pos_x < img.width() and 0 <= pos_y < img.height()):
            return False
        return img.pixelColor(pos_x, pos_y).alpha() > 20
