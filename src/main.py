# main.py
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

import sys
import gi
import time
import os
import subprocess
import inspect

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Xdp', '1.0')
gi.require_version('GtkSource', '5')

from gi.repository import Gtk, Gio, Adw, Xdp, GLib
try:
    from builtins import _  # provided by gettext.install in launcher
except Exception:
    from gettext import gettext as _  # fallback when running out of tree
from .views.window import BavarderWindow
from .views.about_window import AboutWindow
from .views.preferences_window import PreferencesWindow
from .constants import app_id
from .providers import PROVIDERS

import json


def get_clipboard_content():
    """Return clipboard text using xclip or xsel if available, else None.
    Tries up to 3 times with short delays to accommodate clipboard readiness.
    """
    for attempt in range(3):
        try:
            content = subprocess.check_output(
                ['xclip', '-selection', 'clipboard', '-o'], text=True
            )
            if content.strip() != "":
                return content
        except Exception:
            time.sleep(1)

        try:
            content = subprocess.check_output(
                ['xsel', '--clipboard', '--output'], text=True
            )
            if content.strip() != "":
                return content
        except Exception:
            time.sleep(1)

    return None

user_config_dir = os.environ.get(
    "XDG_CONFIG_HOME", os.environ["HOME"] + "/.config"
)

user_data_dir = os.environ.get(
    "XDG_DATA_HOME", os.environ["HOME"] + "/.local/share"
)

user_cache_dir = os.environ.get(
    "XDG_CACHE_HOME", os.environ["HOME"] + "/.cache"
)

model_path = os.path.join(user_cache_dir, "hamonikr-chatbot", "models")

