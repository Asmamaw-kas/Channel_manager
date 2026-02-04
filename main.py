import logging
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler
)
from telegram.constants import ParseMode
from config import Config

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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    if update.effective_user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ You are not authorized to use this bot.")
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
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new channel to the bot."""
    if update.effective_user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ Only the owner can add channels.")
        return
    
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Please provide channel username or ID.\n"
            "Usage: `/add_channel @channel_username`\n"
            "Or forward a message from the channel and use /add_channel",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_identifier = args[0]
    
    try:
        # Try to get channel info
        if channel_identifier.startswith('@'):
            chat = await context.bot.get_chat(channel_identifier)
        else:
            # Try as channel ID
            chat = await context.bot.get_chat(int(channel_identifier))
        
        # Check if bot is admin in the channel
        chat_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                f"❌ Bot is not admin in {chat.title}.\n"
                f"Please add bot as administrator first with all permissions."
            )
            return
        
        # Check if channel already exists
        for channel in channels:
            if channel['channel_id'] == chat.id:
                await update.message.reply_text(
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
        
        await update.message.reply_text(
            f"✅ Channel *{chat.title}* has been added successfully!\n"
            f"• ID: `{chat.id}`\n"
            f"• Username: @{chat.username or 'N/A'}\n"
            f"• Total channels: {len(channels)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}\n\n"
            "Make sure:\n"
            "1. Bot is added to the channel\n"
            "2. Bot is administrator\n"
            "3. Channel username/ID is correct"
        )

async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a channel from the bot."""
    if update.effective_user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ Only the owner can remove channels.")
        return
    
    if not channels:
        await update.message.reply_text("No channels registered.")
        return
    
    if not context.args:
        # Show list of channels for removal
        keyboard = []
        for i, channel in enumerate(channels, 1):
            button_text = f"{i}. {channel['channel_title'][:30]}"
            callback_data = f"remove_{channel['channel_id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
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
                await update.message.reply_text(
                    f"✅ Channel '{removed_channel['channel_title']}' removed successfully.\n"
                    f"Remaining channels: {len(channels)}"
                )
                return
        
        await update.message.reply_text("Channel not found.")
    
    except ValueError:
        await update.message.reply_text("Please provide a valid channel ID.")

