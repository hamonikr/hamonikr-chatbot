import json
import socket
import requests
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class HuggingFaceProvider(BaseProvider):
    name = "HuggingFace"
    model = "meta-llama/Llama-3.2-3B-Instruct"
    api_key_title = "API Token"
    base_url = "https://api-inference.huggingface.co/models"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        self.api_key = self.data.get("api_key", "")
        self.model = self.data.get("model", "meta-llama/Llama-3.2-3B-Instruct")
    
    def ask(self, prompt, chat):
        if not self.api_key:
            return _("Please configure your HuggingFace API token in preferences.")
        
        # Build conversation context
        context = ""
        for c in chat["content"][:-1]:  # Exclude current prompt
            if c["role"] == self.app.bot_name:
                context += f"Assistant: {c['content']}\n"
            else:
                context += f"User: {c['content']}\n"
        
        # Add current prompt
        full_prompt = f"{context}User: {prompt}\nAssistant:"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 2048,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/{self.model}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 401:
                return _("Your API token is invalid, please check your preferences.")
            elif response.status_code == 429:
                return _("Rate limit exceeded. Please try again later.")
            elif response.status_code == 503:
                return _("Model is loading. Please try again in a few seconds.")
            elif response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "")
                elif isinstance(result, dict):
                    return result.get("generated_text", "")
                else:
                    return str(result)
            else:
                error_msg = response.json().get("error", response.text)
                return _(f"Error: {error_msg}")
                
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
        self.model_row.props.title = "Model ID"
        self.model_row.set_show_apply_button(True)
        self.model_row.add_suffix(self.how_to_find_models())
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
        about_button.set_tooltip_text("Get API token from HuggingFace")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
    
    def how_to_find_models(self):
        models_button = Gtk.Button()
        models_button.set_icon_name("system-search-symbolic")
        models_button.set_tooltip_text("Browse HuggingFace models")
        models_button.add_css_class("flat")
        models_button.set_valign(Gtk.Align.CENTER)
        models_button.connect("clicked", self.open_models_page)
        return models_button
    
    def open_documentation(self, widget):
        Gtk.show_uri(None, "https://huggingface.co/settings/tokens", 0)
    
    def open_models_page(self, widget):
        Gtk.show_uri(None, "https://huggingface.co/models?pipeline_tag=text-generation", 0)


class HuggingFaceMistralProvider(HuggingFaceProvider):
    name = "HuggingFace Mistral"
    model = "mistralai/Mistral-7B-Instruct-v0.2"


class HuggingFaceZephyrProvider(HuggingFaceProvider):
    name = "HuggingFace Zephyr"
    model = "HuggingFaceH4/zephyr-7b-beta"


class HuggingFaceCodeLlamaProvider(HuggingFaceProvider):
    name = "HuggingFace CodeLlama"
    model = "codellama/CodeLlama-7b-Instruct-hf"