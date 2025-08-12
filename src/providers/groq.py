import json
import socket
import requests
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class GroqProvider(BaseProvider):
    name = "Groq"
    model = "llama-3.3-70b-versatile"
    api_key_title = "API Key"
    base_url = "https://api.groq.com/openai/v1"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        self.api_key = self.data.get("api_key", "")
    
    def ask(self, prompt, chat):
        if not self.api_key:
            return _("Please configure your Groq API key in preferences.")
        
        # Convert chat history to OpenAI format (Groq uses OpenAI-compatible API)
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
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 401:
                return _("Your API key is invalid, please check your preferences.")
            elif response.status_code == 429:
                return _("Rate limit exceeded. Please try again later.")
            elif response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return _(f"Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            return _("I'm having trouble connecting to the API, please check your internet connection.")
        except requests.exceptions.Timeout:
            return _("Request timed out. Please try again.")
        except Exception as e:
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
        
        return self.rows
    
    def on_apply(self, widget):
        self.api_key = self.api_row.get_text()
        self.data["api_key"] = self.api_key
    
    def how_to_get_a_token(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("Get API key from Groq Console")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
    
    def open_documentation(self, widget):
        Gtk.show_uri(None, "https://console.groq.com/keys", 0)


class GroqMixtralProvider(GroqProvider):
    name = "Groq Mixtral"
    model = "mixtral-8x7b-32768"


class GroqLlama3Provider(GroqProvider):
    name = "Groq Llama 3"
    model = "llama3-70b-8192"


class GroqGemmaProvider(GroqProvider):
    name = "Groq Gemma"  
    model = "gemma2-9b-it"