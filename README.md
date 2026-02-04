# Telegram Channel Manager Bot 🤖

A simple Telegram bot to broadcast messages to multiple channels simultaneously.

## Features ✨
- 📤 **Broadcast messages** to multiple channels at once
- 🎯 **Support all media types**: photos, videos, documents, audio, stickers
- 🔐 **Owner-only access** for security
- 📊 **Live broadcast statistics** with success/failure counts
- 🚀 **Easy channel management** with simple commands
- 💾 **Memory-based storage** (no database needed)

## Quick Start 🚀

### 1. Create a Telegram Bot
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow instructions
3. Copy your **Bot Token**

### 2. Get Your Telegram ID
1. Open Telegram, search for **@userinfobot**
2. Start the bot
3. Copy your **Numeric ID**

### 3. Deploy to Render (Free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)


### 4. Setup Bot in Telegram
1. Add bot as **Admin** to your channels
2. Grant **all permissions** (at least "Post Messages")
3. Start bot with `/start`

## Bot Commands 📋

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and show welcome message |
| `/help` | Show detailed usage guide |
| `/add_channel @username` | Add a channel to broadcast list |
| `/remove_channel` | Remove a channel from list |
| `/list_channels` | Show all registered channels |
| `/clear_channels` | Remove ALL channels (with confirmation) |
| `/stats` | Show bot statistics |

## Usage 📝

### Adding Channels
```bash
# Method 1: Using username
/add_channel @your_channel_username

# Method 2: Using channel ID
/add_channel -************
# Method 3: Forward message from channel
1. Forward any message from channel to bot
2. Reply with /add_channel
