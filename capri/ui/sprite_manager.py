"""Управление спрайтами и масштабированием питомца Capri.

Обеспечивает парсинг графических ресурсов из assets/sprites, случайный выбор
спрайтов, масштабирование, кеширование растровых масок и проверку попадания курсора.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBitmap, QImage, QPixmap, QRegion

from ..core.settings import get_config_value, set_config_value

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

ALLOWED_SCALES = (50, 75, 100, 125, 150)


class SpriteManager:
    """Менеджер спрайтов питомца, масштабирования и растровых масок."""

    def __init__(
        self,
        on_pose_changed: Callable[[QPixmap, QImage | None, str], None]
        | None = None,
    ) -> None:
        self._on_pose_changed = on_pose_changed
        self._scale_percent: int = 100
        self._current_sprite_key: str = ""
        self._current_pixmap: QPixmap = QPixmap()
        self._cached_hit_image: QImage | None = None
        self._cached_mask_region: QRegion | None = None

        self._raw_pixmaps: dict[str, QPixmap] = {}
        self._pixmaps: dict[str, QPixmap] = {}
        self._sprite_keys: list[str] = []

        self._load_saved_scale()
        self.load_all_sprites()
        if self._sprite_keys:
            self._current_sprite_key = random.choice(self._sprite_keys)
            self._current_pixmap = self._pixmaps.get(
                self._current_sprite_key, QPixmap()
            )
            self._update_cached_image_and_mask()

    @property
    def scale_percent(self) -> int:
        return self._scale_percent

    @property
    def current_sprite_key(self) -> str:
        return self._current_sprite_key

    @property
    def current_pose(self) -> str:
        return self._current_sprite_key

    @property
    def sprite_keys(self) -> list[str]:
        return list(self._sprite_keys)

    @property
    def sprite_count(self) -> int:
        return len(self._sprite_keys)

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
        w, h = (
            self._cached_hit_image.width(),
            self._cached_hit_image.height(),
        )
        alpha8 = self._cached_hit_image.convertToFormat(
            QImage.Format.Format_Alpha8
        )
        raw_bytes = bytearray(alpha8.constBits()[: alpha8.sizeInBytes()])
        table = bytes([0 if i <= 20 else 255 for i in range(256)])
        thresh_bytes = raw_bytes.translate(table)
        thresh_img = QImage(
            thresh_bytes,
            w,
            h,
            alpha8.bytesPerLine(),
            QImage.Format.Format_Alpha8,
        )
        mask_bitmap = QBitmap.fromImage(
            thresh_img.createMaskFromColor(0, Qt.MaskMode.MaskInColor)
        )
        base_region = QRegion(mask_bitmap)

        dilated_region = QRegion()
        offsets = (-24, -16, -8, 0, 8, 16, 24)
        for dx in offsets:
            for dy in offsets:
                dilated_region = dilated_region.united(
                    base_region.translated(dx, dy)
                )

        self._cached_mask_region = dilated_region

    def set_sprite_scale(self, percent: int) -> bool:

        if percent not in ALLOWED_SCALES or self._scale_percent == percent:
            return False

        self._scale_percent = percent
        set_config_value("appearance.scale", percent)
        for name in list(self._raw_pixmaps.keys()):
            self._apply_scale_for_pose(name)

        if self._current_sprite_key in self._pixmaps:
            self._current_pixmap = self._pixmaps[self._current_sprite_key]
            self._update_cached_image_and_mask()
            if self._on_pose_changed:
                self._on_pose_changed(
                    self._current_pixmap,
                    self._cached_hit_image,
                    self._current_sprite_key,
                )
        return True

    def load_all_sprites(self) -> None:
        self._raw_pixmaps.clear()
        self._pixmaps.clear()
        self._sprite_keys.clear()

        if SPRITES_DIR.is_dir():
            for file in sorted(SPRITES_DIR.iterdir()):
                if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                    key = file.stem
                    self.load_pixmap(key, file)
                    self._sprite_keys.append(key)

        if not self._sprite_keys:
            fallback = QPixmap(420, 420)
            fallback.fill(Qt.GlobalColor.transparent)
            self._raw_pixmaps["default"] = fallback
            self._apply_scale_for_pose("default")
            self._sprite_keys.append("default")

    def load_all_poses(self) -> None:
        self.load_all_sprites()

    def set_random_sprite(self, exclude_current: bool = True) -> bool:
        if not self._sprite_keys:
            return False

        if len(self._sprite_keys) == 1:
            chosen_key = self._sprite_keys[0]
        elif exclude_current and self._current_sprite_key in self._sprite_keys:
            pool = [k for k in self._sprite_keys if k != self._current_sprite_key]
            chosen_key = random.choice(pool)
        else:
            chosen_key = random.choice(self._sprite_keys)

        pixmap = self._pixmaps.get(chosen_key)
        if pixmap is None:
            return False

        changed = chosen_key != self._current_sprite_key
        self._current_sprite_key = chosen_key
        self._current_pixmap = pixmap
        self._update_cached_image_and_mask()

        if self._on_pose_changed:
            self._on_pose_changed(
                self._current_pixmap,
                self._cached_hit_image,
                self._current_sprite_key,
            )
        return changed

    def set_pose(self, pose: str = "") -> bool:
        if pose and pose in self._pixmaps:
            changed = pose != self._current_sprite_key
            self._current_sprite_key = pose
            self._current_pixmap = self._pixmaps[pose]
            self._update_cached_image_and_mask()
            if self._on_pose_changed:
                self._on_pose_changed(
                    self._current_pixmap,
                    self._cached_hit_image,
                    self._current_sprite_key,
                )
            return changed
        return self.set_random_sprite(exclude_current=True)

    def set_pose_image(self, pose_name: str, path: Path) -> bool:
        self.load_pixmap(pose_name, path)
        if pose_name not in self._sprite_keys:
            self._sprite_keys.append(pose_name)
        return self.set_pose(pose_name)

    def is_point_on_sprite(self, pos_x: int, pos_y: int) -> bool:

        img = self._cached_hit_image
        if img is None or img.isNull():
            return True
        if not (0 <= pos_x < img.width() and 0 <= pos_y < img.height()):
            return False
        return img.pixelColor(pos_x, pos_y).alpha() > 20
