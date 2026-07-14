from app.course_matcher import CourseMatcher


class NoLLMClient:
    is_configured = False


def test_course_matcher_local_match_exact_titles() -> None:
    matcher = CourseMatcher(NoLLMClient())
    matched, unmatched, package_name = awaitable(
        matcher.match(
            "Клиент купил: Разработчик AI агентов и No-code автоматизация",
            ["Разработчик AI агентов", "No-code автоматизация", "RAG и базы знаний"],
        )
    )

    assert matched == ["Разработчик AI агентов", "No-code автоматизация"]
    assert unmatched == []
    assert package_name is None


def test_course_matcher_drops_catalog_titles_from_unmatched() -> None:
    matcher = CourseMatcher(NoLLMClient())

    assert matcher._unmatched_titles(
        ["RAG и базы знаний", "Новый неизвестный курс"],
        ["RAG и базы знаний", "No-code автоматизация"],
    ) == ["Новый неизвестный курс"]


def awaitable(coro):
    import asyncio

    return asyncio.run(coro)
