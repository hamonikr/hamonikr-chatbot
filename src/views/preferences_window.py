from gi.repository import Gtk, Adw, Gio, Pango, GLib
import json
import os

try:
    from ..constants import app_id, rootdir
    from ..providers.provider_item import Provider
    from ..widgets.model_item import Model
    from ..widgets.download_row import DownloadRow
except ImportError:
    from constants import app_id, rootdir
    from providers.provider_item import Provider
    from widgets.model_item import Model
    from widgets.download_row import DownloadRow

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
    webkit_rendering_switch = Gtk.Template.Child()
    
    # System Prompt UI elements
    system_prompt_text = Gtk.Template.Child()
    clear_system_prompt_btn = Gtk.Template.Child()
    apply_system_prompt_btn = Gtk.Template.Child()
    

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
        self.setup_font_settings()
        self.setup_webkit_settings()
        self.setup_system_prompt()

        self.bot_name.set_text(self.app.bot_name)
        self.user_name.set_text(self.app.user_name)
        
        # 프로바이더 로딩을 지연시켜 초기 표시 속도 향상
        self.providers_loaded = False
        self._add_loading_indicator()
        GLib.idle_add(self.load_providers_async)

    def setup_signals(self):
        pass
    
    def _add_loading_indicator(self):
        """프로바이더 로딩 중 표시할 인디케이터 추가"""
        # 로딩 인디케이터 행 생성
        self.loading_row = Adw.ActionRow()
        self.loading_row.set_title(_("Loading providers..."))
        self.loading_row.set_subtitle(_("Please wait while providers are being loaded"))
        
        # 스피너 추가
        self.loading_spinner = Gtk.Spinner()
        self.loading_spinner.set_spinning(True)
        self.loading_spinner.set_valign(Gtk.Align.CENTER)
        self.loading_row.add_suffix(self.loading_spinner)
        
        # 프로바이더 그룹에 추가
        self.provider_group.add(self.loading_row)
    
    def _remove_loading_indicator(self):
        """로딩 완료 시 인디케이터 제거"""
        if hasattr(self, 'loading_row'):
            self.loading_spinner.set_spinning(False)
            self.provider_group.remove(self.loading_row)
            del self.loading_row
            del self.loading_spinner

    def load_providers_async(self):
        """프로바이더를 비동기적으로 로드하여 초기 표시 속도 향상"""
        if self.providers_loaded:
            return False
            
        # 한 번에 모든 프로바이더를 로드하는 대신 배치로 처리
        providers = list(self.app.providers.values())
        
        def load_batch(start_index):
            """프로바이더를 배치 단위로 로드"""
            batch_size = 3  # 한 번에 3개씩 로드
            end_index = min(start_index + batch_size, len(providers))
            
            for i in range(start_index, end_index):
                provider = providers[i]
                try:
                    p = Provider(self.app, self, provider)
                    self.provider_group.add(p)
                except Exception as e:
                    print(f"Failed to load provider {provider.name}: {e}")
            
            # 로딩 상태 업데이트
            if hasattr(self, 'loading_row'):
                progress = f"{end_index}/{len(providers)}"
                self.loading_row.set_subtitle(_("Loading providers... ({})").format(progress))
            
            # 더 로드할 프로바이더가 있으면 다음 배치를 스케줄
            if end_index < len(providers):
                GLib.idle_add(lambda: load_batch(end_index))
            else:
                self.providers_loaded = True
                # 로딩 완료 시 인디케이터 제거
                self._remove_loading_indicator()
            
            return False
        
        # 첫 번째 배치 시작
        load_batch(0)
        return False
    
    def load_providers(self):
        """원래 메서드 (호환성 유지)"""
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

    def setup_webkit_settings(self):
        """WebKit 렌더링 설정 초기화"""
        # 현재 설정 값 가져오기
        webkit_enabled = self.settings.get_boolean("use-webkit-rendering")
        
        # 스위치에 현재 값 설정
        self.webkit_rendering_switch.set_active(webkit_enabled)
        
        # 변경 시 콜백 연결
        self.webkit_rendering_switch.connect("notify::active", self.on_webkit_rendering_changed)

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

    def on_webkit_rendering_changed(self, switch_row, pspec):
        """WebKit 렌더링 설정이 변경되었을 때 호출되는 메소드"""
        webkit_enabled = switch_row.get_active()
        
        # GSettings에 저장
        self.settings.set_boolean("use-webkit-rendering", webkit_enabled)
        
        # 성공 토스트 표시
        toast = Adw.Toast()
        if webkit_enabled:
            toast.set_title(_("Enhanced markdown rendering enabled"))
        else:
            toast.set_title(_("Enhanced markdown rendering disabled"))
        
        if hasattr(self.parent, 'toast_overlay'):
            self.parent.toast_overlay.add_toast(toast)

    def setup_system_prompt(self):
        """시스템 프롬프트 설정 초기화"""
        # 저장된 시스템 프롬프트 불러오기
        saved_prompt = self.settings.get_string("system-prompt")
        if saved_prompt:
            buffer = self.system_prompt_text.get_buffer()
            buffer.set_text(saved_prompt)
    
    @Gtk.Template.Callback()
    def on_clear_system_prompt(self, *args):
        """시스템 프롬프트 지우기"""
        buffer = self.system_prompt_text.get_buffer()
        buffer.set_text("")
        
        # 설정에서도 제거
        self.settings.set_string("system-prompt", "")
        
        # 앱에서도 제거
        if hasattr(self.app, 'system_prompt'):
            self.app.system_prompt = ""
        
        toast = Adw.Toast()
        toast.set_title(_("System prompt cleared"))
        if hasattr(self.parent, 'toast_overlay'):
            self.parent.toast_overlay.add_toast(toast)
    
    @Gtk.Template.Callback()
    def on_apply_system_prompt(self, *args):
        """시스템 프롬프트 적용"""
        buffer = self.system_prompt_text.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        text = buffer.get_text(start_iter, end_iter, True)
        
        # 설정에 저장
        self.settings.set_string("system-prompt", text)
        
        # 앱에 적용
        if hasattr(self.app, 'system_prompt'):
            self.app.system_prompt = text
        else:
            self.app.system_prompt = text
        
        toast = Adw.Toast()
        toast.set_title(_("System prompt applied"))
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
    