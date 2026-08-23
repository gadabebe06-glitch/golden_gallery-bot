"""
BotBridge — Configurable Telegram Chatbot (Hospital IT Support)
===============================================================
A configuration-driven Telegram bot that businesses can deploy to handle
customer inquiries 24/7. All visible text is driven by config.json.
This deployment is a hospital IT support ticketing bot: users can submit
support tickets through a guided conversation, learn about IT services,
contact the helpdesk, or talk directly to IT staff.

Usage:
    BOTBRIDGE_BOT_TOKEN=your_token_here python bot.py
"""
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

TICKETS_PATH = Path(__file__).parent / "tickets.json"

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
# Conversation states (ticket flow)
# ---------------------------------------------------------------------------
(
    CATEGORY,
    DESCRIPTION,
    PRIORITY,
    DEPARTMENT,
    CONTACT,
    CONFIRM,
) = range(6)

CANCEL = "cancel"
CONFIRM_OK = "confirm"

# ---------------------------------------------------------------------------
# Ticket persistence helpers
# ---------------------------------------------------------------------------
def _load_tickets() -> list:
    """Load existing tickets from tickets.json (empty list if none yet)."""
    if TICKETS_PATH.exists():
        try:
            with open(TICKETS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read tickets.json, starting fresh.")
    return []


def _save_ticket(ticket: dict) -> None:
    """Append a ticket to tickets.json (creating the file if needed)."""
    tickets = _load_tickets()
    tickets.append(ticket)
    with open(TICKETS_PATH, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2, ensure_ascii=False)


def _next_ticket_id() -> str:
    """Return the next auto-incrementing ticket ID: IT-YYYY-XXX."""
    year = datetime.now().year
    max_seq = 0
    for t in _load_tickets():
        mid = t.get("ticket_id", "")
        if mid.startswith(f"IT-{year}-"):
            try:
                seq = int(mid.rsplit("-", 1)[1])
                if seq > max_seq:
                    max_seq = seq
            except (ValueError, IndexError):
                continue
    return f"IT-{year}-{max_seq + 1:03d}"


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------
def _main_menu_keyboard() -> InlineKeyboardMarkup:
    """Build the main menu inline keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Submit Support Ticket 🎫", callback_data="ticket")],
        [InlineKeyboardButton("About IT Services ℹ️", callback_data="about")],
        [InlineKeyboardButton("Contact IT Helpdesk 📍", callback_data="contact")],
        [InlineKeyboardButton("📞 Talk to IT Staff", callback_data="talk_to_human")],
    ])


def _back_keyboard() -> InlineKeyboardMarkup:
    """Build the 'Back to Menu' inline keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Back to Menu", callback_data="main_menu")],
    ])


def _cancel_keyboard() -> InlineKeyboardMarkup:
    """Build a keyboard with only a Cancel button."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)],
    ])


def _category_keyboard() -> InlineKeyboardMarkup:
    """Build the category selection keyboard (2 columns + cancel)."""
    categories = config.get("ticket_categories", [
        "Hardware", "Software", "Network", "Email/Account",
        "EMR/EHR", "Printer", "Other",
    ])
    rows = []
    for i in range(0, len(categories), 2):
        row = [
            InlineKeyboardButton(cat, callback_data=f"cat_{cat}")
            for cat in categories[i:i + 2]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)])
    return InlineKeyboardMarkup(rows)


def _priority_keyboard() -> InlineKeyboardMarkup:
    """Build the priority selection keyboard."""
    priorities = config.get("ticket_priorities", ["Low", "Medium", "High", "Critical"])
    rows = [[]]
    for pri in priorities:
        rows[-1].append(InlineKeyboardButton(pri, callback_data=f"pri_{pri}"))
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)])
    return InlineKeyboardMarkup(rows)


def _confirm_keyboard() -> InlineKeyboardMarkup:
    """Build the confirmation keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Ticket", callback_data=CONFIRM_OK)],
        [InlineKeyboardButton("❌ Cancel", callback_data=CANCEL)],
    ])


def _welcome_text(first_name: str) -> str:
    """Format the welcome message, substituting placeholders."""
    return config["welcome_message"].format(
        first_name=first_name,
        business_name=config["business_name"],
    )


