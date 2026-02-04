import os
import json
import logging
import asyncio
from pathlib import Path
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# File to store channels
CHANNELS_FILE = "channels.json"

# Admin user IDs (add your Telegram user ID here)
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []


def load_channels() -> dict:
    """Load channels from JSON file."""
    if Path(CHANNELS_FILE).exists():
        try:
            with open(CHANNELS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"channels": []}
    return {"channels": []}


def save_channels(data: dict) -> None:
    """Save channels to JSON file."""
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_IDS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ You are not authorized to use this bot.\n"
            f"Your User ID: `{user.id}`",
            parse_mode="Markdown"
        )
        return
    
    welcome_text = f"""
👋 *Welcome to Multi-Channel Broadcaster Bot!*

*Your User ID:* `{user.id}`

*Available Commands:*
• `/add <channel_id>` - Add a channel
• `/remove <channel_id>` - Remove a channel
• `/list` - List all channels
• `/test` - Test broadcast to all channels
• `/help` - Show this help message

*How to use:*
1. Add this bot as admin to your channels
2. Use `/add @channel_username` or `/add -100xxxxxxxxxx`
3. Send any media (photo, video, document, audio) to broadcast

*Note:* Channel IDs usually start with `-100`
"""
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await start(update, context)


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a channel to the broadcast list."""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a channel ID or username.\n"
            "Example: `/add @mychannel` or `/add -1001234567890`",
            parse_mode="Markdown"
        )
        return
    
    channel_id = context.args[0]
    
    # Try to get channel info to verify bot is admin
    try:
        chat = await context.bot.get_chat(channel_id)
        member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                f"⚠️ Bot is not an admin in *{chat.title}*.\n"
                "Please add the bot as admin first.",
                parse_mode="Markdown"
            )
            return
        
        data = load_channels()
        channel_info = {
            "id": chat.id,
            "title": chat.title,
            "username": chat.username
        }
        
        # Check if already exists
        existing_ids = [c["id"] for c in data["channels"]]
        if chat.id in existing_ids:
            await update.message.reply_text(
                f"ℹ️ Channel *{chat.title}* is already in the list.",
                parse_mode="Markdown"
            )
            return
        
        data["channels"].append(channel_info)
        save_channels(data)
        
        await update.message.reply_text(
            f"✅ Successfully added *{chat.title}*\n"
            f"Channel ID: `{chat.id}`\n"
            f"Total channels: {len(data['channels'])}",
            parse_mode="Markdown"
        )
        
    except TelegramError as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Make sure:\n"
            "1. The channel ID/username is correct\n"
            "2. The bot is added as admin to the channel",
            parse_mode="Markdown"
        )


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a channel from the broadcast list."""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a channel ID.\n"
            "Example: `/remove -1001234567890`",
            parse_mode="Markdown"
        )
        return
    
    channel_input = context.args[0]
    data = load_channels()
    
    # Find and remove channel
    removed = None
    for i, channel in enumerate(data["channels"]):
        if (str(channel["id"]) == channel_input or 
            channel.get("username") == channel_input.lstrip("@")):
            removed = data["channels"].pop(i)
            break
    
    if removed:
        save_channels(data)
        await update.message.reply_text(
            f"✅ Removed *{removed['title']}* from broadcast list.\n"
            f"Remaining channels: {len(data['channels'])}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Channel not found in the list.\n"
            "Use `/list` to see all channels.",
            parse_mode="Markdown"
        )


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all channels in the broadcast list."""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    data = load_channels()
    
    if not data["channels"]:
        await update.message.reply_text(
            "📭 No channels added yet.\n"
            "Use `/add <channel_id>` to add channels.",
            parse_mode="Markdown"
        )
        return
    
    channels_text = "*📢 Broadcast Channels:*\n\n"
    for i, channel in enumerate(data["channels"], 1):
        username = f"@{channel['username']}" if channel.get('username') else "No username"
        channels_text += f"{i}. *{channel['title']}*\n   ID: `{channel['id']}`\n   Username: {username}\n\n"
    
    channels_text += f"*Total:* {len(data['channels'])} channels"
    
    await update.message.reply_text(channels_text, parse_mode="Markdown")


async def test_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a test message to all channels."""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    data = load_channels()
    
    if not data["channels"]:
        await update.message.reply_text("❌ No channels to test. Add channels first.")
        return
    
    success = 0
    failed = 0
    failed_channels = []
    
    status_msg = await update.message.reply_text("🔄 Testing broadcast...")
    
    for channel in data["channels"]:
        try:
            await context.bot.send_message(
                chat_id=channel["id"],
                text="🧪 *Test Message*\nThis is a test broadcast from the bot.",
                parse_mode="Markdown"
            )
            success += 1
        except TelegramError as e:
            failed += 1
            failed_channels.append(f"{channel['title']}: {str(e)}")
    
    result_text = f"*Test Broadcast Results:*\n\n✅ Success: {success}\n❌ Failed: {failed}"
    
    if failed_channels:
        result_text += "\n\n*Failed channels:*\n" + "\n".join(failed_channels)
    
    await status_msg.edit_text(result_text, parse_mode="Markdown")


