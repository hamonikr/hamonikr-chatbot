import json
import socket
import requests
import uuid
import time
from gettext import gettext as _
from gi.repository import Gtk, Adw

from .base import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = "OpenRouter"
    description = _("여러 벤더의 모델을 통합 라우팅")
    default_model = "openai/gpt-oss-20b:free"
    api_key_title = "API Key"
    base_url = "https://openrouter.ai/api/v1"
    
    def __init__(self, app, window):
        super().__init__(app, window)
        
        self.api_key = self.data.get("api_key", "")
        self.site_url = self.data.get("site_url", "https://github.com/hamonikr/hamonikr-chatbot")
        self.site_name = self.data.get("site_name", "HamoniKR Chatbot")
        self.model = self.data.get("model", self.default_model)
        
        # 모델이 설정되지 않았다면 기본 모델로 설정
        if not self.data.get("model"):
            self.data["model"] = self.default_model
        

    def get_active_api_key(self):
        """사용자가 설정한 API 키를 반환합니다."""
        return self.api_key.strip() if self.api_key else ""

    
    def ask(self, prompt, chat, stream=False, callback=None):
        # 사용할 API 키 결정
        active_key = self.get_active_api_key()
        if not active_key:
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
            "Authorization": f"Bearer {active_key}",
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
        
        if stream and callback:
            data["stream"] = True
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
                stream=bool(stream and callback)
            )
            
            if response.status_code == 401:
                return _("Your API key is invalid, please check your preferences.")
            elif response.status_code == 429:
                return _("Rate limit exceeded. Please try again later.")
            elif response.status_code == 402:
                return _("Insufficient credits. Please add credits to your account.")
            elif response.status_code == 200:
                if stream and callback:
                    # Handle streaming response
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data_str = line[6:]
                                if data_str == '[DONE]':
                                    break
                                try:
                                    data = json.loads(data_str)
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            content = delta["content"]
                                            full_response += content
                                            callback(content)
                                except json.JSONDecodeError:
                                    continue
                    return full_response
                else:
                    # Regular non-streaming response
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

    def ask_stream(self, prompt, chat, callback=None):
        """Stream-enabled version for OpenRouter providers"""
        return self.ask(prompt, chat, stream=True, callback=callback)

    def fetch_models(self):
        """OpenRouter API에서 사용 가능한 모델 목록을 가져옵니다"""
        try:
            # 사용할 API 키 결정
            active_key = self.get_active_api_key()
            if not active_key:
                return self._get_fallback_models()

            headers = {
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.site_url,
                "X-Title": self.site_name
            }
            
            # OpenRouter API의 모델 목록 조회
            resp = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for model in data.get("data", []):
                    model_id = model.get("id")
                    if model_id:
                        models.append(model_id)
                
                # 인기 모델 우선 정렬
                return self._sort_models(models) or self._get_fallback_models()
            else:
                return self._get_fallback_models()
                
        except Exception:
            return self._get_fallback_models()
    
    def _get_fallback_models(self):
        """API 조회 실패 시 사용할 기본 모델 목록"""
        return [
            # 무료 모델 (최우선)
            "openai/gpt-oss-20b:free",
            "gpt-oss:free",
            # Anthropic Claude
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-haiku",
            # OpenAI GPT
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/gpt-4-turbo",
            "openai/gpt-3.5-turbo",
            # Google Gemini
            "google/gemini-pro-1.5",
            "google/gemini-flash-1.5",
            # Meta Llama
            "meta-llama/llama-3.2-90b-vision-instruct",
            "meta-llama/llama-3.1-405b-instruct",
            # Mistral
            "mistralai/mistral-large",
            "mistralai/mistral-medium",
            # Cohere
            "cohere/command-r-plus",
            "cohere/command-r",
        ]
    
    def _sort_models(self, models):
        """모델을 인기도/카테고리별로 정렬합니다"""
        if not models:
            return []
        
        # 인기 모델 우선순위 정의 (무료 모델 최우선)
        priority_models = [
            "openai/gpt-oss-20b:free",  # 무료 모델 최우선
            "gpt-oss:free",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4o-mini", 
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-405b-instruct",
            "mistralai/mistral-large",
        ]
        
        # 우선순위 모델을 먼저 배치
        sorted_models = []
        remaining_models = list(models)
        
        for priority_model in priority_models:
            if priority_model in remaining_models:
                sorted_models.append(priority_model)
                remaining_models.remove(priority_model)
        
        # 나머지 모델은 알파벳 순으로 정렬하여 추가
        sorted_models.extend(sorted(remaining_models))
        
        return sorted_models
    
    def get_settings_rows(self):
        self.rows = []
        
        # API 키 설정 안내
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small>OpenRouter를 사용하려면 개인 API 키를 설정하세요.</small>"
        )
        info_label.set_wrap(True)
        info_label.add_css_class("dim-label")
        self.rows.append(info_label)
        
        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.api_key or ""
        self.api_row.props.title = self.api_key_title
        # subtitle 설정을 hasattr로 안전하게 체크
        if hasattr(self.api_row.props, 'subtitle'):
            try:
                self.api_row.props.subtitle = "OpenRouter API 키를 입력하세요"
            except:
                pass
        self.api_row.set_show_apply_button(True)
        self.api_row.add_suffix(self.how_to_get_a_token())
        self.rows.append(self.api_row)
        
        # 모델 드롭다운 (동적 조회 + 폴백)
        model_choices = self.fetch_models() + ["Custom…"]
        self.model_combo = Adw.ComboRow()
        self.model_combo.set_title(_("Model"))
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
            idx = len(model_choices) - 1  # Custom…
        self.model_combo.set_selected(idx)
        try:
            self.model_combo.set_tooltip_text(model_choices[idx])
        except Exception:
            pass
        self.model_combo.connect("notify::selected", self.on_model_combo_changed)
        self.rows.append(self.model_combo)

        # Custom 입력용 EntryRow (Custom…일 때만 표시)
        self.model_row = Adw.EntryRow()
        self.model_row.connect("apply", self.on_apply_model_custom)
        self.model_row.props.text = self.model if idx == len(model_choices) - 1 else ""
        self.model_row.props.title = _("Custom model id")
        self.model_row.set_show_apply_button(True)
        self.model_row.set_visible(idx == len(model_choices) - 1)
        self.rows.append(self.model_row)

        return self.rows
    
    def on_apply(self, widget):
        self.api_key = self.api_row.get_text()
        self.data["api_key"] = self.api_key

    def on_model_combo_changed(self, combo, _pspec=None):
        selected = combo.get_selected()
        if selected < 0:
            return
        model_choices = self.fetch_models() + ["Custom…"]
        choice = model_choices[selected]
        is_custom = (choice == "Custom…")
        self.model_row.set_visible(is_custom)
        if not is_custom:
            self.model = choice
            self.data["model"] = choice
        # 항상 툴팁에 전체 모델명을 노출
        try:
            self.model_combo.set_tooltip_text(choice)
        except Exception:
            pass

    def on_apply_model_custom(self, widget):
        text = self.model_row.get_text().strip()
        if text:
            self.model = text
            self.data["model"] = self.model

    def get_available_models(self):
        """외부에서 사용할 수 있는 모델 목록을 반환합니다"""
        return self.fetch_models()
    
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
    default_model = "openai/gpt-4-turbo"


class OpenRouterClaudeProvider(OpenRouterProvider):
    name = "OpenRouter Claude"
    default_model = "anthropic/claude-3.5-sonnet"


class OpenRouterGeminiProvider(OpenRouterProvider):
    name = "OpenRouter Gemini"
    default_model = "google/gemini-pro-1.5"
