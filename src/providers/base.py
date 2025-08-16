import unicodedata
import re
from typing import List, Dict
from gi.repository import Gtk, Adw, GLib
from enum import Enum

class ProviderType(Enum):
    IMAGE = _("Image")
    CHAT = _("Chat")
    VOICE = _("Voice")
    TEXT = _("Text")
    MOVIE = _("Movie")
class BaseProvider:
    name: str
    description: str = ""
    provider_type: ProviderType = ProviderType.CHAT
    languages: List[str] = []
    developer_name: str = "0xMRTT"
    developers = ["0xMRTT https://github.com/0xMRTT"]
    license_type = Gtk.License.GPL_3_0
    data: Dict[str, str] = {}
    has_auth: bool = False
    require_authentification: bool = False
    base_url = "https://github.com/hamonikr/hamonikr-chatbot"
    
    def __init__(self, app, window):
        self.slug = self.slugify(self.name)
        self.copyright = f"© 2023 {self.developer_name}"
        self.url = f"{self.base_url}{self.slug}"

        self.app = app
        self.window = window

        self.data

    @property
    def data(self):
        try:
            return self.app.data["providers"][self.slug]["data"]
        except KeyError:
            # Ollama provider는 기본적으로 활성화
            default_enabled = self.slug == "ollama"
            self.app.data["providers"][self.slug] = {
                "enabled": default_enabled,
                "data": {

                }
            }
        finally:
            return self.app.data["providers"][self.slug]["data"]

    @property
    def enabled(self):
        return  self.app.data["providers"][self.slug]["enabled"]

    def set_enabled(self, status):
        self.app.data["providers"][self.slug]["enabled"] = status

    def ask(self, prompt, chat, stream=False, callback=None):
        """
        Ask the provider to generate a response.
        
        Args:
            prompt: The user's prompt
            chat: The conversation history
            stream: Whether to stream the response
            callback: Callback function for streaming responses (token) -> None
        
        Returns:
            Complete response text (for non-streaming) or None (for streaming)
        """
        raise NotImplementedError()

    def ask_stream(self, prompt, chat, callback=None):
        """
        Stream-enabled version of ask method.
        Default implementation falls back to non-streaming.
        Override this in providers that support streaming.
        
        Args:
            prompt: The user's prompt  
            chat: The conversation history
            callback: Function to call with each token/chunk
        """
        # Fallback to non-streaming for providers that don't support it
        response = self.ask(prompt, chat, stream=False)
        if callback and response:
            callback(response)
        return response

    def load_authentification(self):
        """Must set self.has_auth to True when auth is done"""
        raise NotImplementedError()

    def get_settings_rows(self) -> list:
        return []

    # TOOLS
    def slugify(self, value):
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return re.sub(r'[-\s]+', '-', value)

    def chunk(self, prompt, n=4000):
        if len(prompt) > n:
            prompt = [(prompt[i : i + n]) for i in range(0, len(prompt), n)]
        return prompt

    def open_documentation(self, *args, **kwargs):
        GLib.spawn_command_line_async(
            f"xdg-open {self.url}"
        )
    
    def how_to_get_a_token(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text(_("How to get a token"))
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button
