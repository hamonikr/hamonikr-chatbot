from .base import BaseProvider
import socket
import os
import requests
import json
from gettext import gettext as _

from gi.repository import Gtk, Adw


class AnthropicBaseProvider(BaseProvider):
    name = "Anthropic"
    description = "Claude 계열 모델을 제공하는 Anthropic API"

    api_key_title = "API Key"
    model = None

    def ask(self, prompt, chat, stream=False, callback=None):
        messages = []
        for c in chat["content"]:
            role = "assistant" if c["role"] == self.app.bot_name else "user"
            messages.append({"role": role, "content": c["content"]})

        if not self.data.get("api_key"):
            return _("No model selected, you can choose one in preferences")

        headers = {
            "x-api-key": self.data.get("api_key", ""),
            "anthropic-version": "2023-06-01", 
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": messages + [{"role": "user", "content": prompt}],
        }

        if stream and callback:
            payload["stream"] = True

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60,
                stream=stream
            )
            
            if stream and callback:
                # Handle streaming response
                full_response = ""
                for line in resp.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        text = delta.get("text", "")
                                        full_response += text
                                        callback(text)
                            except json.JSONDecodeError:
                                continue
                return full_response
            else:
                # Regular non-streaming response
                data = resp.json()
                if resp.status_code >= 400:
                    return data.get("error", {}).get("message", str(data))
                content = data.get("content", [])
                if content and isinstance(content, list):
                    block = content[0]
                    return block.get("text", "") if isinstance(block, dict) else str(block)
                return str(data)
        except requests.exceptions.RequestException:
            return _("I'm having trouble connecting to the API, please check your internet connection.")

    def ask_stream(self, prompt, chat, callback=None):
        """Stream-enabled version for Anthropic providers"""
        return self.ask(prompt, chat, stream=True, callback=callback)

    def get_settings_rows(self):
        self.rows = []

        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.data.get("api_key") or ""
        self.api_row.props.title = self.api_key_title
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_get_a_token())
        self.rows.append(self.api_row)

        # Anthropic: 공식 모델 목록 API가 없으므로 권장 프리셋 + Custom
        presets = self.fetch_presets()
        model_choices = presets + ["Custom…"]

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
            idx = model_choices.index(self.data.get("model", self.model or presets[0]))
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
        self.model_row.props.text = self.data.get("model", self.model or "") if idx == len(model_choices) - 1 else ""
        self.model_row.props.title = _("Custom model id")
        self.model_row.set_show_apply_button(True)
        self.model_row.set_visible(idx == len(model_choices) - 1)
        self.rows.append(self.model_row)

        return self.rows

    def on_apply(self, widget):
        api_key = self.api_row.get_text()
        self.data["api_key"] = api_key
        # 모델 저장
        self.model = self.model_row.get_text() or self.model
        if self.model:
            self.data["model"] = self.model

    def on_model_combo_changed(self, combo, _pspec=None):
        selected = combo.get_selected()
        if selected < 0:
            return
        model_choices = self.fetch_presets() + ["Custom…"]
        choice = model_choices[selected]
        is_custom = (choice == "Custom…")
        self.model_row.set_visible(is_custom)
        if not is_custom:
            self.model = choice
            self.data["model"] = self.model
        try:
            self.model_combo.set_tooltip_text(choice)
        except Exception:
            pass

    def fetch_presets(self):
        # 최신 라인업(Anthropic API 모델명) - Alias + Version 포함
        presets_in_order = [
            # Opus 4.1
            "claude-opus-4-1",            # alias
            "claude-opus-4-1-20250805",  # version
            # Opus 4
            "claude-opus-4-0",            # alias
            "claude-opus-4-20250514",    # version
            # Sonnet 4
            "claude-sonnet-4-0",         # alias
            "claude-sonnet-4-20250514",  # version
            # Sonnet 3.7
            "claude-3-7-sonnet-latest",  # alias
            "claude-3-7-sonnet-20250219",# version
            # Sonnet 3.5
            "claude-3-5-sonnet-latest",  # alias
            "claude-3-5-sonnet-20241022",# version
            # Haiku 3.5
            "claude-3-5-haiku-latest",   # alias
            "claude-3-5-haiku-20241022", # version
        ]
        # 중복 제거(순서 유지)
        seen = set()
        deduped = []
        for m in presets_in_order:
            if m not in seen:
                seen.add(m)
                deduped.append(m)
        return deduped

    def get_available_models(self):
        # Expose presets as available models list
        return self.fetch_presets()


class AnthropicProvider(AnthropicBaseProvider):
    name = "Anthropic"
    description = "Claude 계열 모델을 한 프로바이더에서 관리"
    # 기본 모델
    model = "claude-sonnet-4-20250514"

    def __init__(self, app, window):
        super().__init__(app, window)
        # 저장된 모델 우선
        self.model = self.data.get("model", self.model)

