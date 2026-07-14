from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)

from app.dialog_manager import DialogManager
from app.models import StudentProfile


TELEGRAM_MESSAGE_LIMIT = 4096


def welcome_message(next_question: str) -> str:
    return (
        "Здравствуйте. Я бот-навигатор по обучению УИИ.\n\n"
        "Я помогу собрать персональный порядок прохождения курсов: что пройти сначала, "
        "что оставить как факультатив и какой результат будет на каждом этапе.\n\n"
        "Можно написать цель своими словами или вставить уже проданный пакет курсов. Например:\n"
        "Клиент купил: Разработчик AI агентов, AI-консультант и нейро-продажник. "
        "Цель: AI-ассистент для продаж без глубокого программирования. Время: 3-4 часа в неделю.\n\n"
        f"{next_question}"
    )


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новый трек"), KeyboardButton(text="Мой профиль")],
            [KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
    )


async def send_text(message: Message, text: str, *, with_keyboard: bool = True) -> None:
    reply_markup = main_keyboard() if with_keyboard else ReplyKeyboardRemove()
    chunks = split_telegram_text(text)
    for index, chunk in enumerate(chunks):
        await message.answer(chunk, reply_markup=reply_markup if index == len(chunks) - 1 else None)


def split_telegram_text(text: str) -> list[str]:
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > TELEGRAM_MESSAGE_LIMIT:
        split_at = remaining.rfind("\n", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_at < TELEGRAM_MESSAGE_LIMIT // 2:
            split_at = TELEGRAM_MESSAGE_LIMIT
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def render_profile(profile: StudentProfile) -> str:
    fields = [
        ("Цель", profile.goal),
        ("Результат", profile.target_result),
        ("Технический уровень", profile.technical_level),
        ("Контекст", profile.role),
        ("Время в неделю", profile.weekly_time),
        ("Глубина", profile.depth),
        ("Инструменты", ", ".join(profile.known_tools) if profile.known_tools else None),
        ("Приоритеты", ", ".join(profile.priority_topics) if profile.priority_topics else None),
        ("Пакет", profile.package_name),
        ("Купленные курсы", ", ".join(profile.available_course_titles) if profile.available_course_titles else None),
        (
            "Не сопоставлено",
            ", ".join(profile.unmatched_course_titles) if profile.unmatched_course_titles else None,
        ),
    ]
    lines = ["Текущий профиль"]
    for title, value in fields:
        lines.append(f"{title}: {value or 'не указано'}")
    if profile.missing_required_fields():
        lines.extend(["", f"Не хватает: {', '.join(profile.missing_required_fields())}"])
    else:
        lines.extend(["", "Данных достаточно для сборки трека."])
    return "\n".join(lines)


def build_dispatcher(dialog_manager: DialogManager) -> Dispatcher:
    router = Router()

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        user_id = str(message.from_user.id if message.from_user else message.chat.id)
        response = dialog_manager.reset(user_id)
        await send_text(message, welcome_message(response.reply))

    @router.message(Command("newtrack"))
    async def new_track(message: Message) -> None:
        user_id = str(message.from_user.id if message.from_user else message.chat.id)
        response = dialog_manager.reset(user_id)
        await send_text(message, response.reply)

    @router.message(Command("help"))
    async def help_message(message: Message) -> None:
        await send_text(
            message,
            "Опишите цель обучения свободным текстом. Я задам несколько уточнений и соберу персональный трек.\n\n"
            "Команды:\n"
            "/newtrack — начать новый маршрут\n"
            "/profile — показать собранный профиль\n"
            "/status — проверить каталог\n"
            "/help — помощь",
        )

    @router.message(Command("profile"))
    async def profile_message(message: Message) -> None:
        user_id = str(message.from_user.id if message.from_user else message.chat.id)
        await send_text(message, render_profile(dialog_manager.database.get_profile(user_id)))

    @router.message(Command("status"))
    async def status_message(message: Message) -> None:
        status = dialog_manager.catalog.status()
        await send_text(
            message,
            "Статус каталога\n"
            f"Активных материалов: {status['active_lessons']}\n"
            f"Версия: {status['catalog_version']}",
        )

    @router.message()
    async def handle_text(message: Message) -> None:
        if not message.text:
            await send_text(message, "Пока я понимаю только текстовые сообщения. Опишите цель обучения словами.")
            return
        user_id = str(message.from_user.id if message.from_user else message.chat.id)
        normalized = message.text.strip().lower()
        if normalized in {"новый трек", "начать заново"}:
            response = dialog_manager.reset(user_id)
            await send_text(message, response.reply)
            return
        if normalized in {"помощь", "help"}:
            await help_message(message)
            return
        if normalized in {"мой профиль", "профиль"}:
            await profile_message(message)
            return

        response = await dialog_manager.handle_message(user_id, message.text)
        await send_text(message, response.reply)

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    return dispatcher


class TelegramWebhookHandler:
    def __init__(self, bot_token: str, dialog_manager: DialogManager) -> None:
        self.bot = create_bot(bot_token)
        self.dispatcher = build_dispatcher(dialog_manager)

    async def feed_update(self, payload: dict) -> None:
        update = Update.model_validate(payload, context={"bot": self.bot})
        await self.dispatcher.feed_update(self.bot, update)


def create_bot(bot_token: str) -> Bot:
    return Bot(token=bot_token, default=DefaultBotProperties(parse_mode=None))


async def configure_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать диалог"),
            BotCommand(command="newtrack", description="Собрать новый трек"),
            BotCommand(command="profile", description="Показать профиль"),
            BotCommand(command="status", description="Статус каталога"),
            BotCommand(command="help", description="Помощь"),
        ]
    )
