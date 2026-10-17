from ui.common import ft
from ui.design import COLORS

VISUAL_STYLES = {
    "original": {"label": "Nex Original", "dark": True, "background": "#080F21", "surface": "#101A31", "surface_alt": "#17243F", "border": "#2B3C68", "accent": "#7459FF"},
    "claro": {"label": "Claro Moderno", "dark": False, "background": "#F4F6FC", "surface": "#FFFFFF", "surface_alt": "#E9EDFA", "border": "#CDD5E9", "accent": "#6650DA"},
    "tech": {"label": "Grafite Tecnológico", "dark": True, "background": "#0C111D", "surface": "#182235", "surface_alt": "#21314A", "border": "#3A4B68", "accent": "#39BFE8"},
}

class ThemeScreen:
    def visual_style(self):
        key = self.preferences.get("visual_style", "original")
        return VISUAL_STYLES.get(key, VISUAL_STYLES["original"])

    def is_dark(self):
        return self.page.theme_mode == ft.ThemeMode.DARK


    def page_color(self):
        if self.preferences.get("visual_style") in VISUAL_STYLES:
            return self.visual_style()["background"]
        return "#111318" if self.is_dark() else "#F7F8FB"


    def surface_color(self):
        if self.preferences.get("visual_style") in VISUAL_STYLES:
            return self.visual_style()["surface"]
        return "#1B1D23" if self.is_dark() else ft.Colors.WHITE


    def surface_alt_color(self):
        if self.preferences.get("visual_style") in VISUAL_STYLES:
            return self.visual_style()["surface_alt"]
        return "#24272F" if self.is_dark() else ft.Colors.GREY_50


    def border_color(self):
        if self.preferences.get("visual_style") in VISUAL_STYLES:
            return self.visual_style()["border"]
        return ft.Colors.GREY_700 if self.is_dark() else ft.Colors.GREY_200


    def muted_color(self):
        return ft.Colors.GREY_400 if self.is_dark() else ft.Colors.GREY_600


    def subtle_color(self):
        return ft.Colors.GREY_500


    def user_bubble_color(self):
        return self.surface_alt_color() if self.is_dark() else ft.Colors.INDIGO_50


    def assistant_bubble_color(self):
        return self.surface_color() if self.is_dark() else ft.Colors.GREY_100


    def warning_surface_color(self):
        return "#332A16" if self.is_dark() else ft.Colors.AMBER_50


    def apply_theme(self):
        self.page.bgcolor = self.page_color()
        # Built-in controls, dialogs, fields and navigation inherit these themes.
        accent = self.visual_style()["accent"] if self.preferences.get("visual_style") in VISUAL_STYLES else COLORS["brand"]
        self.page.theme = ft.Theme(color_scheme_seed=accent)
        self.page.dark_theme = ft.Theme(color_scheme_seed=accent)

    def choose_visual_style(self, key):
        if key not in VISUAL_STYLES:
            raise ValueError("Aparência inválida")
        self.preferences["visual_style"] = key
        self.preferences["dark_mode"] = VISUAL_STYLES[key]["dark"]
        self.save_preferences()
        self.page.theme_mode = ft.ThemeMode.DARK if VISUAL_STYLES[key]["dark"] else ft.ThemeMode.LIGHT
        self.apply_theme()
        self.render()


    def toggle_dark_mode(self, value):
        self.preferences.pop("visual_style", None)
        self.preferences["dark_mode"] = bool(value)
        self.save_preferences()
        self.page.theme_mode = ft.ThemeMode.DARK if value else ft.ThemeMode.LIGHT
        self.apply_theme()
        # Rebuild fixed-color custom cards/graphs with the active palette.
        self.render()
