import json
import socket
from gettext import gettext as _
import google.generativeai as genai
from gi.repository import Gtk, Adw

from .base import BaseProvider


class GeminiProvider(BaseProvider):
    name = "Gemini"
    model = "gemini-1.5-pro"
    api_key_title = "API Key"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        
        self.api_key = self.data.get("api_key", "")
        if self.api_key:
            genai.configure(api_key=self.api_key)
    
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
        
        return self.rows
    
    def on_apply(self, widget):
        self.api_key = self.api_row.get_text()
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.data["api_key"] = self.api_key
    
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


class GeminiFlashProvider(GeminiProvider):
    name = "Gemini Flash"
    model = "gemini-1.5-flash"


class GeminiProProvider(GeminiProvider):  
    name = "Gemini Pro"
    model = "gemini-1.5-pro"