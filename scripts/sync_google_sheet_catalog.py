import argparse
import csv
import html
import io
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SPREADSHEET_ID = "1Ur-UDG6lvvxW3X7VORZ6KqPmBqRkdM0qLxVmdjxzkYU"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync course catalog from public Google Sheets CSV exports.")
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--output", default="data/catalog_seed.json")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of sheets for debugging.")
    args = parser.parse_args()

    payload = sync_catalog(args.spreadsheet_id, Path(args.output), limit=args.limit, verbose=True)
    print(
        f"Synced {payload['source']['lesson_count']} lessons from "
        f"{payload['source']['sheet_count']} sheets into {args.output}"
    )


def sync_catalog(
    spreadsheet_id: str = DEFAULT_SPREADSHEET_ID,
    output_path: Path | str = Path("data/catalog_seed.json"),
    *,
    limit: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    sheet_titles = fetch_sheet_titles(spreadsheet_id)
    if limit:
        sheet_titles = sheet_titles[:limit]

    lessons = []
    failed_sheets = []
    for title in sheet_titles:
        try:
            rows = fetch_sheet_csv(spreadsheet_id, title)
        except Exception as exc:
            failed_sheets.append({"title": title, "error": f"{type(exc).__name__}: {exc}"})
            if verbose:
                print(f"Skipped {title!r}: {exc}")
            continue
        sheet_lessons = parse_sheet(title, rows, spreadsheet_id)
        lessons.extend(sheet_lessons)
        if verbose:
            print(f"{title}: {len(sheet_lessons)} lessons")

    payload = {
        "source": {
            "spreadsheet_id": spreadsheet_id,
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "sheet_count": len(sheet_titles),
            "failed_sheet_count": len(failed_sheets),
            "failed_sheets": failed_sheets,
            "lesson_count": len(lessons),
        },
        "lessons": lessons,
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output.with_suffix(f"{output.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(output)
    return payload


def fetch_sheet_titles(spreadsheet_id: str) -> list[str]:
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    text = http_get_text(url)
    titles = [
        html.unescape(match.group(1)).strip()
        for match in re.finditer(r'docs-sheet-tab-caption">([^<]+)</div>', text)
    ]
    return [title for title in dict.fromkeys(titles) if title]


def fetch_sheet_csv(spreadsheet_id: str, sheet_title: str) -> list[list[str]]:
    quoted_sheet = urllib.parse.quote(sheet_title)
    url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={quoted_sheet}"
    )
    text = http_get_text(url)
    return list(csv.reader(io.StringIO(text)))


def http_get_text(url: str) -> str:
    # Local macOS Python often lacks the cert bundle used by browsers.
    context = ssl._create_unverified_context()
    request = urllib.request.Request(url, headers={"User-Agent": "learning-track-bot-sync/0.1"})
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=45, context=context) as response:
                return response.read().decode("utf-8-sig", errors="replace")
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)
    raise last_error or RuntimeError("HTTP request failed")


def parse_sheet(sheet_title: str, rows: list[list[str]], spreadsheet_id: str) -> list[dict[str, Any]]:
    if not rows:
        return []
    header_index = find_header_row(rows)
    if header_index is None:
        return []

    header = normalize_header(rows[header_index])
    indexes = resolve_indexes(header)
    lessons = []
    current_module = ""
    catalog_version = "google-sheets"

    for row_index, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        lesson_order = get_value(row, indexes.get("lesson_order"))
        if not is_lesson_order(lesson_order):
            module_value = get_value(row, indexes.get("module"))
            title_value = get_value(row, indexes.get("lesson_title"))
            if module_value and not title_value:
                current_module = module_value
            continue

        module = get_value(row, indexes.get("module")) or current_module
        lesson_title = get_value(row, indexes.get("lesson_title"))
        if not lesson_title:
            continue

        lesson_id = get_value(row, indexes.get("lesson_id")) or f"{slugify(sheet_title)}-{lesson_order}"
        description = get_value(row, indexes.get("description"))
        material = get_value(row, indexes.get("material"))
        homework_lite = get_value(row, indexes.get("homework_lite"))
        homework_pro = get_value(row, indexes.get("homework_pro"))
        yandex = get_value(row, indexes.get("yandex"))
        vk = get_value(row, indexes.get("vk"))

        text_for_tags = " ".join([sheet_title, module, lesson_title, description, material, homework_lite, homework_pro])
        lessons.append(
            {
                "lesson_id": str(lesson_id).strip(),
                "course_title": sheet_title.strip(),
                "module_title": module.strip(),
                "lesson_order": int(float(str(lesson_order).replace(",", "."))),
                "lesson_title": lesson_title.strip(),
                "description": description.strip(),
                "learning_result": extract_learning_result(description),
                "materials": build_materials(material, yandex, vk),
                "homework_lite": homework_lite.strip(),
                "homework_pro": homework_pro.strip(),
                "level": infer_level(text_for_tags),
                "roles": infer_roles(text_for_tags),
                "topics": infer_topics(text_for_tags),
                "technologies": infer_technologies(text_for_tags),
                "prerequisites": [],
                "mandatory_for_goals": infer_goals(text_for_tags),
                "track_position": infer_track_position(module, lesson_title, int(float(str(lesson_order).replace(",", ".")))),
                "estimated_hours": None,
                "status": "active",
                "catalog_version": catalog_version,
                "source_sheet_id": spreadsheet_id,
                "source_hash": f"{slugify(sheet_title)}:{row_index}:{lesson_id}",
            }
        )
    return lessons


