import os
import logging
import asyncio
from threading import Thread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackQueryHandler,
    CallbackContext
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Render health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "Telegram Channel Manager Bot is running!"

@app.route('/health')
def health():
    return "OK", 200

# Store channels in memory
channels = []

# Load configuration from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER_ID = int(os.getenv('OWNER_ID', 0))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
PORT = int(os.getenv('PORT', 10000))

def start_command(update: Update, context: CallbackContext):
    """Send a welcome message when /start is issued."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⚠️ You are not authorized to use this bot.")
        return
    
    welcome_text = """
🤖 *Welcome to Channel Manager Bot*

*Available Commands:*
/add_channel - Add a new channel
/remove_channel - Remove a channel
/list_channels - List all channels
/clear_channels - Remove all channels
/stats - Get bot statistics
/help - Show this help message

*How to use:*
1. Add bot as admin to your channels
2. Use /add_channel to register channels
3. Send any media/message to bot to forward to all channels
    """
    
    update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )

def help_command(update: Update, context: CallbackContext):
    """Send help message."""
    help_text = """
*📚 Bot Usage Guide*

1. *Add Bot to Channels:*
   - Add bot as administrator to all channels
   - Grant all permissions (Post Messages is minimum)

2. *Register Channels:*
   - Use `/add_channel @channel_username`
   - Or forward a message from the channel
   - Or use `/add_channel channel_id`

3. *Send Broadcasts:*
   - Simply send any message/media to the bot
   - It will automatically forward to all registered channels

4. *Manage Channels:*
   - `/list_channels` - View all channels
   - `/remove_channel` - Remove a channel
   - `/clear_channels` - Remove ALL channels
   - `/stats` - View statistics

*Note:* Channels are stored in memory. They will reset when bot restarts.
    """
    
    update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def get_chat_async(bot, chat_id_or_username):
    """Async wrapper for get_chat."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return await bot.get_chat(chat_id_or_username)
    finally:
        loop.close()

async def get_chat_member_async(bot, chat_id, user_id):
    """Async wrapper for get_chat_member."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return await bot.get_chat_member(chat_id, user_id)
    finally:
        loop.close()

def add_channel_command(update: Update, context: CallbackContext):
    """Add a new channel to the bot."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⚠️ Only the owner can add channels.")
        return
    
    args = context.args
    
    if not args:
        update.message.reply_text(
            "Please provide channel username or ID.\n"
            "Usage: `/add_channel @channel_username`\n"
            "Or forward a message from the channel and use /add_channel",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_identifier = args[0]
    
    try:
        # Run async functions in a thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get chat info
        if channel_identifier.startswith('@'):
            chat = loop.run_until_complete(context.bot.get_chat(channel_identifier))
        else:
            chat = loop.run_until_complete(context.bot.get_chat(int(channel_identifier)))
        
        # Check if bot is admin
        chat_member = loop.run_until_complete(
            context.bot.get_chat_member(chat.id, context.bot.id)
        )
        
        loop.close()
        
        if chat_member.status not in ['administrator', 'creator']:
            update.message.reply_text(
                f"❌ Bot is not admin in {chat.title}.\n"
                f"Please add bot as administrator first with all permissions."
            )
            return
        
        # Check if channel already exists
        for channel in channels:
            if channel['channel_id'] == chat.id:
                update.message.reply_text(
                    f"⚠️ Channel '{chat.title}' is already registered."
                )
                return
        
        # Add channel to memory
        channel_data = {
            'channel_id': chat.id,
            'channel_username': chat.username,
            'channel_title': chat.title,
            'added_by': update.effective_user.id
        }
        
        channels.append(channel_data)
        
        update.message.reply_text(
            f"✅ Channel *{chat.title}* has been added successfully!\n"
            f"• ID: `{chat.id}`\n"
            f"• Username: @{chat.username or 'N/A'}\n"
            f"• Total channels: {len(channels)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Make sure:\n"
            "1. Bot is added to the channel\n"
            "2. Bot is administrator\n"
            "3. Channel username/ID is correct"
        )

def remove_channel_command(update: Update, context: CallbackContext):
    """Remove a channel from the bot."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⚠️ Only the owner can remove channels.")
        return
    
    if not channels:
        update.message.reply_text("No channels registered.")
        return
    
    if not context.args:
        # Show list of channels for removal
        keyboard = []
        for i, channel in enumerate(channels, 1):
            button_text = f"{i}. {channel['channel_title'][:30]}"
            callback_data = f"remove_{channel['channel_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Select a channel to remove:",
            reply_markup=reply_markup
        )
        return
    
    # Remove by ID provided in arguments
    try:
        channel_id = int(context.args[0])
        for i, channel in enumerate(channels):
            if channel['channel_id'] == channel_id:
                removed_channel = channels.pop(i)
                update.message.reply_text(
                    f"✅ Channel '{removed_channel['channel_title']}' removed successfully.\n"
                    f"Remaining channels: {len(channels)}"
                )
                return
        
        update.message.reply_text("Channel not found.")
    
    except ValueError:
        update.message.reply_text("Please provide a valid channel ID.")

def clear_channels_command(update: Update, context: CallbackContext):
    """Remove ALL channels."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⚠️ Only the owner can clear channels.")
        return
    
    if not channels:
        update.message.reply_text("No channels to clear.")
        return
    
    # Create confirmation buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, clear all", callback_data="clear_yes"),
            InlineKeyboardButton("❌ No, keep them", callback_data="clear_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"⚠️ Are you sure you want to remove ALL {len(channels)} channels?\n"
        "This action cannot be undone!",
        reply_markup=reply_markup
    )

