from ui.common import ft
from ui.design import COLORS

class ThemeScreen:
    def is_dark(self):
        return self.page.theme_mode == ft.ThemeMode.DARK


    def page_color(self):
        return "#111318" if self.is_dark() else "#F7F8FB"


    def surface_color(self):
        return "#1B1D23" if self.is_dark() else ft.Colors.WHITE


    def surface_alt_color(self):
        return "#24272F" if self.is_dark() else ft.Colors.GREY_50


    def border_color(self):
        return ft.Colors.GREY_700 if self.is_dark() else ft.Colors.GREY_200


    def muted_color(self):
        return ft.Colors.GREY_400 if self.is_dark() else ft.Colors.GREY_600


    def subtle_color(self):
        return ft.Colors.GREY_500


    def user_bubble_color(self):
        return "#252A44" if self.is_dark() else ft.Colors.INDIGO_50


    def assistant_bubble_color(self):
        return "#252830" if self.is_dark() else ft.Colors.GREY_100


    def warning_surface_color(self):
        return "#332A16" if self.is_dark() else ft.Colors.AMBER_50


    def apply_theme(self):
        self.page.bgcolor = self.page_color()
        # Built-in controls, dialogs, fields and navigation inherit these themes.
        self.page.theme = ft.Theme(color_scheme_seed=COLORS["brand"])
        self.page.dark_theme = ft.Theme(color_scheme_seed=COLORS["brand_2"])


    def toggle_dark_mode(self, value):
        self.preferences["dark_mode"] = bool(value)
        self.save_preferences()
        self.page.theme_mode = ft.ThemeMode.DARK if value else ft.ThemeMode.LIGHT
        self.apply_theme()
        # Rebuild fixed-color custom cards/graphs with the active palette.
        self.render()


