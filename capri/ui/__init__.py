"""User interface components, menus, and styling package exports."""

from .console_hud import CyberConsoleHud
from .context_menu import (
    ContextMenuBuilder,
    CyberMenu,
    ReminderRangeDialog,
    TrayManager,
    build_pet_context_menu,
    build_tray_context_menu,
)
from .pet_renderer import (
    PetRenderer,
    PetRenderState,
    free_bands,
    least_overlap_point,
    pick_adjacent_position,
    pick_position,
    pick_side_position,
    random_free_point,
)
from .pet_window import CapriWindow
from .shredder_drop_handler import ShredderDropHandler
from .speech import SpeechWindow, show_text
from .theme import (
    APP_STYLE,
    CSS_CYBER_HUD,
    CSS_CYBER_TERMINAL,
    CSS_CYBER_UI,
    FONT_CYBER_HUD,
    FONT_CYBER_TERMINAL,
    FONT_CYBER_UI,
    FONT_FAMILY,
    get_font,
    get_hud_font,
    get_terminal_font,
    get_ui_font,
    init_fonts,
)
from .voice_hud import CyberVoiceHud
from .volume_hud import CyberVolumeHud

__all__ = [
    "APP_STYLE",
    "CSS_CYBER_HUD",
    "CSS_CYBER_TERMINAL",
    "CSS_CYBER_UI",
    "FONT_CYBER_HUD",
    "FONT_CYBER_TERMINAL",
    "FONT_CYBER_UI",
    "FONT_FAMILY",
    "CapriWindow",
    "ContextMenuBuilder",
    "CyberConsoleHud",
    "CyberMenu",
    "CyberVoiceHud",
    "CyberVolumeHud",
    "PetRenderState",
    "PetRenderer",
    "ReminderRangeDialog",
    "ShredderDropHandler",
    "SpeechWindow",
    "TrayManager",
    "build_pet_context_menu",
    "build_tray_context_menu",
    "free_bands",
    "get_font",
    "get_hud_font",
    "get_terminal_font",
    "get_ui_font",
    "init_fonts",
    "least_overlap_point",
    "pick_adjacent_position",
    "pick_position",
    "pick_side_position",
    "random_free_point",
    "show_text",
]
