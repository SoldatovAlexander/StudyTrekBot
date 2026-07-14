import re

from app.models import StudentProfile


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def merge_profile_from_message(profile: StudentProfile, message: str) -> StudentProfile:
    text = message.lower()
    data = profile.model_dump()

    if message.strip():
        data["free_goal"] = message.strip()

    goal = _detect_goal(text)
    if goal:
        data["goal"] = goal

    target_result = _detect_target_result(text)
    if target_result:
        data["target_result"] = target_result

    technical_level = _detect_technical_level(text)
    if technical_level:
        data["technical_level"] = technical_level

    role = _detect_role(text)
    if role:
        data["role"] = role

    weekly_time = _detect_weekly_time(text)
    if weekly_time:
        data["weekly_time"] = weekly_time

    depth = _detect_depth(text)
    if depth:
        data["depth"] = depth

    known_tools = set(data.get("known_tools") or [])
    priority_topics = set(data.get("priority_topics") or [])
    for tool in _detect_tools(text):
        known_tools.add(tool)
    for topic in _detect_topics(text):
        priority_topics.add(topic)
    data["known_tools"] = sorted(known_tools)
    data["priority_topics"] = sorted(priority_topics)

    if _contains_any(text, ["быстро", "практический результат", "рабочий результат"]):
        data["strategy"] = "quick practical result"
    elif _contains_any(text, ["системно", "с нуля", "разобраться"]):
        data["strategy"] = "systematic foundation"

    return StudentProfile.model_validate(data)


def next_question(profile: StudentProfile) -> str:
    missing = profile.missing_required_fields()
    if "goal" in missing:
        return (
            "Расскажите, чего вы хотите добиться с помощью обучения: применять ИИ в работе, "
            "собрать ассистента, сделать Telegram-бота, автоматизировать процесс или что-то другое?"
        )
    if "technical_level" in missing:
        return "Насколько вам комфортна техническая часть: без программирования, немного Python или уже есть опыт разработки?"
    if "weekly_time" in missing:
        return "Сколько времени в неделю реально готовы выделять, чтобы маршрут был выполнимым?"
    if "target_result" in missing:
        return "Что должно получиться в конце: ассистент, Telegram-бот, автоматизация, рабочий проект или понятная система навыков?"
    if "role" in missing:
        return "В каком контексте хотите применять ИИ: продажи, маркетинг, управление, разработка, аналитика или свой бизнес?"
    return "Данных достаточно, могу собрать черновой маршрут."


def _detect_goal(text: str) -> str | None:
    if _contains_any(text, ["rag", "баз", "знани", "документ"]):
        return "rag_knowledge_base"
    if _contains_any(text, ["телеграм", "telegram", "бот"]):
        return "telegram_bot"
    if _contains_any(text, ["агент"]):
        return "ai_agent"
    if _contains_any(text, ["ассистент", "консультант", "помощник"]):
        return "ai_assistant"
    if _contains_any(text, ["автоматиза", "n8n", "make", "zapier"]):
        return "no_code_automation"
    if _contains_any(text, ["продаж", "маркетинг"]):
        return "commercial_ai_product"
    if _contains_any(text, ["разработ", "приложен", "api"]):
        return "web_ai_app"
    if _contains_any(text, ["использовать ии", "применять ии", "chatgpt", "чатгпт"]):
        return "ai_literacy"
    return None


def _detect_target_result(text: str) -> str | None:
    if _contains_any(text, ["телеграм", "telegram", "бот"]):
        return "создать Telegram-бота с ИИ"
    if _contains_any(text, ["ассистент", "агент", "консультант", "помощник"]):
        return "собрать AI-ассистента"
    if _contains_any(text, ["автоматиза", "n8n", "make", "zapier"]):
        return "настроить автоматизацию без кода"
    if _contains_any(text, ["портфолио", "проект"]):
        return "собрать проект для портфолио или работы"
    if _contains_any(text, ["разобраться", "понять", "использовать"]):
        return "понимать возможности ИИ и применять инструменты"
    return None


def _detect_technical_level(text: str) -> str | None:
    if _contains_any(text, ["не программист", "без программ", "без кода", "no-code", "nocode"]):
        return "beginner"
    if _contains_any(text, ["с нуля", "ничего не знаю", "нович"]):
        return "zero"
    if _contains_any(text, ["python", "пайтон", "немного код", "чуть программ"]):
        return "beginner_to_intermediate"
    if _contains_any(text, ["разработчик", "backend", "бекенд", "api", "пишу код"]):
        return "intermediate"
    if _contains_any(text, ["ml", "data science", "production", "продакш"]):
        return "advanced"
    return None


def _detect_role(text: str) -> str | None:
    if _contains_any(text, ["продаж", "лид", "crm"]):
        return "sales"
    if _contains_any(text, ["маркетинг", "реклам", "контент"]):
        return "marketing"
    if _contains_any(text, ["руковод", "предприним", "бизнес", "коммерчес"]):
        return "business"
    if _contains_any(text, ["продукт", "product"]):
        return "product"
    if _contains_any(text, ["разработчик", "backend", "frontend", "программист"]):
        return "developer"
    if _contains_any(text, ["аналит", "data"]):
        return "analyst"
    if _contains_any(text, ["поддержк", "support"]):
        return "support"
    return None


def _detect_weekly_time(text: str) -> str | None:
    if _contains_any(text, ["интенсив", "каждый день"]):
        return "10+ hours"
    numbers = [int(value) for value in re.findall(r"\d+", text)]
    if not numbers or not _contains_any(text, ["час", "недел", "в неделю"]):
        return None
    max_hours = max(numbers)
    if max_hours <= 2:
        return "up to 2 hours"
    if max_hours <= 5:
        return "3-5 hours"
    if max_hours <= 10:
        return "6-10 hours"
    return "10+ hours"


def _detect_depth(text: str) -> str | None:
    if _contains_any(text, ["коротк", "без лишней теории", "быстро"]):
        return "short practical"
    if _contains_any(text, ["глубок", "техническ", "детально"]):
        return "deep"
    if _contains_any(text, ["сбаланс", "теория плюс практика"]):
        return "balanced"
    return None


def _detect_tools(text: str) -> list[str]:
    tools = []
    mapping = {
        "ChatGPT": ["chatgpt", "чатгпт"],
        "Python": ["python", "пайтон"],
        "API": ["api"],
        "Telegram Bot API": ["telegram", "телеграм"],
        "n8n": ["n8n"],
        "Make": ["make"],
        "Google AI Studio": ["google ai studio"],
        "RAG": ["rag"],
    }
    for tool, needles in mapping.items():
        if _contains_any(text, needles):
            tools.append(tool)
    return tools


def _detect_topics(text: str) -> list[str]:
    topics = []
    mapping = {
        "ai_assistant": ["ассистент", "консультант", "помощник"],
        "ai_agent": ["агент"],
        "telegram_bot": ["telegram", "телеграм", "бот"],
        "no_code_automation": ["автоматиза", "n8n", "make"],
        "sales": ["продаж", "лид", "crm"],
        "marketing": ["маркетинг", "реклам"],
        "rag_knowledge_base": ["rag", "баз", "знани", "документ"],
    }
    for topic, needles in mapping.items():
        if _contains_any(text, needles):
            topics.append(topic)
    return topics

