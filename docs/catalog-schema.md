# Нормализованный каталог курсов

Текущая Google-таблица содержит много вкладок с курсами и учебными блоками. Колонки на вкладках похожи, но не полностью одинаковы: где-то есть модуль, где-то блок, где-то отдельное видео, где-то измененное описание. Поэтому для бота нужен нормализованный каталог, который отделяет исходные данные от полей маршрутизации.

## Цель нормализации

Нормализация нужна, чтобы бот мог:

- выбирать материалы под цель слушателя;
- сортировать уроки и курсы в логичном порядке;
- отличать обязательные материалы от факультативных;
- учитывать уровень подготовки и prerequisites;
- объяснять слушателю, зачем нужен каждый этап.

Каталог должен считаться динамическим. Google-таблица может меняться, поэтому нормализованные записи должны хранить связь с исходной строкой, статус актуальности и версию синхронизации.

## Уровни данных

Каталог лучше хранить в трех уровнях:

1. Курс.
2. Модуль или блок внутри курса.
3. Урок или материал.

Для MVP можно начать с уровня уроков, потому что именно уроки содержат описания, материалы и ДЗ. Курс и модуль будут контекстом для урока.

## Сущность `course`

```json
{
  "course_id": "442873",
  "course_title": "Разработчик AI агентов",
  "source_sheet_name": "Разработчик AI агентов",
  "source_sheet_id": 1023357165,
  "package_names": ["AI-разработка", "AI-агенты"],
  "course_type": "main",
  "primary_audience": ["developer", "business", "beginner"],
  "primary_goal": ["создание AI-агентов", "AI-приложения"],
  "default_level": "beginner_to_intermediate",
  "estimated_duration_hours": null,
  "status": "active",
  "catalog_version": "2026-06-04T14:00:00+03:00",
  "source_hash": "..."
}
```

### Поля курса

| Поле | Назначение |
| --- | --- |
| `course_id` | ID курса, если он указан в таблице или LMS |
| `course_title` | Название курса |
| `source_sheet_name` | Название вкладки в Google Sheets |
| `source_sheet_id` | Стабильный ID вкладки Google Sheets |
| `package_names` | Пакеты, в которые входит курс |
| `course_type` | `main`, `optional`, `faculty`, `legacy`, `support` |
| `primary_audience` | Основные аудитории |
| `primary_goal` | Для каких целей курс подходит |
| `default_level` | Базовый уровень сложности курса |
| `estimated_duration_hours` | Оценка длительности, если доступна |
| `status` | `active`, `new`, `changed`, `deleted`, `needs_review` |
| `catalog_version` | Версия или дата синхронизации каталога |
| `source_hash` | Хеш исходного содержимого для поиска изменений |

## Сущность `module`

```json
{
  "module_id": "442873-vibe-coding",
  "course_id": "442873",
  "module_title": "Vibe coding",
  "module_order": 1,
  "module_goal": "быстрое прототипирование AI-приложений",
  "module_level": "beginner",
  "is_optional": false
}
```

### Поля модуля

| Поле | Назначение |
| --- | --- |
| `module_id` | Внутренний ID модуля |
| `course_id` | Связь с курсом |
| `module_title` | Название модуля или блока |
| `module_order` | Порядок внутри курса |
| `module_goal` | Зачем нужен модуль |
| `module_level` | Уровень сложности |
| `is_optional` | Факультативный ли модуль |

## Сущность `lesson`

