# window.py
#
# Copyright 2023
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime
import locale 
import io 
import base64
import re

from gi.repository import Gtk, Gio, Adw, GLib, Gdk
try:
    from builtins import _  # provided by gettext.install in launcher
except Exception:
    from gettext import gettext as _  # fallback when running out of tree
from babel.dates import format_date, format_datetime, format_time

from ..constants import app_id, build_type, rootdir
from ..widgets.thread_item import ThreadItem
from ..widgets.item import Item
from ..threading import KillableThread
from .export_dialog import ExportDialog

class CustomEntry(Gtk.TextView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_css_name("entry")
        # 키 컨트롤러: Enter=전송, Ctrl/Shift+Enter=줄바꿈
        keyc = Gtk.EventControllerKey.new()
        keyc.connect("key-pressed", self._on_key_pressed)
        keyc.connect("key-released", self._on_key_released)
        self.add_controller(keyc)

        # 전송 지연 상태 관리 (IME 커밋을 기다리기 위함)
        self._send_pending = False
        self._send_timeout_id = 0
        self._buffer_insert_handler = 0
        
        # 공통: Enter 키 집합
        self._enter_keys = (
            getattr(Gdk, "KEY_Return", 0),
            getattr(Gdk, "KEY_KP_Enter", 0),
            getattr(Gdk, "KEY_ISO_Enter", 0),
            getattr(Gdk, "KEY_3270_Enter", 0),
        )

    def _attach_send_hooks(self):
        if self._send_pending:
            return
        self._send_pending = True
        buf = self.get_buffer()

        # IME 커밋으로 실제 텍스트가 삽입되는 순간을 대기
        def on_insert_text(_buf, _iter, _text, _length):
            if not self._send_pending:
                return
            self._clear_send_hooks()
            win = self.get_ancestor(Adw.ApplicationWindow)
            if win and hasattr(win, "on_ask"):
                GLib.idle_add(win.on_ask)

        # one-shot 연결
        self._buffer_insert_handler = buf.connect("insert-text", on_insert_text)

        # 폴백 타이머 (120ms)
        win = self.get_ancestor(Adw.ApplicationWindow)
        self._send_timeout_id = GLib.timeout_add(120, self._send_fallback, win)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        # IME가 먼저 처리하도록 기본적으로 FALSE 반환
        # 단, Enter(키패드 포함)이고 Ctrl/Shift가 아닐 때는 커밋 훅을 선제적으로 심어 신뢰성 보장
        if keyval in self._enter_keys:
            if not (state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK)):
                self._attach_send_hooks()
        return False

    def _on_key_released(self, controller, keyval, keycode, state):
        # Shift/Ctrl+Enter는 줄바꿈 유지
        if keyval in self._enter_keys:
            if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK):
                return False
            # 일반 Enter: 만약 pressed 단계에서 훅을 못 심었으면 여기서 보강
            if not self._send_pending:
                self._attach_send_hooks()

                # 이벤트는 소비하지 않음 → TextView가 개행을 추가하지만 곧바로 on_ask에서 버퍼를 비움
                return False
        return False

    def _send_fallback(self, win):
        if self._send_pending and win and hasattr(win, "on_ask"):
            self._clear_send_hooks()
            win.on_ask()
        return False

    def _clear_send_hooks(self):
        self._send_pending = False
        if self._buffer_insert_handler:
            try:
                self.get_buffer().disconnect(self._buffer_insert_handler)
            except Exception:
                pass
            self._buffer_insert_handler = 0
        if self._send_timeout_id:
            try:
                GLib.source_remove(self._send_timeout_id)
            except Exception:
                pass
            self._send_timeout_id = 0