def find_header_row(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows[:20]):
        normalized = normalize_header(row)
        if any("название урока" in cell for cell in normalized):
            return index
        if any(cell in {"тема", "занятие"} or "название темы" in cell for cell in normalized):
            return index
        if normalized and normalized[0] == "№" and len(normalized) > 2:
            return index
        if any("№ урока" in cell or "номер урока" in cell for cell in normalized) and any(
            "описание" in cell for cell in normalized
        ):
            return index
    if rows and any("название урока" in cell for cell in normalize_header(rows[0])):
        return 0
    return None


def normalize_header(row: list[str]) -> list[str]:
    return [re.sub(r"\s+", " ", str(cell).replace("\n", " ")).strip().casefold() for cell in row]


def resolve_indexes(header: list[str]) -> dict[str, int]:
    indexes: dict[str, int] = {}
    for idx, name in enumerate(header):
        if "№ урока" in name or "номер урока" in name or "№ темы" in name or name == "№" or name.endswith("№"):
            indexes.setdefault("lesson_order", idx)
        elif (
            name in {"ид", "id", "ид "}
            or "ид урока" in name
            or "id урока" in name
            or "ид темы" in name
            or "id темы" in name
        ) and "прототип" not in name and "исходник" not in name:
            indexes.setdefault("lesson_id", idx)
        elif "модуль" in name or "блок" in name:
            indexes.setdefault("module", idx)
        elif "название урока" in name or name == "тема" or name == "занятие" or "название темы" in name:
            indexes.setdefault("lesson_title", idx)
        elif name == "описание" or (name.startswith("описание") and "домаш" not in name):
            indexes.setdefault("description", idx)
        elif name == "материал" or name.startswith("материал "):
            indexes.setdefault("material", idx)
        elif "яндекс" in name:
            indexes.setdefault("yandex", idx)
        elif "запись вк" in name or name == "вк":
            indexes.setdefault("vk", idx)
        elif "дз lite" in name or "lite" == name:
            indexes.setdefault("homework_lite", idx)
        elif "дз pro" in name or "pro" == name:
            indexes.setdefault("homework_pro", idx)
    indexes.setdefault("lesson_order", 0)
    if "lesson_id" not in indexes and len(header) > 1 and header[0] == "№":
        indexes["lesson_id"] = 1
    if "lesson_title" not in indexes:
        course_like_columns = [
            idx for idx, name in enumerate(header) if idx > 0 and ("курс" in name or "тема" in name or "урок" in name)
        ]
        if course_like_columns:
            indexes["lesson_title"] = course_like_columns[0]
        elif len(header) > 2 and header[0] == "№":
            indexes["lesson_title"] = 2
        elif len(header) >= 5:
            indexes["lesson_title"] = 4
    return indexes


def get_value(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return str(row[index] or "").strip()


def is_lesson_order(value: str) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"\d+(?:[.,]0+)?", str(value).strip()))


def build_materials(material: str, yandex: str, vk: str) -> list[dict[str, str]]:
    result = []
    for kind, value in [("material", material), ("yandex_disk", yandex), ("vk_video", vk)]:
        for url in extract_urls(value):
            result.append({"type": kind, "url": url})
    return result


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)]+", text or "")