async def clear_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove ALL channels."""
    if update.effective_user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ Only the owner can clear channels.")
        return
    
    if not channels:
        await update.message.reply_text("No channels to clear.")
        return
    
    # Create confirmation buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, clear all", callback_data="clear_yes"),
            InlineKeyboardButton("❌ No, keep them", callback_data="clear_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ Are you sure you want to remove ALL {len(channels)} channels?\n"
        "This action cannot be undone!",
        reply_markup=reply_markup
    )

async def list_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered channels."""
    if update.effective_user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ Only the owner can view channels.")
        return
    
    if not channels:
        await update.message.reply_text("No channels registered yet.")
        return
    
    message = "📊 *Registered Channels:*\n\n"
    for i, channel in enumerate(channels, 1):
        message += f"{i}. *{channel['channel_title']}*\n"
        message += f"   • ID: `{channel['channel_id']}`\n"
        message += f"   • Username: @{channel['channel_username'] or 'N/A'}\n\n"
    
    message += f"Total: {len(channels)} channels"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    if update.effective_user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ Only the owner can view statistics.")
        return
    
    stats_text = f"""
📈 *Bot Statistics*

*Channels:*
• Currently Registered: {len(channels)}

*Bot Info:*
• Username: @{context.bot.username}
• Owner ID: {Config.OWNER_ID}

*Storage:*
• Channels stored in memory
• Will reset on bot restart
    """
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def forward_to_all_channels(message, context: ContextTypes.DEFAULT_TYPE):
    """Forward a message to all registered channels."""
    if not channels:
        if message.chat.type != 'private':
            await message.reply_text("No channels registered yet. Use /add_channel first.")
        return
    
    total_channels = len(channels)
    successful = 0
    failed = 0
    
    # Send processing message
    status_msg = await message.reply_text(f"📤 Broadcasting to {total_channels} channels...")
    
    for channel in channels:
        try:
            # Forward the message based on type
            if message.photo:
                await context.bot.send_photo(
                    chat_id=channel['channel_id'],
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=channel['channel_id'],
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=channel['channel_id'],
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=channel['channel_id'],
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.voice:
                await context.bot.send_voice(
                    chat_id=channel['channel_id'],
                    voice=message.voice.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.sticker:
                await context.bot.send_sticker(
                    chat_id=channel['channel_id'],
                    sticker=message.sticker.file_id
                )
            elif message.animation:
                await context.bot.send_animation(
                    chat_id=channel['channel_id'],
                    animation=message.animation.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Text message
                await context.bot.send_message(
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
    await status_msg.edit_text(
        f"✅ Broadcast completed!\n\n"
        f"• ✅ Successful: {successful}\n"
        f"• ❌ Failed: {failed}\n"
        f"• 📊 Total: {total_channels}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and forward to channels."""
    user = update.effective_user
    
    # Only owner can send messages to broadcast
    if user.id != Config.OWNER_ID:
        await update.message.reply_text("⚠️ You are not authorized to use this bot.")
        return
    
    # Check if message is a command
    if update.message.text and update.message.text.startswith('/'):
        return
    
    # Forward to all channels
    await forward_to_all_channels(update.message, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('remove_'):
        channel_id = int(query.data.replace('remove_', ''))
        
        for i, channel in enumerate(channels):
            if channel['channel_id'] == channel_id:
                removed_channel = channels.pop(i)
                await query.edit_message_text(
                    f"✅ Channel '{removed_channel['channel_title']}' removed successfully.\n"
                    f"Remaining channels: {len(channels)}"
                )
                return
        
        await query.edit_message_text("Channel not found.")
    
    elif query.data == 'clear_yes':
        channel_count = len(channels)
        channels.clear()
        await query.edit_message_text(f"✅ All {channel_count} channels have been cleared.")
    
    elif query.data == 'clear_no':
        await query.edit_message_text("✅ Channel clearing cancelled.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

async def post_init(application: Application):
    """Post initialization."""
    await application.bot.set_my_commands([
        ("start", "Start the bot"),
        ("add_channel", "Add a new channel"),
        ("remove_channel", "Remove a channel"),
        ("clear_channels", "Remove ALL channels"),
        ("list_channels", "List all channels"),
        ("stats", "Show statistics"),
        ("help", "Show help")
    ])
    
    logger.info(f"Bot @{application.bot.username} started successfully!")
    logger.info(f"Owner ID: {Config.OWNER_ID}")

def setup_bot():
    """Setup and run the bot."""
    # Create application
    application = Application.builder().token(Config.BOT_TOKEN).post_init(post_init).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add_channel", add_channel_command))
    application.add_handler(CommandHandler("remove_channel", remove_channel_command))
    application.add_handler(CommandHandler("clear_channels", clear_channels_command))
    application.add_handler(CommandHandler("list_channels", list_channels_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application

def run_flask():
    """Run Flask app."""
    logger.info("Starting Flask server...")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False, use_reloader=False)

def main():
    """Main function to run both bot and Flask."""
    logger.info("Starting Channel Manager Bot...")
    
    # Get the bot application
    bot_application = setup_bot()
    
    # Check if we should use webhook or polling
    if Config.WEBHOOK_URL and Config.WEBHOOK_URL.startswith('http'):
        # Webhook mode for production
        logger.info(f"Starting in WEBHOOK mode")
        logger.info(f"Webhook URL: {Config.WEBHOOK_URL}")
        
        # Start Flask first, then set up webhook
        import threading
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Give Flask time to start
        import time
        time.sleep(2)
        
        # Run bot with webhook
        bot_application.run_webhook(
            listen="0.0.0.0",
            port=Config.PORT,
            url_path=Config.BOT_TOKEN,
            webhook_url=f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}",
        )
    else:
        # Polling mode for development
        logger.info("Starting in POLLING mode")
        
        # Run bot with polling
        bot_application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()