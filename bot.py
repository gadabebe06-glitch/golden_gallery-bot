"""
BotBridge — Configurable Telegram Chatbot
==========================================
A configuration-driven Telegram bot that businesses can deploy to handle
customer inquiries 24/7. All visible text is driven by config.json.

Usage:
    BOTBRIDGE_BOT_TOKEN=your_token_here python bot.py
"""

import json
import logging
import os
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = os.environ.get("BOTBRIDGE_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError(
        "BOTBRIDGE_BOT_TOKEN environment variable is not set.\n"
        "Set it before running:  BOTBRIDGE_BOT_TOKEN=your_token python bot.py"
    )

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------

def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the main menu inline keyboard from config."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("About Us 🏢", callback_data="about"),
            InlineKeyboardButton("Our Services 🛠️", callback_data="services"),
        ],
        [
            InlineKeyboardButton("Contact Us 📍", callback_data="contact"),
            InlineKeyboardButton("💬 Talk to Human", callback_data="talk_to_human"),
        ],
    ])


def _back_keyboard() -> InlineKeyboardMarkup:
    """Build the 'Back to Menu' inline keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back to Menu", callback_data="main_menu")],
    ])


def _welcome_text(first_name: str) -> str:
    """Format the welcome message, substituting placeholders."""
    return config["welcome_message"].format(
        first_name=first_name,
        business_name=config["business_name"],
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command — send welcome message with main menu."""
    user = update.effective_user
    first_name = user.first_name if user else "there"

    await update.message.reply_text(
        text=_welcome_text(first_name),
        reply_markup=_main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_first_name = update.effective_user.first_name if update.effective_user else "there"

    # --- Back to main menu ---
    if data == "main_menu":
        await query.edit_message_text(
            text=_welcome_text(user_first_name),
            reply_markup=_main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    # --- About Us ---
    if data == "about":
        text = f"🏢 *About {config['business_name']}:*\n\n{config['about_text']}"
        await query.edit_message_text(
            text=text,
            reply_markup=_back_keyboard(),
            parse_mode="Markdown",
        )
        return

    # --- Our Services ---
    if data == "services":
        lines = [f"🛠️ *Our Services:*"]
        for i, service in enumerate(config["services"], 1):
            lines.append(f"{i}\\. {service}")
        text = "\n".join(lines)
        await query.edit_message_text(
            text=text,
            reply_markup=_back_keyboard(),
            parse_mode="MarkdownV2",
        )
        return

    # --- Contact Us ---
    if data == "contact":
        text = (
            f"📍 *Contact Us:*\n\n"
            f"🏠 {config['contact_address']}\n"
            f"📞 {config['contact_phone']}\n"
            f"🌐 {config['contact_website']}"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=_back_keyboard(),
            parse_mode="Markdown",
        )
        return

    # --- Talk to Human ---
    if data == "talk_to_human":
        username = config["owner_telegram_username"]
        talk_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "💬 Chat with us on Telegram",
                    url=f"https://t.me/{username}",
                ),
            ],
            [InlineKeyboardButton("⬅ Back to Menu", callback_data="main_menu")],
        ])
        await query.edit_message_text(
            text=(
                "Click the button below to chat with us directly on Telegram\\!\n\n"
                "Our team is ready to assist you\\."
            ),
            reply_markup=talk_keyboard,
            parse_mode="MarkdownV2",
        )
        return

    # --- Fallback (unknown callback) ---
    logger.warning("Unknown callback data received: %s", data)
    await query.edit_message_text(
        text="Unknown option\\. Please try again\\.",
        reply_markup=_back_keyboard(),
        parse_mode="MarkdownV2",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Build and run the BotBridge bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))

    logger.info("BotBridge bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
