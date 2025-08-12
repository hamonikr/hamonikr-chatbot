import json
import socket
import requests
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class OllamaProvider(BaseProvider):
    name = "Ollama"
    model = "llama3.2"
    api_key_title = None  # Ollama doesn't need API key
    base_url = "http://localhost:11434"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        self.base_url = self.data.get("base_url", "http://localhost:11434")
        self.model = self.data.get("model", "llama3.2")
    
    def ask(self, prompt, chat):
        # Convert chat history to Ollama format
        messages = []
        for c in chat["content"][:-1]:  # Exclude current prompt
            if c["role"] == self.app.bot_name:
                role = "assistant"
            else:
                role = "user"
            messages.append({"role": role, "content": c["content"]})
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                headers=headers,
                json=data,
                timeout=60  # Longer timeout for local models
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["message"]["content"]
            elif response.status_code == 404:
                return _(f"Model '{self.model}' not found. Please pull it first with: ollama pull {self.model}")
            else:
                return _(f"Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            return _("Cannot connect to Ollama. Make sure Ollama is running (ollama serve).")
        except requests.exceptions.Timeout:
            return _("Request timed out. The model might be loading or processing.")
        except Exception as e:
            return _(f"Error: {str(e)}")
    
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
        
        # Model selection row
        self.model_row = Adw.EntryRow()
        self.model_row.connect("apply", self.on_apply)
        self.model_row.props.text = self.model or ""
        self.model_row.props.title = "Model"
        self.model_row.set_show_apply_button(True)
        self.model_row.add_suffix(self.how_to_get_models())
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