class BavarderApplication(Adw.Application):
    """The main application singleton class."""

    model_name = "ggml-model-gpt4all-falcon-q4_0.bin"
    models = set()
    model = None
    action_running_in_background = False
    number_of_win = 0

    def __init__(self):
        super().__init__(application_id=app_id,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS | Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.create_action("quit", self.on_quit, ["<primary>q"])
        self.create_action("close", self.on_close, ["<primary>w"])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action, ['<primary>comma'])
        self.create_action('new_chat', self.on_new_chat_action, ["<primary>n"])
        # 키 입력은 위젯 단에서 처리(Enter=전송, Ctrl/Shift+Enter=줄바꿈)
        self.create_action('ask', self.on_ask)
        self.create_action('new_window', self.on_new_window, ["<primary><shift>n"])

        # CLI 옵션: -p/--prompt 초기 프롬프트 지원
        try:
            self.add_main_option(
                "prompt",
                ord('p'),
                GLib.OptionFlags.NONE,
                GLib.OptionArg.STRING,
                _("Initial prompt to send on startup"),
                _("PROMPT")
            )
            # CLI 옵션: -c/--clipboard 클립보드 내용을 프롬프트로 사용
            self.add_main_option(
                "clipboard",
                ord('c'),
                GLib.OptionFlags.NONE,
                GLib.OptionArg.NONE,
                _("Use clipboard content as prompt"),
                None
            )
        except Exception:
            # 일부 환경에서 중복 등록 등을 무시
            pass

        self.initial_prompt = None
        self.initial_prompt_from_clipboard = False
        self.initial_system_injection = None

        self.data_path = os.path.join(user_data_dir, "hamonikr-chatbot")

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)

        if not os.path.exists(model_path):
            os.makedirs(model_path)

        self.data_path = os.path.join(self.data_path, "data.json")

        self.data = {
            "chats": [],
            "providers": {
                "ollama": {"enabled": True, "data": {}},
                "google-flan-t5-xxl": {"enabled": False, "data": {}},
                "gpt-2": {"enabled": False, "data": {}},

            },
            "models": {}
        }

        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception: # if there is an error, we use a plain config
                pass

        self.settings = Gio.Settings(schema_id=app_id)

        self.local_mode = self.settings.get_boolean("local-mode")
        self.current_provider = self.settings.get_string("current-provider")
        self.model_name = self.settings.get_string("model")
        
        # 신규 사용자의 경우 current_provider가 기본값이 아니면 ollama로 설정
        if self.current_provider in ["google-flan-t5-xxl", ""]:
            self.settings.set_string("current-provider", "ollama")
            self.current_provider = "ollama"
        # 초기 테마 적용
        try:
            scheme = self.settings.get_string("color-scheme") or "light"
            # 시스템 테마가 설정되어 있으면 라이트 테마로 변경
            if scheme == "system":
                scheme = "light"
                self.settings.set_string("color-scheme", scheme)
        except Exception:
            scheme = "light"
        self.apply_color_scheme(scheme)

        self.create_stateful_action(
            "set_provider",
            GLib.VariantType.new("s"),
            GLib.Variant("s", self.current_provider),
            self.on_set_provider_action
        )

        self.create_stateful_action(
            "set_model",
            GLib.VariantType.new("s"),
            GLib.Variant("s", self.model_name),
            self.on_set_model_action
        )

        # Online provider model selection (for current provider)
        self.create_stateful_action(
            "set_provider_model",
            GLib.VariantType.new("s"),
            GLib.Variant("s", ""),
            self.on_set_provider_model_action
        )

        self.bot_name = self.settings.get_string("bot-name")
        self.user_name = self.settings.get_string("user-name")

        # 테마 상태 액션 등록
        self.create_stateful_action(
            "set_color_scheme",
            GLib.VariantType.new("s"),
            GLib.Variant("s", scheme),
            self.on_set_color_scheme_action
        )

    def apply_color_scheme(self, scheme: str):
        try:
            sm = Adw.StyleManager.get_default()
            if scheme == "light":
                sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            elif scheme == "dark":
                sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            else:
                # 시스템 테마 제거, 기본적으로 라이트 테마 사용
                sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        except Exception:
            pass

    def on_set_color_scheme_action(self, action, param):
        try:
            scheme = param.get_string()
        except Exception:
            scheme = "light"
        
        # 시스템 테마 선택 시 라이트 테마로 변경
        if scheme == "system":
            scheme = "light"
            
        self.apply_color_scheme(scheme)
        try:
            self.settings.set_string("color-scheme", scheme)
        except Exception:
            pass
        try:
            Gio.SimpleAction.set_state(self.lookup_action("set_color_scheme"), GLib.Variant("s", scheme))
        except Exception:
            pass


    def on_set_provider_action(self, action, *args):
        self.current_provider = args[0].get_string()
        Gio.SimpleAction.set_state(self.lookup_action("set_provider"), args[0])
        # 프로바이더 변경 시 상단 메뉴의 모델 섹션을 현재 프로바이더 기준으로 재구성
        try:
            if self.win:
                self.win.load_provider_selector()
        except Exception:
            pass

    def on_set_model_action(self, action, *args):
        previous = self.model_name
        self.model_name = args[0].get_string()
        if previous != self.model_name:
            # reset model for loading the new one
            self.model = None
        Gio.SimpleAction.set_state(self.lookup_action("set_model"), args[0])

    def on_set_provider_model_action(self, action, *args):
        """Set the model for the currently selected online provider."""
        try:
            model_id = args[0].get_string()
        except Exception:
            model_id = ""
        if not model_id:
            return
        # Find current provider and update its model
        try:
            provider = self.providers.get(self.current_provider)
            if provider is not None:
                # Persist into provider data and instance attribute if present
                if hasattr(provider, 'data'):
                    provider.data["model"] = model_id
                try:
                    provider.model = model_id
                except Exception:
                    pass
        except Exception:
            pass
        Gio.SimpleAction.set_state(self.lookup_action("set_provider_model"), args[0])

    def save(self):
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)
            self.settings.set_boolean("local-mode", self.local_mode)
            self.settings.set_string("current-provider", self.current_provider)
            self.settings.set_string("model", self.model_name)
            self.settings.set_string("bot-name", self.bot_name)
            self.settings.set_string("user-name", self.user_name)

    def on_quit(self, action, *args, **kwargs):
        """Called when the user activates the Quit action."""
        self.save()
        self.quit()

    def on_close(self, action, *args, **kwargs):
        if self.number_of_win == 1:
            self.on_quit(action, *args, **kwargs)
        else:
            self.win.destroy()
            self.number_of_win -= 1

    def on_new_chat_action(self, widget, _):
        chat_id = 0
        for chat in self.data["chats"]:
            if chat["id"] > chat_id:
                chat_id = chat["id"]
        chat_id += 1
        chat = {
            "id": chat_id,
            "title": "New Chat " + str(chat_id),
            "starred": False,
            "content": [],
        }

        self.data["chats"].append(chat)
        self.win.load_threads()

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        self.new_window()

        # 창이 처음 생성될 때 CLI 프롬프트가 있으면 전송 예약
        if getattr(self, "initial_prompt", None):
            GLib.idle_add(self._send_initial_prompt)

    @property
    def win(self):
        """The application's main window."""
        return self.props.active_window
        
    def new_window(self, window=None):
        if window:
            win = self.props.active_window
        else:
            win = BavarderWindow(application=self)
            self.number_of_win += 1

        
        win.connect("close-request", self.on_close)

        self.providers = {}

        for provider in PROVIDERS:
            p = provider(self, win)

            self.providers[p.slug] = p

        # 오프라인 모델 선택 UI 제거됨
        win.load_provider_selector()
        win.present()


    def on_new_window(self, widget, _):
        self.new_window()


    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = AboutWindow(self.win)
        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        self.preferences_window = PreferencesWindow(self.win)
        self.preferences_window.present()


    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)

        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def create_stateful_action(self, name, parameter_type, initial_state, callback, shortcuts=None):
        """Add a stateful application action."""

        action = Gio.SimpleAction.new_stateful(
            name, parameter_type, initial_state)
        action.connect("activate", callback)

        self.add_action(action)

        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)

    def on_ask(self, widget, _):
        try:
            self.win.on_ask()
        except AttributeError:
            pass

    def do_command_line(self, command_line):
        """Handle CLI options like -p/--prompt for initial message."""
        try:
            options = command_line.get_options_dict()
            v = options.lookup_value("prompt", GLib.VariantType.new('s'))
            if v is not None:
                try:
                    self.initial_prompt = v.get_string()
                except Exception:
                    self.initial_prompt = None
            # -c/--clipboard 처리 (명시적 -p가 없을 때만 사용)
            if not self.initial_prompt:
                c = options.lookup_value("clipboard", GLib.VariantType.new('b'))
                if c is not None and c.get_boolean():
                    clip = get_clipboard_content()
                    if clip and clip.strip():
                        self.initial_prompt = clip.strip()
                        self.initial_prompt_from_clipboard = True
                        # 시스템 프롬프트 동적 주입 텍스트
                        self.initial_system_injection = (
                            "다음 문장을 분석해주세요:\n"
                            "1. 프로그램 소스코드인 경우: 코드에 대한 설명을 제공해주세요.\n"
                            "2. 오류 메시지인 경우: \n"
                            "    하모니카OS(우분투 커널 기반, 리눅스 민트의 시나몬 데스크톱 환경 포함)를 사용하는 질문자가 특정 문제를 제기한 상황입니다.\n\n"
                            "    하모니카, 하모니카OS, HamoniKR, HamoniKR OS 등의 단어는 모두 하모니카OS를 의미합니다.\n"
                            "    하모니카OS 는 linuxmint 를 기반으로, 한국 사용자들의 환경에 적합한 여러 프로그램을 추가하고 개작한 운영체제입니다.\n"
                            "    하모니카 5.0은 linuxmint 20.1 Ulyssa 기반이며, Ubuntu 20.04 Focal 과 동일한 패키지입니다. 코드네임은 한라(Hanla) 입니다.\n"
                            "    하모니카 6.0은 linuxmint 20.3 Una 기반이며, Ubuntu 20.4 Focal 과 동일한 패키지입니다. 코드네임은 금강(kumkang) 입니다.\n"
                            "    하모니카 7.0은 linuxmint 21.2 Victoria 기반이며, Ubuntu 22.04 jammy 과 동일한 패키지입니다. 코드네임은 태백(taebaek) 입니다.\n"
                            "    하모니카 8.0은 linuxmint 22 Wilma 기반이며, Ubuntu 24.04 Noble 과 동일한 패키지입니다. 코드네임은 백두(paektu) 입니다.\n\n"
                            "    정보를 제공할 때 다음의 우선순위로 웹사이트에서 정보를 검색하여 답변에 포함합니다:\n"
                            "    - 하모니카 매뉴얼 사이트 (버전별):\n"
                            "    - https://docs.hamonikr.org/hamonikr\n"
                            "    - https://docs.hamonikr.org/hamonikr-5.0\n"
                            "    - https://docs.hamonikr.org/hamonikr-6.0\n"
                            "    - https://docs.hamonikr.org/hamonikr-7.0\n"
                            "    - https://docs.hamonikr.org/hamonikr-8.0\n"
                            "    - 하모니카 커뮤니티 질의응답 게시글:\n"
                            "    - https://hamonikr.org/hamoni_board\n"
                            "    - 우분투와 리눅스 민트의 질의응답 사이트:\n"
                            "    - https://askubuntu.com/\n"
                            "    - https://forums.linuxmint.com/\n\n"
                            "    a. 질문자가 제공한 정보가 충분하다면, 해당 문제를 해결하기 위한 구체적인 방법을 한글로 자세히 설명합니다. 반드시 사용한 정보의 출처를 명확하게 제공하세요.\n"
                            "    b. 질문이 하모니카OS, 리눅스, 또는 시나몬 데스크톱 환경과 관련이 없거나, 제공된 정보로 정확한 출처를 명확하게 제시할 수 없는 경우에는 일반적인 응답을 해주세요.\n"
                            "    c. 이 답변이 AI 가 작성한 것을 알려주고, 인공지능 답변을 그대로 사용하는 위험에 대해서 알려주세요.\n\n"
                            "    주의사항: 코드를 설명하는 부분은 bash, python 등의 문구를 붙이지 말고 평문으로 출력해주세요.\n"
                            "    주의사항: 강조를 위해 ** 으로 표시하는 부분은 평문으로 출력해주세요.\n"
                            "    주의사항: 항상 친절하고 이해하기 쉬운 언어를 사용하여 답변하며, 하모니카OS, 리눅스 민트, 시나몬 데스크톱 환경과 관련된 문제 해결에 중점을 둡니다.\n"
                            "    주의사항: 답변을 하기 전 전체 답변 내용을 검토해서, 제대로 구성되지 않은 문장이나, 문맥상 이상한 부분을 자연스럽게 수정하는 과정을 수행 후, 리눅스 전문가가 말하듯이 해주세요."
                        )
        except Exception:
            self.initial_prompt = None

        # 활성화 및 창 표시
        self.activate()

        # 이미 실행 중인 인스턴스에서도 즉시 전송 예약
        if getattr(self, "initial_prompt", None):
            GLib.idle_add(self._send_initial_prompt)

        return 0

    def _send_initial_prompt(self):
        """Inject the CLI prompt into entry and trigger send once UI is ready."""
        try:
            prompt = (self.initial_prompt or "").strip()
            self.initial_prompt = None
            if not prompt:
                return False
            if not self.win:
                return False
            # -c 사용 시 시스템 텍스트를 프롬프트 앞에 결합
            # -c 사용 시 시스템 프롬프트는 보이지 않게(시스템 롤) 주입하고, 사용자에겐 원문만 보이게 함
            if self.initial_prompt_from_clipboard and self.initial_system_injection:
                try:
                    # 공급자에게 전달하기 위해 일시 시스템 프롬프트로 저장
                    self.transient_system_prompt = self.initial_system_injection
                except Exception:
                    pass
                visible_text = prompt
            else:
                visible_text = prompt
            buf = self.win.message_entry.get_buffer()
            buf.set_text(visible_text)
            self.win.on_ask()
        except Exception:
            # 실패 시 한 번만 시도하고 종료
            pass
        return False

    def ask(self, prompt, chat, stream=False, callback=None):
        if self.local_mode:
            if not self.setup_chat(): # NO MODELS:
                return _("Please download a model from Preferences by clicking on the Dot Menu at the top!")
            else:
                for p in ["Hi", "Hello"]:
                    if p.lower() in prompt.lower():
                        return _("Hello, I am HamoniKR Chatbot, a Chit-Chat AI")
                system_template = f"""You are a helpful and friendly AI assistant with the name {self.bot_name}. The name of the user are {self.user_name}. Respond very concisely."""
                try:
                    if getattr(self, "transient_system_prompt", None):
                        system_template = f"{self.transient_system_prompt}\n\n{system_template}"
                except Exception:
                    pass
                with self.model.chat_session(self.model_settings.get("system_template", system_template)):
                    self.model.current_chat_session = chat["content"].copy()
                response = self.model.generate(
                    prompt=prompt, 
                    top_k=int(self.model_settings.get("top_k", 40)),
                    top_p=float(self.model_settings.get("top_p", 0.5)),
                    temp=float(self.model_settings.get("temperature", 0.9)),
                    max_tokens=int(self.model_settings.get("max_tokens", 500)),
                    repeat_penalty=float(self.model_settings.get("repetition_penalty", 1.20)),
                    repeat_last_n=int(self.model_settings.get("repeat_last_n", 64)),
                    n_batch=int(self.model_settings.get("n_batch", 10)),
                )

        else:
            l = list(self.providers.values())

            for p in l:
                if p.enabled and p.slug == self.current_provider:
                    # One-off system prompt injection support
                    sys_prompt = None
                    try:
                        sys_prompt = getattr(self, "transient_system_prompt", None)
                    except Exception:
                        sys_prompt = None
                    # Clear after capturing to avoid leaking into next request
                    try:
                        self.transient_system_prompt = None
                    except Exception:
                        pass

                    # Build a temporary chat payload if system prompt exists (do not mutate UI chat)
                    chat_payload = chat
                    try:
                        if sys_prompt:
                            chat_payload = {"content": list(chat["content"]) }
                            chat_payload["content"].insert(0, {"role": "system", "content": sys_prompt})
                    except Exception:
                        chat_payload = chat

                    if stream and callback:
                        # Use streaming if supported
                        if hasattr(self.providers[self.current_provider], 'ask_stream'):
                            # Try to pass system_prompt if supported
                            try:
                                sig = inspect.signature(self.providers[self.current_provider].ask_stream)
                                if 'system_prompt' in sig.parameters and sys_prompt:
                                    response = self.providers[self.current_provider].ask_stream(prompt, chat_payload, callback=callback, system_prompt=sys_prompt)
                                else:
                                    response = self.providers[self.current_provider].ask_stream(prompt, chat_payload, callback)
                            except Exception:
                                response = self.providers[self.current_provider].ask_stream(prompt, chat_payload, callback)
                        else:
                            # Fallback to non-streaming ask
                            try:
                                sig = inspect.signature(self.providers[self.current_provider].ask)
                                if 'system_prompt' in sig.parameters and sys_prompt:
                                    response = self.providers[self.current_provider].ask(prompt, chat_payload, system_prompt=sys_prompt)
                                else:
                                    response = self.providers[self.current_provider].ask(prompt, chat_payload)
                            except Exception:
                                response = self.providers[self.current_provider].ask(prompt, chat_payload)
                            if callback and response:
                                callback(response)
                    else:
                        # Regular non-streaming path
                        try:
                            sig = inspect.signature(self.providers[self.current_provider].ask)
                            if 'system_prompt' in sig.parameters and sys_prompt:
                                response = self.providers[self.current_provider].ask(prompt, chat_payload, system_prompt=sys_prompt)
                            else:
                                response = self.providers[self.current_provider].ask(prompt, chat_payload)
                        except Exception:
                            response = self.providers[self.current_provider].ask(prompt, chat_payload)
                    break
                else:
                    response = _("Please enable a provider from the Dot Menu")
                
        return response

    @property
    def model_settings(self):
        try:
            return self.data["models"][self.model_name]
        except KeyError:
            try:
                self.data["models"][self.model_name] = {}
            except KeyError:
                self.data["models"] = {}
                self.data["models"][self.model_name] = {}

        return self.data["models"][self.model_name]

    def setup_chat(self):
        if not self.models:
            self.list_models()
        return bool(self.models)

    def download_model(self, model=None):
        if model:
            self.model_name = model

    def list_models(self):
        self.models = set()
        for root, dirs, files in os.walk(model_path):
            for model in files:
                self.models.add(model)
    
    def delete_model(self, model):
        os.remove(os.path.join(model_path, model))
        self.list_models()

    def check_network(self):
        return False

    def clear_all_chats(self):
        self.data["chats"] = []
        self.win.load_threads()

def main(version):
    """The application's entry point."""
    app = BavarderApplication()
    return app.run(sys.argv)