@Gtk.Template(resource_path=f'{rootdir}/ui/window.ui')
class BavarderWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'BavarderWindow'

    split_view = Gtk.Template.Child()
    threads_list = Gtk.Template.Child()
    title = Gtk.Template.Child()
    main_list = Gtk.Template.Child()
    status_no_chat = Gtk.Template.Child()
    status_no_chat_thread = Gtk.Template.Child()
    status_no_thread = Gtk.Template.Child()
    status_no_thread_main = Gtk.Template.Child()
    status_no_internet = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    provider_selector_button = Gtk.Template.Child()
    banner = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    thread_stack = Gtk.Template.Child()
    main = Gtk.Template.Child()
    scroll_down_button = Gtk.Template.Child()

    threads = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app = Gtk.Application.get_default()
        self.settings = Gio.Settings(schema_id=app_id)

        CustomEntry.set_css_name("entry")
        self.message_entry = CustomEntry()
        self.message_entry.set_hexpand(True)
        self.message_entry.set_accepts_tab(False)
        self.message_entry.set_top_margin(7)
        self.message_entry.set_bottom_margin(7)
        self.message_entry.set_margin_start(5)
        self.message_entry.set_margin_end(5)
        self.message_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        self.message_entry.add_css_class("chat-entry")

        self.scrolled_window.set_child(self.message_entry)
        self.load_threads()

        # 로컬/클라우드 모드 토글 제거

        self.create_action("cancel", self.cancel, ["<primary>Escape"])
        self.create_action("clear_all", self.on_clear_all)
        self.create_action("export", self.on_export, ["<primary>e"])

        self.settings.bind(
            "width", self, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "height", self, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "is-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT
        )
        self.settings.bind(
            "is-fullscreen", self, "fullscreened", Gio.SettingsBindFlags.DEFAULT
        )

        self.message_entry.grab_focus()

        self.main.connect("edge-reached", self.on_edge_reached)
        self.main.connect("edge-overshot", self.on_edge_reached)

    @property
    def chat(self):
        try:
            return self.threads_list.get_selected_row().get_child().chat
        except AttributeError: # create a new chat
            #self.on_new_chat_action()
            return {}
        

    @property
    def content(self):
        try:
            return self.chat["content"]
        except KeyError: # no content
            return []

    def load_threads(self):
        self.threads_list.remove_all()
        if self.app.data["chats"]:
            self.thread_stack.set_visible_child(self.threads_list)
            self.stack.set_visible_child(self.main)
            for chat in self.app.data["chats"]:
                thread = ThreadItem(self, chat)
                self.threads_list.append(thread)
                self.threads.append(thread)

                try:
                    if not chat["content"]:
                        self.stack.set_visible_child(self.status_no_chat)
                except KeyError:
                    self.stack.set_visible_child(self.status_no_chat)
            self.stack.set_visible_child(self.status_no_thread_main)
        else:
            if self.props.default_width < 500:
                self.thread_stack.set_visible_child(self.status_no_thread)
                self.stack.set_visible_child(self.status_no_chat)
            else:
                self.stack.set_visible_child(self.status_no_thread_main)
                self.thread_stack.set_visible_child(self.status_no_chat_thread)

    @Gtk.Template.Callback()
    def mobile_mode_apply(self, *args):
        if not self.app.data["chats"]:
            self.thread_stack.set_visible_child(self.status_no_thread)
            self.stack.set_visible_child(self.status_no_chat)

    @Gtk.Template.Callback()
    def mobile_mode_unapply(self, *args):
        if not self.app.data["chats"]:
            self.stack.set_visible_child(self.status_no_thread_main)
            self.thread_stack.set_visible_child(self.status_no_chat_thread)

    def do_size_allocate(self, width, height, baseline):
        try:
            self.has_been_allocated
        except Exception:
            self.has_been_allocated = True
            self.load_threads()

        Adw.ApplicationWindow.do_size_allocate(self, width, height, baseline)

    @Gtk.Template.Callback()
    def threads_row_activated_cb(self, *args):
        self.split_view.set_show_content(True)

        try:
            self.title.set_title(self.chat["title"])
        except KeyError:
            self.title.set_title(_("New chat"))

        if self.content:
            self.stack.set_visible_child(self.main)
            self.main_list.remove_all()
            i = 0
            for item in self.content:
                i += 1
                item = Item(self, self.chat, item)
                self.main_list.append(item)
            
            for i in range(i):
                row = self.main_list.get_row_at_index(i)
                row.set_selectable(False)
                row.set_activatable(False)
        else:
            self.stack.set_visible_child(self.status_no_chat)

    @Gtk.Template.Callback()
    def on_new_chat_action(self, *args):
        # 새 채팅 생성
        self.app.on_new_chat_action(None, None)
        # 방금 생성된 마지막 스레드를 선택/활성화하여 중복 생성 방지
        try:
            last_index = len(self.app.data["chats"]) - 1
            if last_index >= 0:
                row = self.threads_list.get_row_at_index(last_index)
                if row:
                    self.threads_list.select_row(row)
                    self.threads_row_activated_cb()
                    try:
                        self.split_view.set_show_content(True)
                    except Exception:
                        pass
                    try:
                        self.message_entry.grab_focus()
                    except Exception:
                        pass
        except Exception:
            pass

    @Gtk.Template.Callback()
    def scroll_down(self, *args):
        code = self.main.emit("scroll-child", Gtk.ScrollType.END, False)

    def on_edge_reached(self, widget, edge):
        if edge == Gtk.PositionType.BOTTOM:
            self.scroll_down_button.set_visible(False)
        else:
            self.scroll_down_button.set_visible(True)

    def on_clear_all(self, *args):
        if self.app.data["chats"]:
            dialog = Adw.MessageDialog(
                heading=_("Delete All Chats"),
                body=_("Are you sure you want to delete all chats in this thread? This can't be undone!"),
                body_use_markup=True
            )

            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("delete", _("Delete"))
            dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")

            dialog.connect("response", self.on_clear_all_response)

            dialog.set_transient_for(self)
            dialog.present()
        else:
            toast = Adw.Toast()
            toast.set_title(_("Nothing to clear!"))
            self.toast_overlay.add_toast(toast)


    def on_clear_all_response(self, _widget, response):
        if response == "delete":
            toast = Adw.Toast()
            if self.app.data["chats"]:
                if self.content:
                    self.stack.set_visible_child(self.main)
                    self.main_list.remove_all()
                    del self.chat["content"]
                self.stack.set_visible_child(self.status_no_chat)

                toast.set_title(_("All chats cleared!"))
            else:
                toast.set_title(_("Nothing to clear!"))
            self.toast_overlay.add_toast(toast)

    def on_export(self, *args):
        if self.content:
            dialog = ExportDialog(self, self.chat["content"])
            dialog.set_transient_for(self)
            dialog.present()
        else:
            toast = Adw.Toast()
            toast.set_title(_("Nothing to export!"))
            self.toast_overlay.add_toast(toast)

    # PROVIDER - ONLINE
    def load_provider_selector(self):
        provider_menu = Gio.Menu()

        # Section: Providers
        section_providers = Gio.Menu()
        for provider in self.app.providers.values():
            if provider.enabled:
                item_provider = Gio.MenuItem.new(provider.name, None)
                item_provider.set_action_and_target_value(
                    "app.set_provider",
                    GLib.Variant("s", provider.slug)
                )
                section_providers.append_item(item_provider)
        if self.app.providers:
            provider_menu.append_section(_("Providers"), section_providers)

        # Section: Current provider's models (if supported)
        try:
            current = self.app.providers.get(self.app.current_provider)
            if current and hasattr(current, 'get_available_models'):
                models = current.get_available_models() or []
                if models:
                    section_models = Gio.Menu()
                    for mid in models:
                        item_model = Gio.MenuItem.new(mid, None)
                        item_model.set_action_and_target_value(
                            "app.set_provider_model",
                            GLib.Variant("s", mid)
                        )
                        section_models.append_item(item_model)
                    provider_menu.append_section(_("Models"), section_models)
        except Exception:
            pass

        # Section: Tools
        section_tools = Gio.Menu()
        item_preferences = Gio.MenuItem.new(_("Preferences"), None)
        item_preferences.set_action_and_target_value("app.preferences", None)
        section_tools.append_item(item_preferences)

        item_clear = Gio.MenuItem.new(_("Clear all"), None)
        item_clear.set_action_and_target_value("win.clear_all", None)
        section_tools.append_item(item_clear)

        item_export = Gio.MenuItem.new(_("Export"), None)
        item_export.set_action_and_target_value("win.export", None)
        section_tools.append_item(item_export)

        provider_menu.append_section(None, section_tools)

        self.provider_selector_button.set_menu_model(provider_menu)
        self.provider_selector_button.set_visible(True)

    # 로컬/오프라인 모델 선택 UI 제거

    def check_network(self):
        if self.app.check_network(): # Internet
            if not self.content:
                self.status_no_chat.set_visible(True)
                self.status_no_internet.set_visible(False)
            else:
                self.status_no_chat.set_visible(False)
                self.status_no_internet.set_visible(False)
        else:
            self.status_no_chat.set_visible(False)
            self.status_no_internet.set_visible(True)



    @Gtk.Template.Callback()
    def on_ask(self, *args):
        # IME(입력기) 커밋이 버퍼에 완전히 반영된 뒤 처리되도록 충분한 지연(50ms)
        GLib.timeout_add(50, self._on_ask_after_ime)

    def _on_ask_after_ime(self):
        prompt = self.message_entry.get_buffer().props.text.strip()
        if not prompt:
            return False

        self.message_entry.get_buffer().set_text("")

        if not self.chat:
            self.on_new_chat_action()

            # now get the latest row
            row = self.threads_list.get_row_at_index(len(self.app.data["chats"]) - 1)

            self.threads_list.select_row(row)
            self.threads_row_activated_cb()

        self.add_user_item(prompt)

        def thread_run():
            self.toast = Adw.Toast()
            self.toast.set_title(_("Generating response"))
            self.toast.set_button_label(_("Cancel"))
            self.toast.set_action_name("win.cancel")
            self.toast.set_timeout(0)
            self.toast_overlay.add_toast(self.toast)
            response = self.app.ask(prompt, self.chat)
            GLib.idle_add(cleanup, response, self.toast)

        def cleanup(response, toast):
            try:
                self.t.join()
                self.toast.dismiss()

                if not response:
                    self.add_assistant_item(_("Sorry, I don't know what to say."))
                else:
                    if isinstance(response, str):
                        self.add_assistant_item(response)
                    else:
                        buffered = io.BytesIO()
                        response.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue())

                        self.add_assistant_item(img_str.decode("utf-8"))

            except AttributeError:
                self.toast.dismiss()
                self.add_assistant_item(_("Sorry, I don't know what to say."))

        self.t = KillableThread(target=thread_run)
        self.t.start()
        return False

    # @Gtk.Template.Callback()
    # def on_emoji(self, *args):
    #     self.message_entry.do_insert_emoji(self.message_entry)

    def cancel(self, *args):
        try:
            self.t.kill()
            self.t.join()

            del self.t
            self.toast.dismiss()
        except AttributeError: # nothing to stop
            pass
        except Exception:
            self.t.join()
            del self.t
            self.toast.dismiss()

    def create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"win.{name}", shortcuts)
        
    def get_time(self):
        return format_time(datetime.now())


    def add_user_item(self, content):
        self.content.append(
            {
                "role": self.app.user_name,
                "content": content,
                "time": self.get_time(),
                "model": "",
            }
        )

        self.threads_row_activated_cb()

        self.scroll_down()

    def add_assistant_item(self, content):
        # If this is the first assistant reply in a brand-new chat, derive a title
        # from the assistant's first message (common chat UX)
        try:
            if len(self.content) == 1:  # exactly one user message present
                self._maybe_update_chat_title_from_assistant(content)
        except Exception:
            pass

        c = {
                "role": self.app.bot_name,
                "content": content,
                "time": self.get_time(),
            }

        # Provider · Model 표시
        display_model = "hamonize"
        try:
            provider = self.app.providers.get(self.app.current_provider)
            if provider and provider.enabled:
                prov_name = getattr(provider, 'name', self.app.current_provider)
                prov_model = getattr(provider, 'model', None) or getattr(provider, 'data', {}).get('model', '')
                if prov_model:
                    display_model = f"{prov_name} · {prov_model}"
                else:
                    display_model = prov_name
        except Exception:
            pass
        c["model"] = display_model

        self.content.append(c)

        self.threads_row_activated_cb()

        self.scroll_down()

    def _sanitize_title_text(self, text: str, max_len: int = 40) -> str:
        """Return a single-line, trimmed title, capped to max_len with ellipsis.

        - Use first non-empty line
        - Strip common markdown markers (**, *, _, __, ~~), inline code/backticks,
          heading/blockquote markers, and link syntax while keeping visible text
        - Collapse multiple spaces
        - Truncate with … if longer than max_len
        """
        if not text:
            return ""
        # Choose first non-empty line
        line = ""
        for part in str(text).splitlines():
            if part.strip():
                line = part.strip()
                break
        if not line:
            return ""
        # Basic markdown cleanup
        # Remove code fences/backticks
        line = line.replace("```", "")
        line = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", line)
        # Remove heading/blockquote markers
        line = line.lstrip("# ").lstrip("> ")
        # Convert markdown links [text](url) -> text
        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        # Remove bold/italic/underline/strike wrappers
        line = re.sub(r"(\*\*|__)(.*?)\1", r"\2", line)
        line = re.sub(r"(\*|_)(.*?)\1", r"\2", line)
        line = re.sub(r"~~(.*?)~~", r"\1", line)
        # Remove any remaining lightweight markers
        line = re.sub(r"[*_`~]", "", line)
        # Collapse whitespace
        line = " ".join(line.split())
        if len(line) > max_len:
            line = line[:max_len].rstrip() + "…"
        return line

    def _maybe_update_chat_title_from_assistant(self, assistant_text: str):
        """Update the chat title from the first assistant reply if still default.

        Falls back to the first user prompt if assistant text is unsuitable
        (e.g., image/base64 or empty).
        """
        try:
            current_title = self.chat.get("title", "")
            # Only auto-rename if it still looks like a fresh default title
            if not current_title.startswith("New Chat"):
                return

            # Heuristic: skip base64-like long chunks without spaces
            at = str(assistant_text or "")
            is_probably_base64 = len(at) > 120 and (" " not in at)

            new_title = ""
            if not is_probably_base64:
                new_title = self._sanitize_title_text(at)

            if not new_title or new_title.lower().startswith("sorry"):
                # Fallback to user's first message if assistant text is not helpful
                try:
                    user_first = self.content[0]["content"]
                    new_title = self._sanitize_title_text(user_first)
                except Exception:
                    pass

            if not new_title:
                return

            # Persist into data model
            self.chat["title"] = new_title

            # Update header title if this chat is open
            try:
                self.title.set_title(new_title)
            except Exception:
                pass

            # Update corresponding ThreadItem label in the sidebar
            try:
                current_id = self.chat.get("id")
                for thread_item in self.threads:
                    if getattr(thread_item, "id", None) == current_id:
                        thread_item.label_text = new_title
                        thread_item.label.set_text(new_title)
                        break
            except Exception:
                pass

            # Save to disk so the new title persists
            try:
                self.app.save()
            except Exception:
                pass
        except Exception:
            # Never break the message flow due to title update issues
            pass