async def broadcast_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast media to all channels."""
    user = update.effective_user
    message = update.message
    
    if not is_admin(user.id):
        await message.reply_text("⛔ Unauthorized access.")
        return
    
    data = load_channels()
    
    if not data["channels"]:
        await message.reply_text(
            "❌ No channels configured.\n"
            "Use `/add <channel_id>` to add channels first.",
            parse_mode="Markdown"
        )
        return
    
    status_msg = await message.reply_text(
        f"📤 Broadcasting to {len(data['channels'])} channels..."
    )
    
    success = 0
    failed = 0
    failed_channels = []
    
    for channel in data["channels"]:
        try:
            # Forward or copy the message based on content type
            if message.photo:
                await context.bot.send_photo(
                    chat_id=channel["id"],
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=channel["id"],
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=channel["id"],
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=channel["id"],
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.voice:
                await context.bot.send_voice(
                    chat_id=channel["id"],
                    voice=message.voice.file_id,
                    caption=message.caption
                )
            elif message.video_note:
                await context.bot.send_video_note(
                    chat_id=channel["id"],
                    video_note=message.video_note.file_id
                )
            elif message.sticker:
                await context.bot.send_sticker(
                    chat_id=channel["id"],
                    sticker=message.sticker.file_id
                )
            elif message.animation:
                await context.bot.send_animation(
                    chat_id=channel["id"],
                    animation=message.animation.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities
                )
            elif message.text:
                await context.bot.send_message(
                    chat_id=channel["id"],
                    text=message.text,
                    entities=message.entities
                )
            else:
                # For other types, try to forward
                await message.forward(chat_id=channel["id"])
            
            success += 1
            
        except TelegramError as e:
            failed += 1
            failed_channels.append(f"• {channel['title']}: {str(e)}")
            logger.error(f"Failed to send to {channel['title']}: {e}")
    
    # Update status
    result_text = f"*Broadcast Complete!*\n\n✅ Sent: {success}/{len(data['channels'])}"
    
    if failed > 0:
        result_text += f"\n❌ Failed: {failed}\n\n*Errors:*\n" + "\n".join(failed_channels[:5])
        if len(failed_channels) > 5:
            result_text += f"\n...and {len(failed_channels) - 5} more"
    
    await status_msg.edit_text(result_text, parse_mode="Markdown")


async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get user's Telegram ID."""
    user = update.effective_user
    await update.message.reply_text(
        f"Your Telegram User ID: `{user.id}`",
        parse_mode="Markdown"
    )


def main() -> None:
    """Start the bot."""
    # Get bot token from environment variable
    token = os.getenv("BOT_TOKEN")
    
    if not token:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS not set. Bot will reject all users!")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_channel))
    application.add_handler(CommandHandler("remove", remove_channel))
    application.add_handler(CommandHandler("list", list_channels))
    application.add_handler(CommandHandler("test", test_broadcast))
    application.add_handler(CommandHandler("myid", get_my_id))
    
    # Handle all media and text messages for broadcasting
    application.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.AUDIO | 
        filters.Document.ALL | filters.VOICE | filters.VIDEO_NOTE |
        filters.Sticker.ALL | filters.ANIMATION | 
        (filters.TEXT & ~filters.COMMAND),
        broadcast_media
    ))
    
    # Start the bot
    logger.info("Bot is starting...")
    
    # Use webhook for Render or polling for local development
    port = int(os.getenv("PORT", 10000))
    webhook_url = os.getenv("WEBHOOK_URL")
    
    if webhook_url:
        # Production: Use webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            secret_token=os.getenv("WEBHOOK_SECRET", "your-secret-token"),
            webhook_url=webhook_url
        )
    else:
        # Development: Use polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
