import json
import socket
import requests
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class OllamaProvider(BaseProvider):
    name = "Ollama"
    model = "gpt-oss:latest"
    api_key_title = None  # Ollama doesn't need API key
    base_url = "https://api.hamonize.com/ollama"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        self.base_url = self.data.get("base_url", "https://api.hamonize.com/ollama")
        self.model = self.data.get("model", "gpt-oss:latest")
    
    def ask(self, prompt, chat, stream=False, callback=None, system_prompt=None):
        # Convert chat history to Ollama format
        messages = []
        try:
            for c in chat.get("content", [])[:-1]:  # Exclude current prompt
                role = "assistant" if c.get("role") == self.app.bot_name else "user"
                messages.append({"role": role, "content": c.get("content", "")})
        except Exception:
            pass

        # Optional: prepend system prompt
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "stream": bool(stream)
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                headers=headers,
                json=data,
                timeout=60,  # Longer timeout for local models
                stream=bool(stream)
            )

            if response.status_code == 404:
                return _(f"Model '{self.model}' not found. Please pull it first with: ollama pull {self.model}")
            if response.status_code != 200:
                return _(f"Error: {response.status_code} - {response.text}")

            if stream and callback:
                full_text = ""
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data_line = json.loads(line.decode("utf-8"))
                    except Exception:
                        continue
                    # Typical streaming chunk contains {"message": {"role": "assistant", "content": "..."}, "done": false}
                    msg = data_line.get("message") or {}
                    chunk = msg.get("content") or ""
                    if chunk:
                        full_text += chunk
                        try:
                            callback(chunk)
                        except Exception:
                            # Don't break the stream on callback errors
                            pass
                    if data_line.get("done"):
                        break
                return full_text
            else:
                # Non-streaming: parse once
                result = response.json()
                try:
                    return result["message"]["content"]
                except Exception:
                    return str(result)

        except requests.exceptions.ConnectionError:
            return _("Cannot connect to Ollama. Make sure Ollama is running (ollama serve).")
        except requests.exceptions.Timeout:
            return _("Request timed out. The model might be loading or processing.")
        except Exception as e:
            return _(f"Error: {str(e)}")

    def ask_stream(self, prompt, chat, callback=None, system_prompt=None):
        # Convenience wrapper to enable streaming
        return self.ask(prompt, chat, stream=True, callback=callback, system_prompt=system_prompt)
    
    def get_available_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
        except:
            pass
        return []
    
    def get_settings_rows(self):
        self.rows = []
        
        # Base URL row
        self.url_row = Adw.EntryRow()
        self.url_row.connect("apply", self.on_apply)
        self.url_row.props.text = self.base_url or ""
        self.url_row.props.title = "Ollama URL"
        self.url_row.set_show_apply_button(True)
        self.rows.append(self.url_row)
        
        # Model selection (dynamic via /api/tags) + Custom fallback
        models = self.get_available_models()
        if not models:
            models = [self.model] if self.model else []
        model_choices = models + ["Custom…"]

        self.model_combo = Adw.ComboRow()
        self.model_combo.set_title("Model")
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
        self.model_combo.add_suffix(self.how_to_get_models())
        self.rows.append(self.model_combo)

        # Custom input row
        self.model_row = Adw.EntryRow()
        self.model_row.connect("apply", self.on_apply)
        self.model_row.props.text = self.model if idx == len(model_choices) - 1 else ""
        self.model_row.props.title = "Custom model id"
        self.model_row.set_show_apply_button(True)
        self.model_row.set_visible(idx == len(model_choices) - 1)
        self.rows.append(self.model_row)
        
        return self.rows
    
    def on_apply(self, widget):
        self.base_url = self.url_row.get_text()
        self.model = self.model_row.get_text()
        self.data["base_url"] = self.base_url
        self.data["model"] = self.model
    
    def how_to_get_models(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("See available models at ollama.ai/library")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
    
    def open_documentation(self, widget):
        Gtk.show_uri(None, "https://ollama.ai/library", 0)

    def on_model_combo_changed(self, combo, _pspec=None):
        selected = combo.get_selected()
        if selected < 0:
            return
        model_choices = (self.get_available_models() or ([self.model] if self.model else [])) + ["Custom…"]
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


class OllamaLlama3Provider(OllamaProvider):
    name = "Ollama Llama 3"
    model = "llama3.2"


class OllamaMistralProvider(OllamaProvider):
    name = "Ollama Mistral"
    model = "mistral"


class OllamaGemmaProvider(OllamaProvider):
    name = "Ollama Gemma"
    model = "gemma2"


class OllamaCodeLlamaProvider(OllamaProvider):
    name = "Ollama Code Llama"
    model = "codellama"


class OllamaDeepseekProvider(OllamaProvider):
    name = "Ollama Deepseek"
    model = "deepseek-coder"