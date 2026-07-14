from app.telegram_adapter import TELEGRAM_MESSAGE_LIMIT, split_telegram_text, welcome_message


def test_split_telegram_text_keeps_short_message() -> None:
    assert split_telegram_text("короткий текст") == ["короткий текст"]


def test_split_telegram_text_respects_limit() -> None:
    chunks = split_telegram_text(("строка\n" * 900).strip())

    assert len(chunks) > 1
    assert all(len(chunk) <= TELEGRAM_MESSAGE_LIMIT for chunk in chunks)


def test_welcome_message_explains_package_input() -> None:
    text = welcome_message("Расскажите цель.")

    assert "бот-навигатор" in text
    assert "проданный пакет курсов" in text
    assert "Расскажите цель." in text
