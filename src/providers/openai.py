from .base import BaseProvider
import openai
from openai import OpenAI
import socket
import os
from gettext import gettext as _

from gi.repository import Gtk, Adw, GLib


class BaseOpenAIProvider(BaseProvider):
    model = None
    api_key_title = "API Key"

    def __init__(self, app, window):
        super().__init__(app, window)

        try:
            self.client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
        except openai.OpenAIError:
            self.client = OpenAI(
                api_key="",
            )

        if self.data.get("api_key"):
            self.client.api_key = self.data["api_key"]
        if self.data.get("api_base"):
            self.client.base_url = self.data["api_base"]

    def ask(self, prompt, chat, stream=False, callback=None):
        _chat = []
        for c in chat["content"]:
            if c["role"] == self.app.bot_name:
                role = "assistant"
            else:
                role = "user"
            _chat.append({"role": role, "content": c["content"]})
        chat = _chat

        if self.model:
            prompt = self.chunk(prompt)
            try:
                if stream and callback:
                    # Streaming response
                    full_response = ""
                    stream_response = self.client.chat.completions.create(
                        model=self.model,
                        messages=chat,
                        stream=True
                    )
                    for chunk in stream_response:
                        if chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            callback(content)
                    return full_response
                else:
                    # Regular non-streaming response
                    response = self.client.chat.completions.create(
                                model=self.model,
                                messages=chat,
                            ).choices[0].message.content
                    return response
            except openai.AuthenticationError:
                return _("Your API key is invalid, please check your preferences.")
            except openai.BadRequestError:
                return _("You don't have access to this model, please check your plan and billing details.")
            except openai.RateLimitError:
                return _("You exceeded your current quota, please check your plan and billing details.")
            except openai.APIConnectionError:
                return _("I'm having trouble connecting to the API, please check your internet connection.")
            except socket.gaierror:
                return _("I'm having trouble connecting to the API, please check your internet connection.")
        else:
            return _("No model selected, you can choose one in preferences")

    def ask_stream(self, prompt, chat, callback=None):
        """Stream-enabled version for OpenAI providers"""
        return self.ask(prompt, chat, stream=True, callback=callback)


    def get_settings_rows(self):
        self.rows = []


        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.client.api_key or ""
        self.api_row.props.title = self.api_key_title
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_get_a_token())
        self.rows.append(self.api_row)

        self.api_url_row = Adw.EntryRow()
        self.api_url_row.connect("apply", self.on_apply)
        self.api_url_row.props.text=str(self.client.base_url) or ""
        self.api_url_row.props.title = "API Url"
        self.api_url_row.set_show_apply_button(True)
        self.api_url_row.add_suffix(self.how_to_get_base_url())
        self.rows.append(self.api_url_row)

        return self.rows

    def on_apply(self, widget):
        api_key = self.api_row.get_text()
        self.client.api_key = api_key
        self.client.base_url = self.api_url_row.get_text()

        self.data["api_key"] = self.client.api_key
        self.data["api_base"] = str(self.client.base_url)


    def how_to_get_base_url(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("How to choose base url")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button


class OpenAIProvider(BaseOpenAIProvider):
    name = "OpenAI"
    description = _("OpenAI API를 사용해 채팅 및 도구 호출 모델에 접근합니다")
    # 합리적인 기본값. 사용자가 바꿀 수 있음
    default_model = "gpt-4o-mini"

    def __init__(self, app, window):
        super().__init__(app, window)
        # 저장된 모델이 있으면 사용, 없으면 기본값
        self.model = self.data.get("model", self.default_model)

    def get_settings_rows(self):
        rows = super().get_settings_rows()

        # 모델 목록 동적 조회 (실패 시 대표 모델 리스트로 폴백)
        def _default_models():
            return [
                "gpt-5",
                "gpt-5-mini",
                "gpt-5-nano",
                "gpt-4.1",
                "gpt-4.1-mini",
                "gpt-4.1-nano",
                "gpt-4o",
                "gpt-4o-mini",
            ]

        def _fetch_models():
            try:
                models = []
                # OpenAI SDK 모델 나열
                resp = self.client.models.list()
                data = getattr(resp, "data", []) or []
                for m in data:
                    mid = getattr(m, "id", None)
                    if not mid:
                        continue
                    # 채팅 관련 모델 우선 노출 (간단 필터)
                    if any(k in mid for k in ["gpt", "o1", "o3", "o4", "4o", "4.1", "5"]):
                        models.append(mid)
                # 중복 제거 및 정렬
                models = sorted(list(dict.fromkeys(models)))
                # 폴백
                return models or _default_models()
            except Exception:
                return _default_models()

        dynamic_models = _fetch_models()
        self._openai_model_choices = dynamic_models + ["Custom…"]

        # 드롭다운(ComboRow)
        self.model_combo = Adw.ComboRow()
        self.model_combo.set_title(_("Model"))
        # Gtk.StringList로 모델 바인딩
        try:
            string_list = Gtk.StringList.new(self._openai_model_choices)
        except Exception:
            string_list = Gtk.StringList()
            for m in self._openai_model_choices:
                string_list.append(m)
        self.model_combo.set_model(string_list)

        # 현재 선택 반영
        try:
            idx = self._openai_model_choices.index(self.model)
        except Exception:
            idx = len(self._openai_model_choices) - 1  # Custom…
        self.model_combo.set_selected(idx)
        try:
            current_choice = self._openai_model_choices[idx]
            self.model_combo.set_tooltip_text(current_choice)
        except Exception:
            pass
        self.model_combo.connect("notify::selected", self.on_model_combo_changed)
        rows.append(self.model_combo)

        # Custom 입력용 EntryRow (Custom…일 때만 표시)
        self.custom_model_row = Adw.EntryRow()
        self.custom_model_row.connect("apply", self.on_apply_model_custom)
        self.custom_model_row.props.text = self.model if idx == len(self._openai_model_choices) - 1 else ""
        self.custom_model_row.props.title = _("Custom model id")
        self.custom_model_row.set_show_apply_button(True)
        self.custom_model_row.set_visible(idx == len(self._openai_model_choices) - 1)
        rows.append(self.custom_model_row)

        return rows

    def on_model_combo_changed(self, combo, _pspec=None):
        selected = combo.get_selected()
        if selected < 0:
            return
        choice = self._openai_model_choices[selected]
        is_custom = (choice == "Custom…")
        self.custom_model_row.set_visible(is_custom)
        if not is_custom:
            self.model = choice
            self.data["model"] = self.model
        # 항상 툴팁에 전체 모델명을 노출
        try:
            self.model_combo.set_tooltip_text(choice)
        except Exception:
            pass

    def on_apply_model_custom(self, widget):
        text = self.custom_model_row.get_text().strip()
        if text:
            self.model = text
            self.data["model"] = self.model

    # External API used by window model selector
    def get_available_models(self):
        try:
            models = []
            resp = self.client.models.list()
            data = getattr(resp, "data", []) or []
            for m in data:
                mid = getattr(m, "id", None)
                if mid and any(k in mid for k in ["gpt", "o1", "o3", "o4", "4o", "4.1", "5"]):
                    models.append(mid)
            models = sorted(list(dict.fromkeys(models)))
            if not models:
                return [
                    "gpt-5","gpt-5-mini","gpt-5-nano",
                    "gpt-4.1","gpt-4.1-mini","gpt-4.1-nano",
                    "gpt-4o","gpt-4o-mini",
                ]
            return models
        except Exception:
            return [
                "gpt-5","gpt-5-mini","gpt-5-nano",
                "gpt-4.1","gpt-4.1-mini","gpt-4.1-nano",
                "gpt-4o","gpt-4o-mini",
            ]
