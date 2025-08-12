import json
import socket
import requests
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = "OpenRouter"
    model = "anthropic/claude-3.5-sonnet"
    api_key_title = "API Key"
    base_url = "https://openrouter.ai/api/v1"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        self.api_key = self.data.get("api_key", "")
        self.site_url = self.data.get("site_url", "https://github.com/hamonikr/hamonikr-chatbot")
        self.site_name = self.data.get("site_name", "HamoniKR Chatbot")
    
    def ask(self, prompt, chat):
        if not self.api_key:
            return _("Please configure your OpenRouter API key in preferences.")
        
        # Convert chat history to OpenAI format
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
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name
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
            elif response.status_code == 402:
                return _("Insufficient credits. Please add credits to your account.")
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
        
        # Model selection row
        self.model_row = Adw.EntryRow()
        self.model_row.connect("apply", self.on_apply)
        self.model_row.props.text = self.model or ""
        self.model_row.props.title = "Model"
        self.model_row.set_show_apply_button(True)
        self.rows.append(self.model_row)
        
        return self.rows
    
    def on_apply(self, widget):
        self.api_key = self.api_row.get_text()
        self.model = self.model_row.get_text()
        self.data["api_key"] = self.api_key
        self.data["model"] = self.model
    
    def how_to_get_a_token(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("Get API key from OpenRouter")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
    
    def open_documentation(self, widget):
        Gtk.show_uri(None, "https://openrouter.ai/keys", 0)


class OpenRouterGPT4Provider(OpenRouterProvider):
    name = "OpenRouter GPT-4"
    model = "openai/gpt-4-turbo"


class OpenRouterClaudeProvider(OpenRouterProvider):
    name = "OpenRouter Claude"
    model = "anthropic/claude-3.5-sonnet"


class OpenRouterGeminiProvider(OpenRouterProvider):
    name = "OpenRouter Gemini"
    model = "google/gemini-pro-1.5"