from gi.repository import Gtk, Adw, Gio, Pango

from ..constants import app_id, rootdir
from ..providers.provider_item import Provider
from ..widgets.model_item import Model
from ..widgets.download_row import DownloadRow

import gettext
_ = gettext.gettext

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences_window.ui")
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "Preferences"

    provider_group = Gtk.Template.Child()
    general_page = Gtk.Template.Child()
    miscellaneous_group = Gtk.Template.Child()
    user_name = Gtk.Template.Child()
    bot_name = Gtk.Template.Child()
    font_button = Gtk.Template.Child()
    font_dialog = Gtk.Template.Child()
    line_height_spin = Gtk.Template.Child()

    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)

        self.parent = parent
        self.settings = parent.settings

        self.app = self.parent.get_application()
        self.win = self.app.get_active_window()

        self.set_transient_for(self.win)

        self.setup()

    def setup(self):
        self.setup_signals()
        self.load_providers()
        self.setup_font_settings()

        self.bot_name.set_text(self.app.bot_name)
        self.user_name.set_text(self.app.user_name)

    def setup_signals(self):
        pass

    def load_providers(self):
        for provider in self.app.providers.values():
            p = Provider(self.app, self, provider)
            self.provider_group.add(p)

    def setup_font_settings(self):
        """폰트 및 줄높이 설정 초기화"""
        # 현재 설정된 폰트 정보 가져오기
        font_family = self.settings.get_string("chat-font-family")
        font_size = self.settings.get_int("chat-font-size")
        line_height = self.settings.get_double("chat-line-height")
        
        # FontDescription 생성
        font_desc = Pango.FontDescription()
        font_desc.set_family(font_family)
        font_desc.set_size(font_size * Pango.SCALE)
        
        # FontDialogButton에 현재 폰트 설정
        self.font_button.set_font_desc(font_desc)
        
        # 줄높이 SpinRow에 현재 값 설정
        self.line_height_spin.set_value(line_height)
        
        # 변경 시 콜백 연결
        self.font_button.connect("notify::font-desc", self.on_font_changed)
        self.line_height_spin.connect("notify::value", self.on_line_height_changed)

    def on_font_changed(self, button, pspec):
        """폰트가 변경되었을 때 호출되는 메소드"""
        font_desc = button.get_font_desc()
        if font_desc:
            # 폰트 패밀리와 크기 추출
            family = font_desc.get_family()
            size = font_desc.get_size() // Pango.SCALE
            
            # GSettings에 저장
            self.settings.set_string("chat-font-family", family)
            self.settings.set_int("chat-font-size", size)
            
            # 메인 윈도우에 폰트 변경 알림
            self.parent.apply_font_settings()
            
            # 성공 토스트 표시
            toast = Adw.Toast()
            toast.set_title(_("Font settings updated"))
            if hasattr(self.parent, 'toast_overlay'):
                self.parent.toast_overlay.add_toast(toast)

    def on_line_height_changed(self, spin_row, pspec):
        """줄높이가 변경되었을 때 호출되는 메소드"""
        line_height = spin_row.get_value()
        
        # GSettings에 저장
        self.settings.set_double("chat-line-height", line_height)
        
        # 메인 윈도우에 변경사항 적용
        self.parent.apply_font_settings()
        
        # 성공 토스트 표시
        toast = Adw.Toast()
        toast.set_title(_("Line height updated"))
        if hasattr(self.parent, 'toast_overlay'):
            self.parent.toast_overlay.add_toast(toast)


    @Gtk.Template.Callback()
    def clear_all_chats_clicked(self, widget, *args):
        dialog = Adw.MessageDialog(
            heading=_("Delete All Threads"),
            body=_("Are you sure you want to delete all threads? This can't be undone!"),
            body_use_markup=True
        )

        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        dialog.connect("response", self.on_delete_response)

        dialog.set_transient_for(self)
        dialog.present()

    def on_delete_response(self, _widget, response):
        if response == "delete":
            self.app.clear_all_chats()

            toast = Adw.Toast()
            toast.set_title(_("All chats cleared!"))
            self.add_toast(toast)

    @Gtk.Template.Callback()
    def on_bot_entry_apply(self, user_data, *args):
        self.app.bot_name = user_data.get_text()

        self.app.load_bot_and_user_name()

    @Gtk.Template.Callback()
    def on_user_entry_apply(self, user_data, *args):
        self.app.user_name = user_data.get_text()

        self.app.load_bot_and_user_name()
    