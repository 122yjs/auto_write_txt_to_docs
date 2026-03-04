import unittest

from src.auto_write_txt_to_docs.ui_helpers import build_center_geometry, center_window


class FakeWindow:
    def __init__(self, width, height, screen_width, screen_height):
        self._width = width
        self._height = height
        self._screen_width = screen_width
        self._screen_height = screen_height
        self.updated = False
        self.geometry_value = None

    def update_idletasks(self):
        self.updated = True

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height

    def winfo_screenwidth(self):
        return self._screen_width

    def winfo_screenheight(self):
        return self._screen_height

    def geometry(self, value):
        self.geometry_value = value


class UiHelpersTests(unittest.TestCase):
    def test_build_center_geometry_returns_expected_value(self):
        geometry = build_center_geometry(550, 400, 1920, 1080)
        self.assertEqual(geometry, "550x400+685+340")

    def test_center_window_updates_and_sets_geometry(self):
        window = FakeWindow(width=900, height=750, screen_width=1920, screen_height=1080)

        geometry = center_window(window)

        self.assertTrue(window.updated)
        self.assertEqual(geometry, "900x750+510+165")
        self.assertEqual(window.geometry_value, geometry)


if __name__ == "__main__":
    unittest.main()