# ---------------------------------------------------------------------------
# General handlers
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
    """Handle all inline keyboard button presses (non-ticket callbacks)."""
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
    # --- About IT Services ---
    if data == "about":
        text = f"🏢 *About {config['business_name']}:*\n\n{config['about_text']}"
        await query.edit_message_text(
            text=text,
            reply_markup=_back_keyboard(),
            parse_mode="Markdown",
        )
        return
    # --- Services ---
    if data == "services":
        lines = [f"🛠️ <b>Our Services:</b>"]
        for i, service in enumerate(config["services"], 1):
            # Escape < and > in service text for HTML parse mode
            safe = service.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Convert *text* to <b>text</b> for bold
            safe = re.sub(r"\*(.+?)\*", r"<b>\1</b>", safe)
            lines.append(f"{i}. {safe}")
        text = "\n".join(lines)
        await query.edit_message_text(
            text=text,
            reply_markup=_back_keyboard(),
            parse_mode="HTML",
        )
        return
    # --- Contact IT Helpdesk ---
    if data == "contact":
        lines = [f"📍 *Contact IT Helpdesk:*", ""]
        lines.append(f"🏠 {config['contact_address']}")
        if config.get("contact_phone"):
            lines.append(f"📞 {config['contact_phone']}")
        if config.get("contact_email"):
            lines.append(f"✉️ {config['contact_email']}")
        if config.get("contact_website"):
            lines.append(f"🌐 {config['contact_website']}")
        if config.get("contact_hours"):
            lines.append(f"🕒 {config['contact_hours']}")
        text = "\n".join(lines)
        await query.edit_message_text(
            text=text,
            reply_markup=_back_keyboard(),
            parse_mode="Markdown",
        )
        return
    # --- Talk to IT Staff ---
    if data == "talk_to_human":
        owner_id = config.get("owner_telegram_user_id", "1017133229")
        talk_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📩 Message IT Staff",
                    url=f"tg://user?id={owner_id}",
                ),
            ],
            [InlineKeyboardButton("⬅ Back to Menu", callback_data="main_menu")],
        ])
        await query.edit_message_text(
            text=(
                "Click the button below to message an IT staff member directly.\n\n"
                "They will respond to you personally."
            ),
            reply_markup=talk_keyboard,
            parse_mode="Markdown",
        )
        return
    # --- Fallback (unknown callback) ---
    logger.warning("Unknown callback data received: %s", data)
    await query.edit_message_text(
        text="Unknown option. Please try again.",
        reply_markup=_back_keyboard(),
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Ticket submission flow (ConversationHandler)
# ---------------------------------------------------------------------------
async def ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point — ask for the category of the issue."""
    query = update.callback_query
    await query.answer()
    context.user_data["ticket"] = {}
    await query.edit_message_text(
        text=(
            "🎫 *Submit Support Ticket*\n\n"
            "Please select the category that best describes your issue:"
        ),
        reply_markup=_category_keyboard(),
        parse_mode="Markdown",
    )
    return CATEGORY


async def ticket_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record the category, then ask for a description."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == CANCEL:
        return await cancel_ticket(update, context)
    category = data.split("_", 1)[1]
    context.user_data["ticket"]["category"] = category
    await query.edit_message_text(
        text=(
            f"📝 *Describe your issue*\n\n"
            f"Category: *{category}*\n\n"
            "Please describe the issue you are experiencing. "
            "(Type your message below, or send /cancel to abort)"
        ),
        reply_markup=_cancel_keyboard(),
        parse_mode="Markdown",
    )
    return DESCRIPTION


async def ticket_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record the description, then ask for a priority."""
    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text("Please describe the issue you are experiencing:")
        return DESCRIPTION
    context.user_data["ticket"]["description"] = description
    await update.message.reply_text(
        text="🕒 *Priority*\n\nHow urgent is this issue? Please select a priority:",
        reply_markup=_priority_keyboard(),
        parse_mode="Markdown",
    )
    return PRIORITY


async def ticket_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record the priority, then ask for department/location."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == CANCEL:
        return await cancel_ticket(update, context)
    priority = data.split("_", 1)[1]
    context.user_data["ticket"]["priority"] = priority
    await query.edit_message_text(
        text=(
            "🏥 *Department / Location*\n\n"
            "Which department or location are you in? "
            "(e.g. Emergency, Radiology, ICU, Admin, Main Building)\n\n"
            "Type your answer below, or send /cancel to abort"
        ),
        reply_markup=_cancel_keyboard(),
        parse_mode="Markdown",
    )
    return DEPARTMENT


async def ticket_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record the department, then ask for a contact extension/phone."""
    department = (update.message.text or "").strip()
    if not department:
        await update.message.reply_text("Please provide your department or location:")
        return DEPARTMENT
    context.user_data["ticket"]["department"] = department
    await update.message.reply_text(
        text=(
            "📞 *Contact Extension / Phone*\n\n"
            "Please provide a contact extension or phone number so our team "
            "can reach you about this ticket.\n\n"
            "Type your answer below, or send /cancel to abort"
        ),
        reply_markup=_cancel_keyboard(),
        parse_mode="Markdown",
    )
    return CONTACT


async def ticket_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record the contact info, then show a confirmation summary."""
    contact = (update.message.text or "").strip()
    if not contact:
        await update.message.reply_text(
            "Please provide a contact extension or phone number:"
        )
        return CONTACT
    context.user_data["ticket"]["contact"] = contact
    ticket = context.user_data["ticket"]
    await update.message.reply_text(
        text=(
            "📋 *Please confirm your ticket details:*\n\n"
            f"• *Category:* {ticket.get('category')}\n"
            f"• *Description:* {ticket.get('description')}\n"
            f"• *Priority:* {ticket.get('priority')}\n"
            f"• *Department/Location:* {ticket.get('department')}\n"
            f"• *Contact:* {ticket.get('contact')}\n\n"
            "Is everything correct?"
        ),
        reply_markup=_confirm_keyboard(),
        parse_mode="Markdown",
    )
    return CONFIRM


async def ticket_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and save the ticket, then show the confirmation message."""
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == CANCEL:
        return await cancel_ticket(update, context)
    if data != CONFIRM_OK:
        return CONFIRM

    ticket = context.user_data.get("ticket", {})
    ticket["ticket_id"] = _next_ticket_id()
    ticket["submit_time"] = datetime.now().isoformat(timespec="seconds")
    ticket["user_id"] = update.effective_user.id if update.effective_user else None
    ticket["user_name"] = (
        update.effective_user.full_name if update.effective_user else None
    )
    _save_ticket(ticket)
    logger.info("Ticket %s submitted by user %s", ticket["ticket_id"], ticket.get("user_id"))

    await query.edit_message_text(
        text=(
            f"✅ *Ticket {ticket['ticket_id']} Submitted!*\n\n"
            f"• *Category:* {ticket.get('category')}\n"
            f"• *Description:* {ticket.get('description')}\n"
            f"• *Priority:* {ticket.get('priority')}\n"
            f"• *Department/Location:* {ticket.get('department')}\n"
            f"• *Contact:* {ticket.get('contact')}\n\n"
            "Your ticket has been logged. Our IT team has been notified and "
            "will respond as soon as possible. Please keep the ticket ID for reference."
        ),
        reply_markup=_main_menu_keyboard(),
        parse_mode="Markdown",
    )
    context.user_data.pop("ticket", None)
    return ConversationHandler.END


async def cancel_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the ticket submission from any state."""
    context.user_data.pop("ticket", None)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text="Ticket submission cancelled. ❌\nIs there anything else we can help with?",
            reply_markup=_main_menu_keyboard(),
            parse_mode="Markdown",
        )
    elif update.message:
        await update.message.reply_text(
            text="Ticket submission cancelled. ❌\nIs there anything else we can help with?",
            reply_markup=_main_menu_keyboard(),
            parse_mode="Markdown",
        )
    return ConversationHandler.END


ticket_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(ticket_start, pattern="^ticket$")],
    name="ticket_flow",
    states={
        CATEGORY: [CallbackQueryHandler(ticket_category, pattern="^cat_")],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_description)],
        PRIORITY: [CallbackQueryHandler(ticket_priority, pattern="^pri_")],
        DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_department)],
        CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_contact)],
        CONFIRM: [CallbackQueryHandler(ticket_confirm, pattern=f"^({CONFIRM_OK}|{CANCEL})$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_ticket),
        CallbackQueryHandler(cancel_ticket, pattern=f"^{CANCEL}$"),
        MessageHandler(filters.COMMAND, cancel_ticket),
    ],
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Build and run the BotBridge bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(ticket_conversation)
    application.add_handler(CallbackQueryHandler(button_click))
    logger.info("BotBridge bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
