"""Tokens visuais compartilhados entre Android, Windows e futuro iOS.

A interface ainda usa Flet, mas as decisões de spacing/radius/tipografia ficam
centralizadas para reduzir divergência entre desktop e Android.
"""
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}
RADIUS = {"sm": 10, "md": 14, "lg": 18, "xl": 24}
TOUCH_TARGET = 48
MOTION_MS = {"fast": 150, "normal": 200, "slow": 250}
BREAKPOINTS = {"phone": 700, "tablet": 900, "compact": 1180}

COLORS = {
    "brand": "#7459FF",
    "brand_2": "#A874FF",
    "cyan": "#23D5F3",
    "navy": "#080F21",
    "surface": "#101A31",
    "surface_alt": "#17243F",
    "brand_soft_dark": "#191847",
    "brand_border_dark": "#4A3D92",
    "success": "#36DFAE",
    "warning": "#FFB020",
    "danger": "#FF6B6B",
}
