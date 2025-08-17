from .base import BaseProvider
import requests
import json
from gettext import gettext as _

from gi.repository import Gtk, Adw


class MistralBaseProvider(BaseProvider):
    name = "Mistral"
    description = "Mistral AI API"

    api_key_title = "API Key"
    # 통합: 기본 모델 지정, 설정에서 덮어쓰기 가능
    default_model = "mistral-large-latest"

    def __init__(self, app, window):
        super().__init__(app, window)
        # 저장된 모델 우선, 없으면 기본값
        self.model = self.data.get("model", getattr(self, "model", None) or self.default_model)

    def ask(self, prompt, chat, stream=False, callback=None):
        messages = []
        for c in chat["content"]:
            role = "assistant" if c["role"] == self.app.bot_name else "user"
            content = c["content"].strip()
            if content:  # 빈 메시지 제외
                messages.append({"role": role, "content": content})

        if not self.data.get("api_key"):
            return _("Please configure your Mistral API key in preferences.")

        headers = {
            "Authorization": f"Bearer {self.data.get('api_key', '')}",
            "Content-Type": "application/json",
        }

        # 새 프롬프트를 추가
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }
        
        if stream and callback:
            payload["stream"] = True


        try:
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
                stream=bool(stream and callback)
            )
            
            if stream and callback:
                # Handle streaming response
                if resp.status_code >= 400:
                    try:
                        error_text = resp.text
                        try:
                            data = resp.json()
                            error_info = data.get("error", {})
                            error_msg = error_info.get("message", str(data))
                            error_code = error_info.get("code", "")
                        except:
                            error_msg = error_text
                            error_code = ""
                        
                        if resp.status_code == 500:
                            return _("Mistral AI server error. This may be due to invalid message format. Please try again.")
                        elif "Service unavailable" in error_msg or error_code == "3600":
                            return _("Mistral AI service is temporarily unavailable. Please try again in a few moments.")
                        elif resp.status_code == 401:
                            return _("Your Mistral API key is invalid, please check your preferences.")
                        elif resp.status_code == 429:
                            return _("Rate limit exceeded. Please try again later.")
                        
                        return f"Mistral API Error ({resp.status_code}): {error_msg}"
                    except Exception as e:
                        return f"Mistral API Error: {resp.status_code} - {resp.text}"
                
                full_response = ""
                for line in resp.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and data["choices"]:
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
                if resp.status_code >= 400:
                    try:
                        error_text = resp.text
                        try:
                            data = resp.json()
                            error_info = data.get("error", {})
                            error_msg = error_info.get("message", str(data))
                            error_code = error_info.get("code", "")
                        except:
                            error_msg = error_text
                            error_code = ""
                        
                        if resp.status_code == 500:
                            return _("Mistral AI server error. This may be due to invalid message format. Please try again.")
                        elif resp.status_code == 401:
                            return _("Your Mistral API key is invalid, please check your preferences.")
                        elif resp.status_code == 429:
                            return _("Rate limit exceeded. Please try again later.")
                        elif resp.status_code == 402:
                            return _("Insufficient credits. Please add credits to your Mistral account.")
                        elif "Service unavailable" in error_msg or error_code == "3600":
                            return _("Mistral AI service is temporarily unavailable. Please try again in a few moments.")
                        
                        return f"Mistral API Error ({resp.status_code}): {error_msg}"
                    except:
                        return f"Mistral API Error: {resp.status_code} - {resp.text}"
                
                data = resp.json()
                return data["choices"][0]["message"]["content"]
                
        except requests.exceptions.RequestException:
            return _("I'm having trouble connecting to the API, please check your internet connection.")
        except json.JSONDecodeError as e:
            return f"Mistral API Error: Invalid JSON response - {str(e)}"
        except (KeyError, IndexError) as e:
            return f"Mistral API Error: Unexpected response format - {str(e)}"

    def ask_stream(self, prompt, chat, callback=None):
        """Stream-enabled version for Mistral providers"""
        return self.ask(prompt, chat, stream=True, callback=callback)

    def fetch_models(self):
        """Mistral API에서 사용 가능한 모델 목록을 가져옵니다"""
        try:
            if not self.data.get("api_key"):
                # API 키가 없으면 기본 모델 목록 반환
                return [
                    "mistral-large-latest",
                    "mistral-medium-latest", 
                    "mistral-small-latest",
                    "mistral-tiny",
                    "open-mistral-7b",
                    "open-mixtral-8x7b",
                    "open-mixtral-8x22b",
                    "codestral-latest",
                    "mistral-embed",
                ]

            headers = {
                "Authorization": f"Bearer {self.data.get('api_key', '')}",
                "Content-Type": "application/json",
            }
            
            # Mistral API의 모델 목록 조회 (OpenAI 호환 엔드포인트 시도)
            resp = requests.get(
                "https://api.mistral.ai/v1/models",
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
                
                # 정렬하여 반환
                return sorted(list(dict.fromkeys(models))) or self._get_fallback_models()
            else:
                return self._get_fallback_models()
                
        except Exception:
            return self._get_fallback_models()
    
    def _get_fallback_models(self):
        """API 조회 실패 시 사용할 기본 모델 목록"""
        return [
            "mistral-large-latest",
            "mistral-medium-latest", 
            "mistral-small-latest",
            "mistral-tiny",
            "open-mistral-7b",
            "open-mixtral-8x7b",
            "open-mixtral-8x22b",
            "codestral-latest",
            "mistral-embed",
        ]

    def get_settings_rows(self):
        self.rows = []

        self.api_row = Adw.PasswordEntryRow()
        self.api_row.connect("apply", self.on_apply)
        self.api_row.props.text = self.data.get("api_key") or ""
        self.api_row.props.title = self.api_key_title
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
        api_key = self.api_row.get_text()
        self.data["api_key"] = api_key

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
            self.data["model"] = self.model
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


class MistralLargeProvider(MistralBaseProvider):
    name = "Mistral"
    description = "Mistral AI API"


