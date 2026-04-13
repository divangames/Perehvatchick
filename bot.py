import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Iterable

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("order-sniffer-bot")


@dataclass(frozen=True)
class BotConfig:
    token: str
    source_chat_ids: set[int]
    target_chat_id: int
    order_keywords: tuple[str, ...]


def _parse_ids(raw_value: str) -> set[int]:
    ids = set()
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        ids.add(int(item))
    return ids


def _parse_keywords(raw_value: str) -> tuple[str, ...]:
    words = []
    for item in raw_value.split(","):
        word = item.strip().lower()
        if word:
            words.append(word)
    return tuple(words)


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    return float(raw)


def load_config() -> BotConfig:
    load_dotenv()

    token = os.getenv("BOT_TOKEN", "").strip()
    source_chat_ids_raw = os.getenv("SOURCE_CHAT_IDS", "").strip()
    target_chat_id_raw = os.getenv("TARGET_CHAT_ID", "").strip()
    order_keywords_raw = os.getenv("ORDER_KEYWORDS", "").strip()

    if not token:
        raise ValueError("BOT_TOKEN is required")
    if not source_chat_ids_raw:
        raise ValueError("SOURCE_CHAT_IDS is required")
    if not target_chat_id_raw:
        raise ValueError("TARGET_CHAT_ID is required")

    source_chat_ids = _parse_ids(source_chat_ids_raw)
    if not source_chat_ids:
        raise ValueError("SOURCE_CHAT_IDS has no valid values")

    return BotConfig(
        token=token,
        source_chat_ids=source_chat_ids,
        target_chat_id=int(target_chat_id_raw),
        order_keywords=_parse_keywords(order_keywords_raw),
    )


def _message_text(update: Update) -> str:
    message = update.effective_message
    if not message:
        return ""
    return (message.text or message.caption or "").lower()


def _has_keywords(text: str, keywords: Iterable[str]) -> bool:
    # If no keywords are configured, forward every message from source chats.
    keywords = tuple(keywords)
    if not keywords:
        return True
    return any(word in text for word in keywords)


async def intercept_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_message:
        return

    config: BotConfig = context.bot_data["config"]
    source_chat_id = update.effective_chat.id

    if source_chat_id not in config.source_chat_ids:
        return

    text = _message_text(update)
    if not _has_keywords(text, config.order_keywords):
        return

    try:
        await context.bot.copy_message(
            chat_id=config.target_chat_id,
            from_chat_id=source_chat_id,
            message_id=update.effective_message.message_id,
        )
        logger.info("Forwarded message %s from chat %s", update.effective_message.message_id, source_chat_id)
    except Exception:
        logger.exception("Failed to forward message %s from chat %s", update.effective_message.message_id, source_chat_id)


async def main() -> None:
    config = load_config()

    connect_t = _env_float("TELEGRAM_CONNECT_TIMEOUT", 30.0)
    read_t = _env_float("TELEGRAM_READ_TIMEOUT", 30.0)
    write_t = _env_float("TELEGRAM_WRITE_TIMEOUT", 30.0)
    pool_t = _env_float("TELEGRAM_POOL_TIMEOUT", 10.0)
    proxy = os.getenv("TELEGRAM_PROXY", "").strip() or None

    builder = (
        Application.builder()
        .token(config.token)
        .connect_timeout(connect_t)
        .read_timeout(read_t)
        .write_timeout(write_t)
        .pool_timeout(pool_t)
        .get_updates_connect_timeout(connect_t)
        .get_updates_read_timeout(read_t)
        .get_updates_write_timeout(write_t)
        .get_updates_pool_timeout(pool_t)
    )
    if proxy:
        builder = builder.proxy(proxy).get_updates_proxy(proxy)
        logger.info("Using TELEGRAM_PROXY for API requests")

    app = builder.build()
    app.bot_data["config"] = config

    app.add_handler(MessageHandler(filters.ALL, intercept_message))
    logger.info(
        "Bot started. Watching %s chat(s), forwarding to %s",
        len(config.source_chat_ids),
        config.target_chat_id,
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
