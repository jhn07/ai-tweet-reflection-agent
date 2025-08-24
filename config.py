from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class TweetAgentConfig:
    """Configuration for Tweet AI agent"""

    model_name: str = "gpt-4o-mini"
    temperature: float = 0.4
    critique_temperature: float = 0.0
    max_iters: int = 3
    quality_threshold: float = 0.78
    default_language: str = "ru"
    
    # Error handling settings
    request_timeout: int = 120  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    exponential_backoff: bool = True
    
    # Fallback settings
    fallback_enabled: bool = True
    fallback_message: str = "Sorry, an error occurred while generating the tweet. Please try again."


# Global constants
MAX_ITERS_DEFAULT = 3
QUALITY_SCORE_THRESHOLD = 0.78

# Default planned steps for workflow tracking
DEFAULT_PLANNED_STEPS = ["Generation", "Critique", "Rewrite", "Final Review"]

# Multilingual prompts templates
PROMPTS = {
    "ru": {
        "gen_sys": (
            "Ты — автор кратких, информативных твитов. "
            "Пиши до 280 символов, без преамбул, без кавычек. "
            "Добавляй 1–3 релевантных хэштега. Ясный, полезный месседж."
        ),
        "gen_user": "Напиши твит на тему: {topic}",
        "crit_sys": (
            "Ты — строгий редактор твитов.\n"
            "Проверь твит по правилам и верни JSON по схеме: "
            "{needs_revision: bool, issues: string[], tips: string[], score: float 0..1}.\n"
            "Критерии: 1) соответствие теме, 2) информативность/ценность, "
            "3) 1–3 релевантных хэштега, 4) читаемость, 5) ≤280 символов."
        ),
        "crit_user": "Оцени твит и укажи проблемы/советы.\n\nТвит: {tweet}",
        "rewrite_sys": (
            "Ты — редактор твитов. Перепиши твит, исправив замечания редактора.\n"
            "- Сохраняй тон исходного текста (дружелюбный/информативный)\n"
            "- 1–3 релевантных хэштега, не повторяй одинаковые\n"
            "- До 280 символов\n"
            "Верни только готовый твит, без пояснений."
        ),
        "rewrite_user": "Исходный твит:\n{tweet}\n\nЗамечания:\n- {issues}"
    },
    "en": {
        "gen_sys": (
            "You are a concise, informative tweet writer. "
            "Keep it under 280 characters, no preambles/quotes. "
            "Add 1–3 relevant hashtags. Clear, useful message."
        ),
        "gen_user": "Write a tweet about: {topic}",
        "crit_sys": (
            "You are a strict tweet editor.\n"
            "Return JSON with the schema: "
            "{needs_revision: bool, issues: string[], tips: string[], score: float 0..1}.\n"
            "Criteria: 1) topic relevance, 2) informativeness/value, "
            "3) 1–3 relevant hashtags, 4) readability, 5) ≤280 chars."
        ),
        "crit_user": "Evaluate the tweet and list problems/tips.\n\nTweet: {tweet}",
        "rewrite_sys": (
            "You are a tweet editor. Rewrite to address the notes.\n"
            "- Preserve tone (friendly/informative)\n"
            "- 1–3 relevant hashtags, avoid duplicates\n"
            "- ≤280 characters\n"
            "Return only the final tweet, no explanations."
        ),
        "rewrite_user": "Original tweet:\n{tweet}\n\nNotes:\n- {issues}"
    }
}


def get_prompt(lang: str, key: str) -> str:
    """Get prompt for specified language and key"""
    return PROMPTS.get(lang, PROMPTS["ru"]).get(key, "")


def create_llm_models(config: TweetAgentConfig = None) -> tuple[ChatOpenAI, ChatOpenAI]:
    """Create LLM models for generation and critique"""
    if config is None:
        config = TweetAgentConfig()
    
    llm = ChatOpenAI(model=config.model_name, temperature=config.temperature)
    crit_llm = ChatOpenAI(model=config.model_name, temperature=config.critique_temperature)
    
    return llm, crit_llm


# Default settings for initial state
DEFAULT_INITIAL_STATE = {
    "needs_revision": True,
    "iter": 0,
    "max_iters": MAX_ITERS_DEFAULT,
    "language": "ru",
    "steps": [],
    "planned_steps": DEFAULT_PLANNED_STEPS,
}