from .openaigpt35turbo import OpenAIGPT35TurboProvider
from .openaigpt4 import OpenAIGPT4Provider
from .openaigpt4o import OpenAIGPT4oProvider, OpenAIGPT4oMiniProvider
from .openaigpt5 import (
    OpenAIGPT5Provider,
    OpenAIGPT5MiniProvider,
    OpenAIGPT5NanoProvider,
    OpenAIGPT41Provider,
    OpenAIGPT41MiniProvider,
    OpenAIGPT41NanoProvider,
)
from .local import LocalProvider
from .stablediffusion import StableDiffusionProvider 
from .openaiimage import DallE2, DallE3
from .anthropic import ClaudeSonnet4Provider
from .mistral import MistralLargeProvider
from .gemini import GeminiProvider, GeminiFlashProvider, GeminiProProvider
from .perplexity import PerplexityProvider, PerplexitySmallProvider, PerplexityHugeProvider
from .groq import GroqProvider, GroqMixtralProvider, GroqLlama3Provider, GroqGemmaProvider
from .openrouter import OpenRouterProvider, OpenRouterGPT4Provider, OpenRouterClaudeProvider, OpenRouterGeminiProvider
from .ollama import (
    OllamaProvider,
    OllamaLlama3Provider,
    OllamaMistralProvider,
    OllamaGemmaProvider,
    OllamaCodeLlamaProvider,
    OllamaDeepseekProvider
)
from .vllm import VLLMProvider
from .huggingface import (
    HuggingFaceProvider,
    HuggingFaceMistralProvider,
    HuggingFaceZephyrProvider,
    HuggingFaceCodeLlamaProvider
)
from .together import (
    TogetherProvider,
    TogetherMixtralProvider,
    TogetherLlamaProvider,
    TogetherQwenProvider
)

PROVIDERS = {
    OpenAIGPT35TurboProvider,
    OpenAIGPT4Provider,
    OpenAIGPT4oProvider,
    OpenAIGPT4oMiniProvider,
    OpenAIGPT5Provider,
    OpenAIGPT5MiniProvider,
    OpenAIGPT5NanoProvider,
    OpenAIGPT41Provider,
    OpenAIGPT41MiniProvider,
    OpenAIGPT41NanoProvider,
    LocalProvider,
    StableDiffusionProvider,
    DallE2,
    DallE3,
    ClaudeSonnet4Provider,
    MistralLargeProvider,
    GeminiProvider,
    GeminiFlashProvider,
    GeminiProProvider,
    PerplexityProvider,
    PerplexitySmallProvider,
    PerplexityHugeProvider,
    GroqProvider,
    GroqMixtralProvider,
    GroqLlama3Provider,
    GroqGemmaProvider,
    OpenRouterProvider,
    OpenRouterGPT4Provider,
    OpenRouterClaudeProvider,
    OpenRouterGeminiProvider,
    OllamaProvider,
    OllamaLlama3Provider,
    OllamaMistralProvider,
    OllamaGemmaProvider,
    OllamaCodeLlamaProvider,
    OllamaDeepseekProvider,
    VLLMProvider,
    HuggingFaceProvider,
    HuggingFaceMistralProvider,
    HuggingFaceZephyrProvider,
    HuggingFaceCodeLlamaProvider,
    TogetherProvider,
    TogetherMixtralProvider,
    TogetherLlamaProvider,
    TogetherQwenProvider,
}