from .openai import BaseOpenAIProvider


class OpenAIGPT5Provider(BaseOpenAIProvider):
    name = "OpenAI GPT-5"
    description = "최신 GPT-5 플래그십 모델"
    model = "gpt-5"


class OpenAIGPT5MiniProvider(BaseOpenAIProvider):
    name = "OpenAI GPT-5 mini"
    description = "경량·고속 GPT-5 mini"
    model = "gpt-5-mini"


class OpenAIGPT5NanoProvider(BaseOpenAIProvider):
    name = "OpenAI GPT-5 nano"
    description = "초경량 GPT-5 nano"
    model = "gpt-5-nano"


class OpenAIGPT41Provider(BaseOpenAIProvider):
    name = "OpenAI GPT-4.1"
    description = "향상된 추론과 코딩 성능의 GPT-4.1"
    model = "gpt-4.1"


class OpenAIGPT41MiniProvider(BaseOpenAIProvider):
    name = "OpenAI GPT-4.1 mini"
    description = "가벼운 비용의 GPT-4.1 mini"
    model = "gpt-4.1-mini"


class OpenAIGPT41NanoProvider(BaseOpenAIProvider):
    name = "OpenAI GPT-4.1 nano"
    description = "디바이스 친화적 GPT-4.1 nano"
    model = "gpt-4.1-nano"


