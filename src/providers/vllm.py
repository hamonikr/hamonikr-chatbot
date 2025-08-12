import json
import socket
import requests
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class VLLMProvider(BaseProvider):
    name = "vLLM"
    model = "meta-llama/Llama-3.2-3B-Instruct"
    api_key_title = "API Key (Optional)"
    base_url = "http://localhost:8000"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        self.base_url = self.data.get("base_url", "http://localhost:8000")
        self.api_key = self.data.get("api_key", "")
        self.model = self.data.get("model", "meta-llama/Llama-3.2-3B-Instruct")
    
    def ask(self, prompt, chat):
        # Convert chat history to OpenAI format (vLLM uses OpenAI-compatible API)
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
        
        # Add API key if provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60  # Longer timeout for self-hosted models
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            elif response.status_code == 404:
                return _(f"Model '{self.model}' not found. Please check the model name and ensure it's loaded in vLLM.")
            elif response.status_code == 401:
                return _("Authentication failed. Please check your API key if required.")
            else:
                return _(f"Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            return _("Cannot connect to vLLM server. Make sure vLLM is running at the specified URL.")
        except requests.exceptions.Timeout:
            return _("Request timed out. The model might be loading or processing.")
        except Exception as e:
            return _(f"Error: {str(e)}")
    
    def get_settings_rows(self):
        self.rows = []
        
        # Base URL row
        self.url_row = Adw.EntryRow()
        self.url_row.connect("apply", self.on_apply)
        self.url_row.props.text = self.base_url or ""
        self.url_row.props.title = "vLLM Server URL"
        self.url_row.set_show_apply_button(True)
        self.rows.append(self.url_row)
        
        # Model row
        self.model_row = Adw.EntryRow()
        self.model_row.connect("apply", self.on_apply)
        self.model_row.props.text = self.model or ""
        self.model_row.props.title = "Model Name"
        self.model_row.set_show_apply_button(True)
        self.rows.append(self.model_row)
        
        # API Key row (optional)
        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.api_key or ""
        self.api_row.props.title = self.api_key_title
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_setup())
        self.rows.append(self.api_row)
        
        return self.rows
    
    def on_apply(self, widget):
        self.base_url = self.url_row.get_text()
        self.model = self.model_row.get_text()
        self.api_key = self.api_row.get_text()
        self.data["base_url"] = self.base_url
        self.data["model"] = self.model
        self.data["api_key"] = self.api_key
    
    def how_to_setup(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("Learn how to setup vLLM")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
    
    def open_documentation(self, widget):
        Gtk.show_uri(None, "https://docs.vllm.ai/en/latest/getting_started/quickstart.html", 0)