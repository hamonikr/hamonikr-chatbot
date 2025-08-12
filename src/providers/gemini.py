import json
import socket
from gettext import gettext as _
import google.generativeai as genai
from gi.repository import Gtk, Adw

from .base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "Gemini"
    description = _("Google Gemini API")
    default_model = "gemini-2.5-pro"
    api_key_title = "API Key"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        
        self.api_key = self.data.get("api_key", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = self.data.get("model", self.default_model)
    
    def ask(self, prompt, chat):
        if not self.api_key:
            return _("Please configure your Gemini API key in preferences.")
        
        try:
            model = genai.GenerativeModel(self.model)
            
            # Convert chat history to Gemini format
            history = []
            for c in chat["content"][:-1]:  # Exclude current prompt
                if c["role"] == self.app.bot_name:
                    role = "model"
                else:
                    role = "user"
                history.append({"role": role, "parts": [c["content"]]})
            
            # Start chat with history
            chat_session = model.start_chat(history=history)
            
            # Send the current prompt
            response = chat_session.send_message(prompt)
            return response.text
            
        except Exception as e:
            if "API_KEY_INVALID" in str(e):
                return _("Your API key is invalid, please check your preferences.")
            elif "RATE_LIMIT" in str(e):
                return _("Rate limit exceeded. Please try again later.")
            elif "quota" in str(e).lower():
                return _("You exceeded your current quota, please check your plan and billing details.")
            else:
                return _(f"Error: {str(e)}")
    
    def get_settings_rows(self):
        self.rows = []
        
        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.api_key or ""
        self.api_row.props.title = self.api_key_title
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_get_a_token())
        self.rows.append(self.api_row)

        # 모델 드롭다운 (동적 조회 + 폴백)
        model_choices = self.fetch_models() + ["Custom…"]
        self.model_combo = Adw.ComboRow()
        self.model_combo.set_title(_("Model"))
        try:
            string_list = Gtk.StringList.new(model_choices)
        except Exception:
            string_list = Gtk.StringList()
            for m in model_choices:
                string_list.append(m)
        self.model_combo.set_model(string_list)
        try:
            idx = model_choices.index(self.model)
        except Exception:
            idx = len(model_choices) - 1
        self.model_combo.set_selected(idx)
        try:
            self.model_combo.set_tooltip_text(model_choices[idx])
        except Exception:
            pass
        self.model_combo.connect("notify::selected", self.on_model_combo_changed)
        self.rows.append(self.model_combo)

        # Custom 입력
        self.model_row = Adw.EntryRow()
        self.model_row.connect("apply", self.on_apply)
        self.model_row.props.text = self.model if idx == len(model_choices) - 1 else ""
        self.model_row.props.title = _("Custom model id")
        self.model_row.set_show_apply_button(True)
        self.model_row.set_visible(idx == len(model_choices) - 1)
        self.rows.append(self.model_row)
        
        return self.rows
    
    def on_apply(self, widget):
        self.api_key = self.api_row.get_text()
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.data["api_key"] = self.api_key
        self.model = self.model_row.get_text() or self.model
        if self.model:
            self.data["model"] = self.model

    def on_model_combo_changed(self, combo, _pspec=None):
        selected = combo.get_selected()
        if selected < 0:
            return
        model_choices = self.fetch_models() + ["Custom…"]
        choice = model_choices[selected]
        is_custom = (choice == "Custom…")
        self.model_row.set_visible(is_custom)
        if not is_custom:
            self.model = choice
            self.data["model"] = self.model

    def get_available_models(self):
        try:
            return self.fetch_models()
        except Exception:
            return [self.default_model]
        try:
            self.model_combo.set_tooltip_text(choice)
        except Exception:
            pass
    
    def how_to_get_a_token(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("Get API key from Google AI Studio")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
    
    def open_documentation(self, widget):
        Gtk.show_uri(None, "https://makersuite.google.com/app/apikey", 0)


    def fetch_models(self):
        try:
            if not self.api_key:
                # 프리셋 폴백 (대표 최신 라인업 예시)
                return [
                    "gemini-2.5-pro",
                    "gemini-2.5-flash",
                    "gemini-1.5-pro",
                    "gemini-1.5-flash",
                ]
            # list_models 호출 후 텍스트 생성 가능 모델만 필터
            models = []
            for m in genai.list_models():
                mid = getattr(m, "name", None) or getattr(m, "model", None)
                if not mid:
                    continue
                # 대화/텍스트 생성 가능한 제품군 위주 필터(간단 규칙)
                if any(k in mid for k in ["gemini", "flash", "pro"]):
                    models.append(mid)
            return sorted(list(dict.fromkeys(models))) or [
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ]
        except Exception:
            return [
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ]
class GeminiFlashProvider(GeminiProvider):
    name = "Gemini Flash"
    default_model = "gemini-2.5-flash"


class GeminiProProvider(GeminiProvider):  
    name = "Gemini Pro"
    default_model = "gemini-2.5-pro"