```json
{
  "lesson_id": "2235",
  "course_id": "442873",
  "module_id": "442873-vibe-coding",
  "lesson_order": 1,
  "lesson_title": "Обзор Google AI Studio: интерфейс и основные возможности",
  "description": "Знакомство с Google AI Studio и методологией vibe coding.",
  "learning_result": "Слушатель сможет спроектировать и запустить простой AI-прототип.",
  "materials": [
    {
      "type": "drive_folder",
      "url": "https://drive.google.com/..."
    }
  ],
  "homework_lite": "Создать первый AI-ассистент от идеи к прототипу.",
  "homework_pro": null,
  "source_links": {
    "yandex_disk": ["https://disk.yandex.ru/..."],
    "vk_video": ["https://vkvideo.ru/..."]
  },
  "routing": {
    "level": "beginner",
    "roles": ["business", "developer", "product"],
    "topics": ["Google AI Studio", "vibe coding", "AI assistant"],
    "technologies": ["Google AI Studio"],
    "skills": ["прототипирование", "проектирование интерфейса", "промптинг"],
    "prerequisites": [],
    "next_recommended": ["2236"],
    "mandatory_for_goals": ["создание AI-агентов", "AI-приложения"],
    "optional_for_goals": ["маркетинг", "продажи"],
    "difficulty": 1,
    "estimated_hours": null,
    "track_position": "start"
  },
  "source_raw": {
    "row_number": 3,
    "source_sheet_name": "Разработчик AI агентов",
    "source_sheet_id": 1023357165,
    "source_hash": "...",
    "synced_at": "2026-06-04T14:00:00+03:00",
    "status": "active",
    "original_columns": {}
  }
}
```

### Поля урока

| Поле | Назначение |
| --- | --- |
| `lesson_id` | ID урока из таблицы или LMS |
| `course_id` | Курс, к которому относится урок |
| `module_id` | Модуль или блок |
| `lesson_order` | Порядок в курсе |
| `lesson_title` | Название урока |
| `description` | Описание занятия |
| `learning_result` | Что слушатель сможет после урока |
| `materials` | Материалы занятия |
| `homework_lite` | Базовое практическое задание |
| `homework_pro` | Продвинутое задание |
| `source_links` | Видео, Яндекс Диск, Google Drive и другие ссылки |
| `routing` | Поля, по которым бот строит маршрут |
| `source_raw` | Исходная строка и оригинальные данные для проверки |

## Статусы записей

| Статус | Значение |
| --- | --- |
| `active` | Запись актуальна и может использоваться в треках |
| `new` | Запись появилась после последней синхронизации и еще не проверена |
| `changed` | Запись изменилась, нужно обновить нормализованные поля |
| `deleted` | Запись исчезла из исходной таблицы и не должна попадать в новые треки |
| `needs_review` | LLM не уверена в тегах или prerequisites, нужна ручная проверка |

## Правила обновления

1. Синхронизация читает все вкладки таблицы.
2. Каждая строка получает `source_hash`.
3. Если хеш изменился, запись получает статус `changed`.
4. Если строка появилась впервые, запись получает статус `new`.
5. Если строка исчезла, старая нормализованная запись получает статус `deleted`.
6. Новые и измененные записи проходят нормализацию.
7. В генерацию треков попадают только записи `active`.

## Справочники для маршрутизации

### Уровень

```text
zero
beginner
beginner_to_intermediate
intermediate
advanced
expert
```

### Роли

```text
business
marketing
sales
manager
product
developer
data_scientist
analyst
teacher
hr
support
student
```

### Типы целей

```text
ai_literacy
prompt_engineering
ai_assistant
ai_agent
no_code_automation
telegram_bot
web_ai_app
rag_knowledge_base
local_llm
ml_ds
computer_vision
audio_speech
commercial_ai_product
```

### Позиция в треке

```text
start
foundation
core
practice
advanced
optional
capstone
```

## Минимальные поля для MVP

Для первой версии не обязательно заполнять все. Достаточно:

```json
{
  "course_title": "",
  "lesson_id": "",
  "lesson_order": 0,
  "module_title": "",
  "lesson_title": "",
  "description": "",
  "learning_result": "",
  "materials": [],
  "homework_lite": "",
  "homework_pro": "",
  "level": "",
  "roles": [],
  "topics": [],
  "technologies": [],
  "prerequisites": [],
  "mandatory_for_goals": [],
  "track_position": "",
  "status": "active",
  "catalog_version": "",
  "source_sheet_id": "",
  "source_hash": ""
}
```

## Что нужно добавить к текущей таблице

Текущие поля уже дают содержательную базу. Для персонального трека нужно дополнить их следующими признаками:

- уровень сложности;
- целевая аудитория;
- тип цели;
- технологии;
- навыки;
- входные требования;
- обязательность;
- рекомендуемый этап трека;
- примерный объем времени;
- связь с предыдущими и следующими материалами.

Эти поля можно добавить вручную в отдельную нормализованную таблицу или вычислять полуавтоматически через LLM с ручной проверкой.
