# BotBridge — Configurable Telegram Chatbot (Hospital IT Support)

A configuration-driven Telegram bot that businesses can deploy to handle customer inquiries 24/7. This deployment is a **hospital IT support ticketing bot**: users can submit support tickets through a guided conversation, learn about IT services, contact the helpdesk, or talk directly to IT staff.

## Quick Start
### 1. Install dependencies
```bash
pip install -r requirements.txt
```
### 2. Set your bot token
Obtain a bot token from [@BotFather](https://t.me/BotFather) on Telegram, then export it:
```bash
export BOTBRIDGE_BOT_TOKEN=your_bot_token_here
```
### 3. Configure your service
Edit `config.json` with your details:
| Field | Description |
|---|---|
| `business_name` | Your business / service name |
| `about_text` | "About" description (supports Markdown) |
| `services` | List of IT support categories (one string per category) |
| `ticket_categories` | Ticket category options shown in the submission flow |
| `ticket_priorities` | Priority options (Low / Medium / High / Critical) |
| `contact_address` | Helpdesk location |
| `contact_phone` | Phone number |
| `contact_website` | Website URL |
| `contact_email` | Email address |
| `contact_hours` | Support hours |
| `owner_telegram_user_id` | Your personal Telegram user id (numeric) |
| `welcome_message` | Welcome template — use `{first_name}` and `{business_name}` |
### 4. Run the bot
```bash
python bot.py
```
The bot will start polling and respond to `/start` commands.

## How It Works
- **`/start`** — Sends a welcome message with an inline keyboard menu.
- **Submit Support Ticket 🎫** — Starts a guided conversation: category → description → priority → department/location → contact → confirm. A ticket ID (`IT-YYYY-XXX`) is assigned and the ticket is appended to `tickets.json`. Send `/cancel` or use the Cancel button at any step to abort.
- **About IT Services ℹ️** — Shows the description from `about_text`.
- **Contact IT Helpdesk 📍** — Shows address, phone, email, website, and hours.
- **📞 Talk to IT Staff** — Shows a button that opens a direct Telegram chat with the owner via `tg://user?id={owner_telegram_user_id}`.
- Every sub-page has a **⬅ Back to Menu** button.

All visible text is driven by `config.json` — change any string there and the bot updates without touching `bot.py`.

## Project Structure
```
botbridge/
├── bot.py           # Main bot script (with ticket ConversationHandler)
├── config.json      # Service configuration
├── tickets.json     # Created on first ticket submission (gitignored)
├── requirements.txt # Python dependencies
└── README.md        # This file
```
