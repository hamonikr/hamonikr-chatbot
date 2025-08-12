from .base import BaseProvider
import requests

from gi.repository import Gtk, Adw


class MistralBaseProvider(BaseProvider):
    name = "Mistral"
    description = "Mistral AI API"

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
            "Authorization": f"Bearer {self.data.get('api_key', '')}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages + [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            data = resp.json()
            if resp.status_code >= 400:
                return data.get("error", data)
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            return message.get("content", "")
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


class MistralLargeProvider(MistralBaseProvider):
    name = "Mistral Large"
    description = "복잡한 이해와 추론에 강한 Mistral 대형 모델"
    model = "mistral-large-latest"


