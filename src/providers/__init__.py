from .openai import OpenAIProvider
from .stablediffusion import StableDiffusionProvider 
from .openaiimage import DallE2, DallE3
from .anthropic import AnthropicProvider
from .mistral import MistralLargeProvider
from .gemini import GeminiProvider
from .perplexity import PerplexityProvider
from .groq import GroqProvider
from .openrouter import OpenRouterProvider
from .ollama import (
    OllamaProvider,
)
from .vllm import VLLMProvider
from .huggingface import (
    HuggingFaceProvider,
)
from .together import (
    TogetherProvider,
)

PROVIDERS = {
    # 통합형 프로바이더(벤더 단일 항목만 노출)
    OpenAIProvider,
    AnthropicProvider,
    MistralLargeProvider,  # 라벨은 "Mistral"
    GeminiProvider,
    GroqProvider,
    PerplexityProvider,
    OpenRouterProvider,
    HuggingFaceProvider,
    OllamaProvider,

    # 로컬/이미지/기타
    StableDiffusionProvider,
    DallE2,
    DallE3,
    VLLMProvider,
    TogetherProvider,
}