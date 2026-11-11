# Double Drop — Telegram-бот (детектив-квест + мини-игра «дождь»)

Основной режим: сложный детективный квест **The Double Drop** (Port Meridian, 1947).
Мини-игра: **Raindrop Catch** — ловишь капли 💧 в сетке облаков, копишь drops, есть топ и ежедневное напоминание.
Язык игры: английский.

## Дело 1: The Double Drop
Магнат Виктор Халлоран найден мёртвым в запертом кабинете отеля во время гала-вечера. Восемь подозреваемых, у каждого мотив и ложь.
- 10 говорящих персонажей, 7 локаций, 31 улика
- осмотр мест, допросы, **предъявление улик** (реакции персонажей), блокнот улик, подсказки (стоят 2 действия)
- улики открывают новые локации и новые темы разговора; есть ложные следы
- финальное обвинение: кто → как → почему; ошибка стоит 5 действий, дело остаётся открытым
- рейтинг по числу потраченных действий (★★★ / ★★☆ / ★☆☆), прогресс сохраняется, на открытое дело приходит напоминание
- за раскрытие: +30 drops (один раз, повторное прохождение награды не даёт)

Спойлер-карта сюжета и тайм-лайн лежат в шапке `cases/double_drop.py`.

## Как добавить новое дело
Дело — это данные. Создай `cases/<имя>.py` по образцу `double_drop.py` (классы из `quest.py`: `Clue`, `Spot`, `Location`, `Topic`, `Reaction`, `Character`, `Case`), добавь его в `cases/__init__.py`.
Тесты (`tests/test_quest.py`) сами проверят, что все ссылки на улики существуют, что каждую улику можно получить, что тексты влезают в сообщение Telegram и не ломают HTML-разметку.

## Команды
`/start` · `/case` (дело) · `/notebook` · `/rain` (мини-игра) · `/top` · `/me` · `/reminder`

## Запуск локально
```bash
pip install -r requirements.txt
cp .env.example .env   # вписать BOT_TOKEN
export $(grep -v '^#' .env | xargs)
python bot.py
```

## Деплой на Railway
1. Новый сервис из этого репо, процесс `worker` (есть `Procfile`).
2. Переменные: `BOT_TOKEN`, `DB_PATH`, `REMINDER_HOUR_UTC`.
3. Чтобы прогресс квеста и drops не стирались при редеплое — Volume в `/data` и `DB_PATH=/data/doubledrop.db`.

## Переменные окружения
| Переменная | Что делает |
|---|---|
| `BOT_TOKEN` | токен из @BotFather (обязательно) |
| `DB_PATH` | путь к SQLite, по умолчанию `doubledrop.db` |
| `REMINDER_HOUR_UTC` | час (UTC), когда уходит напоминание, по умолчанию 17 |

## Настройка в BotFather
**About** (`/setabouttext`, до 120 символов):
```
Port Meridian, 1947. A dead magnate, eight suspects, one night. Solve The Double Drop, then catch some rain.
```
**Description** (`/setdescription`):
```
Port Meridian, 1947. Shipping magnate Victor Halloran is dead in a locked room and eight people had a reason.

Search the scenes, question the suspects, put the evidence on the table and name the killer.

Need air? Step into the rain: a 30-second tap game with a fresh shower of bonus drops every day.
```
**Commands** (`/setcommands`):
```
case - Open the case file
notebook - Your clues
rain - Raindrop Catch mini-game
top - Top catchers
me - My drops
reminder - Daily reminder on/off
```

## Тесты
```bash
python -m unittest discover -s tests -t . -v
```
28 тестов: логика дождя, база, целостность и разрешимость дела (бот сам «проходит» всё дело), сквозной прогон квеста через фейковую сессию aiogram с наградой и рестартом.

## Структура
- `bot.py` — главное меню, дождь, напоминания, сборка диспетчера
- `quest.py` — движок квестов (чистая логика)
- `quest_ui.py` — Telegram-обвязка квеста, сохранение, награда
- `cases/` — дела (данные): `double_drop.py`
- `game.py` — логика Raindrop Catch · `db.py` — SQLite · `config.py` — переменные окружения
