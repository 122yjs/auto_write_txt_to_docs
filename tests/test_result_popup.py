import unittest

from src.auto_write_txt_to_docs.result_popup import (
    FAILURE_POPUP_DURATION_MS,
    SUCCESS_POPUP_DURATION_MS,
    ResultPopupPresenter,
)


class FakeRoot:
    def __init__(self):
        self.after_calls = []
        self.after_cancel_calls = []
        self.handle = 100

    def winfo_exists(self):
        return True

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def after(self, delay_ms, callback):
        after_id = f"after-{len(self.after_calls) + 1}"
        self.after_calls.append((after_id, delay_ms, callback))
        return after_id

    def after_cancel(self, after_id):
        self.after_cancel_calls.append(after_id)

    def winfo_id(self):
        return self.handle

    def _get_window_scaling(self):
        return 1.0


class FakeWidget:
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.__class__.instances.append(self)

    def pack(self, *args, **kwargs):
        self.pack_args = args
        self.pack_kwargs = kwargs


class FakeToplevel:
    def __init__(self, root):
        self.root = root
        self.destroyed = False
        self.geometry_value = None
        self.title_value = None
        self.width = 260
        self.height = 128
        self.reqwidth = 260
        self.reqheight = 128
        self.handle = 200

    def title(self, value):
        self.title_value = value

    def resizable(self, *_args):
        pass

    def attributes(self, *_args):
        pass

    def overrideredirect(self, *_args):
        pass

    def configure(self, **_kwargs):
        pass

    def update_idletasks(self):
        pass

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_reqwidth(self):
        return self.reqwidth

    def winfo_reqheight(self):
        return self.reqheight

    def geometry(self, value):
        self.geometry_value = value

    def deiconify(self):
        pass

    def lift(self):
        pass

    def after(self, _delay_ms, callback):
        callback()
        return "popup-after-1"

    def destroy(self):
        self.destroyed = True

    def winfo_exists(self):
        return not self.destroyed

    def winfo_id(self):
        return self.handle


class FakeButton(FakeWidget):
    instances = []


class FakeCtkModule:
    CTkToplevel = FakeToplevel
    CTkFrame = FakeWidget
    CTkLabel = FakeWidget
    CTkButton = FakeButton

    @staticmethod
    def CTkFont(**kwargs):
        return kwargs


class ResultPopupPresenterTests(unittest.TestCase):
    def setUp(self):
        FakeWidget.instances = []
        FakeButton.instances = []

    def test_show_replaces_existing_popup_and_resets_timer(self):
        root = FakeRoot()
        presenter = ResultPopupPresenter(root, ctk_module=FakeCtkModule)
        presenter._get_windows_work_area = lambda _popup_window: (0, 0, 1920, 1040)

        first_result = presenter.show("첫 알림", "첫 줄\n둘째 줄", "success")
        first_popup = presenter.popup_window
        first_after_id = presenter.close_after_id

        second_result = presenter.show("둘째 알림", "하나\n둘\n셋\n넷", "failure")

        self.assertTrue(first_result)
        self.assertTrue(second_result)
        self.assertTrue(first_popup.destroyed)
        self.assertEqual(root.after_cancel_calls, [first_after_id])
        self.assertEqual(root.after_calls[0][1], SUCCESS_POPUP_DURATION_MS)
        self.assertEqual(root.after_calls[1][1], FAILURE_POPUP_DURATION_MS)
        self.assertEqual(presenter.last_payload["level"], "failure")
        self.assertEqual(presenter.last_payload["message"], "하나\n둘\n셋  외 1줄")
        self.assertNotEqual(presenter.popup_window, first_popup)
        self.assertEqual(presenter.popup_window.title_value, "둘째 알림")
        self.assertEqual(presenter.popup_window.geometry_value, "260x128+1648+900")

    def test_show_uses_requested_width_for_right_edge_alignment(self):
        root = FakeRoot()
        presenter = ResultPopupPresenter(root, ctk_module=FakeCtkModule)
        presenter._get_windows_work_area = lambda _popup_window: (0, 0, 1920, 1040)

        presenter.show("폭 테스트", "본문", "success")
        presenter.popup_window.reqwidth = 420
        presenter._place_popup(presenter.popup_window)

        self.assertEqual(presenter.popup_window.geometry_value, "420x128+1488+900")

    def test_show_uses_close_button_command(self):
        root = FakeRoot()
        presenter = ResultPopupPresenter(root, ctk_module=FakeCtkModule)
        presenter._get_windows_work_area = lambda _popup_window: (0, 0, 1920, 1040)

        presenter.show("닫기 테스트", "본문", "success")

        close_button = FakeButton.instances[-1]
        close_button.kwargs["command"]()

        self.assertTrue(presenter.popup_window is None)
        self.assertTrue(root.after_cancel_calls)

    def test_close_safely_handles_missing_popup(self):
        root = FakeRoot()
        presenter = ResultPopupPresenter(root, ctk_module=FakeCtkModule)

        presenter.close()

        self.assertEqual(root.after_cancel_calls, [])
        self.assertIsNone(presenter.popup_window)
        self.assertIsNone(presenter.close_after_id)

    def test_falls_back_to_screen_bounds_when_windows_work_area_is_unavailable(self):
        root = FakeRoot()
        presenter = ResultPopupPresenter(root, ctk_module=FakeCtkModule)
        presenter._get_windows_work_area = lambda _popup_window: None

        presenter.show("기본 위치", "본문", "success")

        self.assertEqual(presenter.popup_window.geometry_value, "260x128+1648+940")


if __name__ == "__main__":
    unittest.main()