def list_channels_command(update: Update, context: CallbackContext):
    """List all registered channels."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⚠️ Only the owner can view channels.")
        return
    
    if not channels:
        update.message.reply_text("No channels registered yet.")
        return
    
    message = "📊 *Registered Channels:*\n\n"
    for i, channel in enumerate(channels, 1):
        message += f"{i}. *{channel['channel_title']}*\n"
        message += f"   • ID: `{channel['channel_id']}`\n"
        message += f"   • Username: @{channel['channel_username'] or 'N/A'}\n\n"
    
    message += f"Total: {len(channels)} channels"
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

def stats_command(update: Update, context: CallbackContext):
    """Show bot statistics."""
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("⚠️ Only the owner can view statistics.")
        return
    
    stats_text = f"""
📈 *Bot Statistics*

*Channels:*
• Currently Registered: {len(channels)}

*Bot Info:*
• Username: @{context.bot.username}
• Owner ID: {OWNER_ID}

*Storage:*
• Channels stored in memory
• Will reset on bot restart
    """
    
    update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

def forward_to_all_channels(message, context: CallbackContext):
    """Forward a message to all registered channels."""
    if not channels:
        if message.chat.type != 'private':
            message.reply_text("No channels registered yet. Use /add_channel first.")
        return
    
    total_channels = len(channels)
    successful = 0
    failed = 0
    
    # Send processing message
    status_msg = message.reply_text(f"📤 Broadcasting to {total_channels} channels...")
    
    for channel in channels:
        try:
            # Forward the message based on type
            if message.photo:
                context.bot.send_photo(
                    chat_id=channel['channel_id'],
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.video:
                context.bot.send_video(
                    chat_id=channel['channel_id'],
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.document:
                context.bot.send_document(
                    chat_id=channel['channel_id'],
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.audio:
                context.bot.send_audio(
                    chat_id=channel['channel_id'],
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.voice:
                context.bot.send_voice(
                    chat_id=channel['channel_id'],
                    voice=message.voice.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.sticker:
                context.bot.send_sticker(
                    chat_id=channel['channel_id'],
                    sticker=message.sticker.file_id
                )
            elif message.animation:
                context.bot.send_animation(
                    chat_id=channel['channel_id'],
                    animation=message.animation.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Text message
                context.bot.send_message(
                    chat_id=channel['channel_id'],
                    text=message.text or message.caption or "📢 Broadcast",
                    entities=message.entities or message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to send to channel {channel['channel_id']}: {e}")
            failed += 1
            continue
    
    # Update status message
    status_msg.edit_text(
        f"✅ Broadcast completed!\n\n"
        f"• ✅ Successful: {successful}\n"
        f"• ❌ Failed: {failed}\n"
        f"• 📊 Total: {total_channels}"
    )

def handle_message(update: Update, context: CallbackContext):
    """Handle incoming messages and forward to channels."""
    user = update.effective_user
    
    # Only owner can send messages to broadcast
    if user.id != OWNER_ID:
        update.message.reply_text("⚠️ You are not authorized to use this bot.")
        return
    
    # Check if message is a command
    if update.message.text and update.message.text.startswith('/'):
        return
    
    # Forward to all channels
    forward_to_all_channels(update.message, context)

def button_callback(update: Update, context: CallbackContext):
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    if query.data.startswith('remove_'):
        channel_id = int(query.data.replace('remove_', ''))
        
        for i, channel in enumerate(channels):
            if channel['channel_id'] == channel_id:
                removed_channel = channels.pop(i)
                query.edit_message_text(
                    f"✅ Channel '{removed_channel['channel_title']}' removed successfully.\n"
                    f"Remaining channels: {len(channels)}"
                )
                return
        
        query.edit_message_text("Channel not found.")
    
    elif query.data == 'clear_yes':
        channel_count = len(channels)
        channels.clear()
        query.edit_message_text(f"✅ All {channel_count} channels have been cleared.")
    
    elif query.data == 'clear_no':
        query.edit_message_text("✅ Channel clearing cancelled.")

def error_handler(update: Update, context: CallbackContext):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Main function to run the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables!")
        return
    
    if OWNER_ID == 0:
        logger.error("OWNER_ID not set in environment variables!")
        return
    
    logger.info("Starting Channel Manager Bot...")
    
    # Create updater
    updater = Updater(BOT_TOKEN, use_context=True)
    
    # Get dispatcher
    dp = updater.dispatcher
    
    # Add command handlers
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("add_channel", add_channel_command))
    dp.add_handler(CommandHandler("remove_channel", remove_channel_command))
    dp.add_handler(CommandHandler("clear_channels", clear_channels_command))
    dp.add_handler(CommandHandler("list_channels", list_channels_command))
    dp.add_handler(CommandHandler("stats", stats_command))
    
    # Add message handler
    dp.add_handler(MessageHandler(Filters.all & ~Filters.command, handle_message))
    
    # Add callback query handler
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    dp.add_error_handler(error_handler)
    
    # Check if webhook or polling
    if WEBHOOK_URL and WEBHOOK_URL.startswith('http'):
        # Webhook mode
        logger.info(f"Starting webhook mode on {WEBHOOK_URL}")
        
        # Start Flask in a separate thread
        flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False))
        flask_thread.daemon = True
        flask_thread.start()
        
        # Set webhook
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
        
        logger.info("Bot started with webhook. Press Ctrl+C to stop.")
        updater.idle()
    else:
        # Polling mode
        logger.info("Starting polling mode...")
        updater.start_polling()
        logger.info("Bot started with polling. Press Ctrl+C to stop.")
        updater.idle()

if __name__ == '__main__':
    main()
