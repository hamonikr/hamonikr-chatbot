from .baseimage import BaseImageProvider
import openai
from openai import OpenAI
import socket
import os
import json
import io
import base64
import requests
from PIL import Image, UnidentifiedImageError
from gettext import gettext as _

from gi.repository import Gtk, Adw, GLib


class BaseOpenAIImageProvider(BaseImageProvider):
    model = None
    api_key_title = "API Key"

    def __init__(self, app, window):
        super().__init__(app, window)

        try:
            self.client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
            )
        except openai.OpenAIError:
            self.client = OpenAI(
                api_key="",
            )

        if self.data.get("api_key"):
            self.client.api_key = self.data["api_key"]
        if self.data.get("api_base"):
            self.client.base_url = self.data["api_base"]

    def ask(self, prompt, chat):
        if not self.model:
            return _("No model selected, you can choose one in preferences")

        # 이미지 생성은 프롬프트를 문자열로 전달해야 함
        prompt_str = str(prompt)

        # 모델별 안전한 파라미터 구성
        kwargs = {
            "model": self.model,
            "prompt": prompt_str,
        }
        # DALL·E 계열은 size/quality/n 지원, gpt-image-1은 최소 인자만 사용
        if self.model in ("dall-e-2", "dall-e-3"):
            kwargs["size"] = "1024x1024"
            if self.model == "dall-e-2":
                kwargs["quality"] = "standard"
                kwargs["n"] = 1

        try:
            response = self.client.images.generate(**kwargs)

            data0 = response.data[0] if getattr(response, "data", None) else None
            image_bytes = None

            # gpt-image-1: b64_json 제공
            b64 = getattr(data0, "b64_json", None)
            if b64:
                try:
                    image_bytes = base64.b64decode(b64)
                except Exception:
                    image_bytes = None

            # DALL·E: url 제공
            if image_bytes is None:
                image_url = getattr(data0, "url", None)
                if image_url:
                    image_bytes = requests.get(image_url, timeout=30).content

            if image_bytes:
                try:
                    return Image.open(io.BytesIO(image_bytes))
                except UnidentifiedImageError:
                    try:
                        error = json.loads(image_bytes).get("error")
                        return str(error)
                    except Exception:
                        return _("Failed to decode image data")
            return None

        except openai.AuthenticationError:
            return _("Your API key is invalid, please check your preferences.")
        except openai.BadRequestError as e:
            return _("You don't have access to this model, please check your plan and billing details.")
        except openai.RateLimitError:
            return _("You exceeded your current quota, please check your plan and billing details.")
        except openai.APIConnectionError:
            return _("I'm having trouble connecting to the API, please check your internet connection.")
        except socket.gaierror:
            return _("I'm having trouble connecting to the API, please check your internet connection.")


    def get_settings_rows(self):
        self.rows = []


        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.client.api_key or ""
        self.api_row.props.title = self.api_key_title
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_get_a_token())
        self.rows.append(self.api_row)

        self.api_url_row = Adw.EntryRow()
        self.api_url_row.connect("apply", self.on_apply)
        self.api_url_row.props.text=str(self.client.base_url) or ""
        self.api_url_row.props.title = "API Url"
        self.api_url_row.set_show_apply_button(True)
        self.api_url_row.add_suffix(self.how_to_get_base_url())
        self.rows.append(self.api_url_row)

        return self.rows

    def on_apply(self, widget):
        api_key = self.api_row.get_text()
        self.client.api_key = api_key
        self.client.base_url = self.api_url_row.get_text()

        self.data["api_key"] = self.client.api_key
        self.data["api_base"] = str(self.client.base_url)


    def how_to_get_base_url(self):
        about_button = Gtk.Button()
        about_button.set_icon_name("dialog-information-symbolic")
        about_button.set_tooltip_text("How to choose base url")
        about_button.add_css_class("flat")
        about_button.set_valign(Gtk.Align.CENTER)
        about_button.connect("clicked", self.open_documentation)
        return about_button

class DallE2(BaseOpenAIImageProvider):
    name = "DALL·E 2"
    model = "dall-e-2"
    description = "DALL·E is a AI system that can create realistic images and art from a description in natural language. "

class DallE3(BaseOpenAIImageProvider):
    name = "DALL·E 3"
    model = "dall-e-3"
    description = "DALL·E is a AI system that can create realistic images and art from a description in natural language. "