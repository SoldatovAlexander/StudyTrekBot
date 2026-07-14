import asyncio
import logging

from app.container import get_container
from app.telegram_adapter import build_dispatcher, configure_bot_commands, create_bot


async def run_polling() -> None:
    container = get_container()
    token = container.settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run the Telegram bot.")

    bot = create_bot(token)
    dispatcher = build_dispatcher(container.dialog_manager)
    me = await bot.get_me()
    logging.info("Starting Telegram polling for @%s (%s)", me.username, me.id)
    await bot.delete_webhook(drop_pending_updates=False)
    await configure_bot_commands(bot)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
