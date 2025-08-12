from .openai import BaseOpenAIProvider


class OpenAIGPT4oProvider(BaseOpenAIProvider):
    name = "OpenAI GPT-4o"
    description = "OpenAI의 최신 멀티모달 플래그십 모델로, 고품질 대화에 최적화되어 있습니다."
    model = "gpt-4o"


class OpenAIGPT4oMiniProvider(BaseOpenAIProvider):
    name = "OpenAI GPT-4o mini"
    description = "저비용·고속 경량 모델로 일상 대화와 도구 연동에 적합합니다."
    model = "gpt-4o-mini"


