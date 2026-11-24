"""Shared violet theme for the GPUI examples (light and dark)."""

import gpyui

LIGHT = {
    "background": "#f5f4fa",
    "foreground": "#1c1930",
    "primary": "#7c3aed",
    "primary_foreground": "#ffffff",
    "primary_hover": "#6d28d9",
    "primary_active": "#5b21b6",
    "secondary": "#ede9fe",
    "secondary_foreground": "#4c1d95",
    "muted": "#eeecf6",
    "muted_foreground": "#6e6a85",
    "border": "#e2deef",
    "input": "#dcd7ec",
    "ring": "#8b5cf6",
    "accent": "#ede9fe",
    "accent_foreground": "#4c1d95",
    "danger": "#e11d48",
    "danger_foreground": "#ffffff",
    "success": "#16a34a",
    "warning": "#d97706",
    "info": "#2563eb",
    "selection": "#7c3aed33",
    "caret": "#7c3aed",
    "button": "#ffffff",
    "button_hover": "#f3f0fc",
    "button_active": "#e9e4f9",
    "popover": "#ffffff",
    "sidebar": "#efedf8",
    "switch_checked": "#7c3aed",
    "slider": "#7c3aed",
}

DARK = {
    "background": "#0f0d1a",
    "foreground": "#ece9f8",
    "primary": "#8b5cf6",
    "primary_foreground": "#ffffff",
    "primary_hover": "#7c3aed",
    "primary_active": "#6d28d9",
    "secondary": "#2a2540",
    "secondary_foreground": "#e9e3ff",
    "muted": "#1d1a2e",
    "muted_foreground": "#9a95b3",
    "border": "#2d2943",
    "input": "#36314f",
    "ring": "#a78bfa",
    "accent": "#2a2540",
    "accent_foreground": "#e9e3ff",
    "danger": "#f43f5e",
    "danger_foreground": "#ffffff",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "info": "#60a5fa",
    "selection": "#8b5cf644",
    "caret": "#a78bfa",
    "button": "#1d1a2e",
    "button_hover": "#26223a",
    "button_active": "#2f2a47",
    "popover": "#17142a",
    "sidebar": "#141124",
    "switch_checked": "#8b5cf6",
    "slider": "#8b5cf6",
}

_THEMES = {
    dark: gpyui.Theme(
        "shadcn-zinc",
        mode="dark" if dark else "light",
        colors=DARK if dark else LIGHT,
        radius=8,
        radius_lg=14,
    )
    for dark in (False, True)
}


def theme(dark: bool = False) -> gpyui.Theme:
    """Return the violet example theme in dark or light mode."""
    return _THEMES[bool(dark)]
