"""Tokens visuais do NexGrana 0.19.

A interface ainda usa Flet, mas as decisões de spacing/radius/tipografia ficam
centralizadas para reduzir divergência entre desktop e Android.
"""
SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}
RADIUS = {"sm": 10, "md": 14, "lg": 18, "xl": 24}
TOUCH_TARGET = 48
MOTION_MS = {"fast": 150, "normal": 200, "slow": 250}
BREAKPOINTS = {"phone": 700, "tablet": 900, "compact": 1180}

COLORS = {
    "brand": "#6D63FF",
    "brand_2": "#8B7CFF",
    "brand_soft_dark": "#17192B",
    "brand_border_dark": "#393266",
    "success": "#55E6A5",
    "warning": "#FFB020",
    "danger": "#FF6B6B",
}
