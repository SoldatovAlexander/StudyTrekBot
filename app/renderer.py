from app.models import GeneratedTrack


def render_track(track: GeneratedTrack) -> str:
    lines = [
        "Ваш персональный трек",
        "",
        f"Цель: {track.goal}",
        "",
        f"Логика: {track.route_logic}",
        "",
    ]

    for index, stage in enumerate(track.stages, start=1):
        lines.extend(
            [
                f"Этап {index}. {stage.title}",
                stage.why,
                "Материалы:",
            ]
        )
        for lesson in stage.materials:
            lines.append(f"- {lesson.course_title}: {lesson.lesson_title}")
        lines.extend(["Результат:", stage.expected_result, ""])

    if track.mandatory:
        lines.append("Обязательное:")
        for lesson in track.mandatory:
            lines.append(f"- {lesson.course_title}: {lesson.lesson_title}")
        lines.append("")

    if track.optional:
        lines.append("Дополнительно:")
        for lesson in track.optional:
            lines.append(f"- {lesson.course_title}: {lesson.lesson_title}")
        lines.append("")

    if track.skipped_now:
        lines.append("Что можно пропустить сейчас:")
        for item in track.skipped_now:
            lines.append(f"- {item}")
        lines.append("")

    lines.extend(
        [
            f"Ориентировочная длительность: {track.estimated_duration}.",
            f"Актуальность каталога: {track.catalog_version}.",
        ]
    )
    return "\n".join(lines)