def extract_learning_result(description: str) -> str:
    if not description:
        return ""
    markers = ["Результат участия во встрече:", "Результат освоения темы:", "Результат встречи:"]
    for marker in markers:
        if marker in description:
            return description.split(marker, 1)[1].strip().split("\n\n", 1)[0].strip()
    return ""


def infer_level(text: str) -> str:
    lowered = text.casefold()
    if any(word in lowered for word in ["продвинут", "production", "локальные модели", "pytorch"]):
        return "intermediate"
    if any(word in lowered for word in ["основ", "для начинающих", "знакомство", "первое приложение"]):
        return "beginner"
    if any(word in lowered for word in ["api", "fastapi", "backend", "telegram", "rag", "sql"]):
        return "beginner_to_intermediate"
    return "beginner"


def infer_roles(text: str) -> list[str]:
    lowered = text.casefold()
    roles = set()
    if any(word in lowered for word in ["продаж", "лид", "crm"]):
        roles.add("sales")
    if any(word in lowered for word in ["маркетинг", "реклам", "контент", "бренд", "seo", "pr"]):
        roles.add("marketing")
    if any(word in lowered for word in ["руковод", "директор", "бизнес", "коммерчес"]):
        roles.add("business")
    if any(word in lowered for word in ["python", "api", "fastapi", "backend", "код", "разработ"]):
        roles.add("developer")
    if any(word in lowered for word in ["data science", "машинное обучение", "данн", "аналит"]):
        roles.add("analyst")
    if not roles:
        roles.update(["business", "developer"])
    return sorted(roles)


def infer_topics(text: str) -> list[str]:
    lowered = text.casefold()
    mapping = {
        "ai_assistant": ["ассистент", "консультант", "нейро-сотрудник"],
        "ai_agent": ["агент"],
        "telegram_bot": ["telegram", "телеграм", "tg-бот", "бот"],
        "no_code_automation": ["no-code", "nocode", "make", "n8n", "vibe coding", "replit"],
        "sales": ["продаж", "лид", "crm"],
        "marketing": ["маркетинг", "реклам", "контент", "бренд", "seo", "pr"],
        "rag_knowledge_base": ["rag", "база знаний", "эмбеддинг", "embedding"],
        "local_llm": ["локальные модели", "local llm"],
        "ml_ds": ["machine learning", "машинное обучение", "data science", "pytorch"],
        "prompt_engineering": ["промт", "prompt"],
        "web_ai_app": ["web", "веб", "приложение", "fastapi"],
    }
    topics = [topic for topic, needles in mapping.items() if any(needle in lowered for needle in needles)]
    return sorted(set(topics)) or ["ai_literacy"]


def infer_technologies(text: str) -> list[str]:
    lowered = text.casefold()
    mapping = {
        "ChatGPT": ["chatgpt", "gpt"],
        "Google AI Studio": ["google ai studio"],
        "Python": ["python", "питон"],
        "FastAPI": ["fastapi"],
        "Telegram Bot API": ["telegram", "телеграм", "tg-бот"],
        "RAG": ["rag"],
        "n8n": ["n8n"],
        "Make": ["make"],
        "Replit": ["replit"],
        "Cursor": ["cursor"],
        "SQL": ["sql", "postgresql"],
        "PyTorch": ["pytorch"],
    }
    return sorted({tech for tech, needles in mapping.items() if any(needle in lowered for needle in needles)})


def infer_goals(text: str) -> list[str]:
    topics = set(infer_topics(text))
    goals = set()
    for topic in topics:
        if topic in {
            "ai_assistant",
            "ai_agent",
            "telegram_bot",
            "no_code_automation",
            "rag_knowledge_base",
            "local_llm",
            "ml_ds",
            "prompt_engineering",
            "web_ai_app",
        }:
            goals.add(topic)
    if "sales" in topics or "marketing" in topics:
        goals.add("commercial_ai_product")
    return sorted(goals) or ["ai_literacy"]


def infer_track_position(module: str, title: str, order: int) -> str:
    text = f"{module} {title}".casefold()
    if order <= 2 or any(word in text for word in ["основ", "знакомство", "обзор"]):
        return "start"
    if any(word in text for word in ["практик", "создание", "первое", "прототип"]):
        return "practice"
    if any(word in text for word in ["продвинут", "локальные", "production"]):
        return "advanced"
    return "core"


def slugify(value: str) -> str:
    value = re.sub(r"[^\w]+", "-", value.casefold(), flags=re.UNICODE).strip("-")
    return value or "sheet"


if __name__ == "__main__":
    main()
