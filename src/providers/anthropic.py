from .base import BaseProvider
import socket
import os
import requests

from gi.repository import Gtk, Adw


class AnthropicBaseProvider(BaseProvider):
    name = "Anthropic"
    description = "Claude 계열 모델을 제공하는 Anthropic API"

    api_key_title = "API Key"
    model = None

    def ask(self, prompt, chat):
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

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "messages": messages + [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            data = resp.json()
            if resp.status_code >= 400:
                return data.get("error", {}).get("message", str(data))
            # Claude API returns list of content blocks
            content = data.get("content", [])
            if content and isinstance(content, list):
                block = content[0]
                return block.get("text", "") if isinstance(block, dict) else str(block)
            return str(data)
        except requests.exceptions.RequestException:
            return _("I'm having trouble connecting to the API, please check your internet connection.")

    def get_settings_rows(self):
        self.rows = []

        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.data.get("api_key") or ""
        self.api_row.props.title = self.api_key_title
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_get_a_token())
        self.rows.append(self.api_row)

        return self.rows

    def on_apply(self, widget):
        api_key = self.api_row.get_text()
        self.data["api_key"] = api_key


class ClaudeSonnet4Provider(AnthropicBaseProvider):
    name = "Anthropic Claude Sonnet 4"
    description = "최신 Sonnet-4 모델"
    model = "claude-4-sonnet-latest"


