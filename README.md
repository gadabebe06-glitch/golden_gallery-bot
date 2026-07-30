# BotBridge — Configurable Telegram Chatbot

A configuration-driven Telegram bot that businesses can deploy to handle customer inquiries 24/7. The bot greets customers, shows business info via inline menus, and redirects interested leads to the business owner's personal Telegram.

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

### 3. Configure your business

Edit `config.json` with your business details:

| Field | Description |
|---|---|
| `business_name` | Your business name |
| `about_text` | "About Us" description (supports Markdown) |
| `services` | List of services (one string per service) |
| `contact_address` | Physical address |
| `contact_phone` | Phone number |
| `contact_website` | Website URL |
| `owner_telegram_username` | Your personal Telegram username (e.g. `johndoe` — no `@` or `t.me/`) |
| `welcome_message` | Welcome template — use `{first_name}` for the user's name and `{business_name}` for the business name |

### 4. Run the bot

```bash
python bot.py
```

The bot will start polling and respond to `/start` commands.

## How It Works

- **`/start`** — Sends a welcome message with an inline keyboard menu.
- **About Us 🏢** — Shows the business description from `about_text`.
- **Our Services 🛠️** — Lists services from the `services` array.
- **Contact Us 📍** — Shows address, phone, and website.
- **💬 Owner** — Shows a button that opens a direct Telegram chat with the business owner via `t.me/{username}`.
- Every sub-page has a **⬅ Back to Menu** button.

All visible text is driven by `config.json` — change any string there and the bot updates without touching `bot.py`.

## Project Structure

```
botbridge/
├── bot.py           # Main bot script
├── config.json      # Business configuration
├── requirements.txt # Python dependencies
└── README.md        # This file
```
