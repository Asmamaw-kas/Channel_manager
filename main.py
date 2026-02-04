import logging
import os
import threading
import time
import requests
import uvicorn
from fastapi import FastAPI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# ─────────────────────────────
#  LOGGING
# ─────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────
#  FASTAPI APP
# ─────────────────────────────
app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Channel Manager Bot is running!", "timestamp": time.time()}

@app.get("/ping")
def ping():
    return {"status": "pong", "timestamp": time.time()}

@app.get("/stats")
def stats():
    return {
        "status": "ok",
        "channels_count": len(CHANNELS),
        "channels": CHANNELS,
        "owner_id": OWNER_ID,
        "uptime": time.time() - START_TIME
    }

# ─────────────────────────────
#  ENVIRONMENT VARIABLES
# ─────────────────────────────
TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
RENDER_URL = os.getenv("RENDER_URL", "https://your-bot-name.onrender.com")
START_TIME = time.time()

# ─────────────────────────────
#  GLOBAL VARIABLES
# ─────────────────────────────
CHANNELS = []  # Store channels: [{"id": -100xxx, "title": "Channel Name", "username": "@channel"}]

# ─────────────────────────────
#  TELEGRAM COMMAND HANDLERS
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📢 Add Channel", callback_data="add_channel")],
        [InlineKeyboardButton("📋 List Channels", callback_data="list_channels")],
        [InlineKeyboardButton("🗑️ Remove Channel", callback_data="remove_channel")],
        [InlineKeyboardButton("🔄 Clear All", callback_data="clear_all")],
        [InlineKeyboardButton("📊 Statistics", callback_data="stats_cmd")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 *Channel Manager Bot*\n\n"
        "📌 *Features:*\n"
        "• Add bot as admin to channels\n"
        "• Forward messages to all channels\n"
        "• Manage multiple channels easily\n\n"
        "📌 *How to use:*\n"
        "1. Add bot as admin to your channels\n"
        "2. Use /addchannel to register channels\n"
        "3. Send any media/message to forward\n\n"
        "📌 *Commands:*\n"
        "/start - Show this menu\n"
        "/addchannel - Add a channel\n"
        "/listchannels - List all channels\n"
        "/removechannel - Remove a channel\n"
        "/clearchannels - Clear all channels\n"
        "/stats - Show statistics\n"
        "/help - Show help",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    help_text = """
📚 *Channel Manager Bot - Help Guide*

*1. Setup:*
- Add bot as admin to your channels
- Grant all permissions (Post Messages required)

*2. Add Channels:*
- Use `/addchannel @channel_username`
- Or `/addchannel channel_id`
- Bot will verify admin status

*3. Send Broadcasts:*
- Simply send any message/media to bot
- Bot forwards to all registered channels
- Supports: Text, Photos, Videos, Documents, Audio, Voice

*4. Manage Channels:*
- `/listchannels` - View all channels
- `/removechannel` - Remove specific channel
- `/clearchannels` - Remove ALL channels
- `/stats` - View statistics

*5. Notes:*
- Channels stored in memory
- Reset on bot restart
- Only you (owner) can use bot
    """
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def addchannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a channel to the bot"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "📝 *Usage:*\n"
            "`/addchannel @channel_username`\n"
            "`/addchannel channel_id`\n\n"
            "Or forward a message from the channel and reply with `/addchannel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_identifier = args[0]
    
    try:
        # Get channel info
        if channel_identifier.startswith('@'):
            chat = await context.bot.get_chat(channel_identifier)
        else:
            chat = await context.bot.get_chat(int(channel_identifier))
        
        # Check if bot is admin
        chat_member = await context.bot.get_chat_member(chat.id, context.bot.id)
        
        if chat_member.status not in ['administrator', 'creator']:
            await update.message.reply_text(
                f"❌ *Bot is not admin in* `{chat.title}`\n"
                "Please add bot as administrator first with all permissions.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check if already exists
        for channel in CHANNELS:
            if channel['id'] == chat.id:
                await update.message.reply_text(
                    f"⚠️ *Channel already registered:*\n`{chat.title}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        # Add channel
        CHANNELS.append({
            'id': chat.id,
            'username': chat.username,
            'title': chat.title,
            'added_by': update.effective_user.id,
            'added_time': time.time()
        })
        
        await update.message.reply_text(
            f"✅ *Channel Added Successfully!*\n\n"
            f"📛 *Title:* {chat.title}\n"
            f"🆔 *ID:* `{chat.id}`\n"
            f"👤 *Username:* @{chat.username or 'N/A'}\n"
            f"📊 *Total Channels:* {len(CHANNELS)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await update.message.reply_text(
            f"❌ *Error adding channel:*\n`{str(e)}`\n\n"
            "*Make sure:*\n"
            "1. Bot is added to channel\n"
            "2. Bot is administrator\n"
            "3. Username/ID is correct",
            parse_mode=ParseMode.MARKDOWN
        )

async def listchannels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all registered channels"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    if not CHANNELS:
        await update.message.reply_text("📭 *No channels registered yet.*", parse_mode=ParseMode.MARKDOWN)
        return
    
    message = "📋 *Registered Channels:*\n\n"
    for i, channel in enumerate(CHANNELS, 1):
        message += f"{i}. *{channel['title']}*\n"
        message += f"   • ID: `{channel['id']}`\n"
        message += f"   • Username: @{channel['username'] or 'N/A'}\n\n"
    
    message += f"📊 *Total:* {len(CHANNELS)} channels"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def removechannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a channel"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    if not CHANNELS:
        await update.message.reply_text("📭 *No channels to remove.*", parse_mode=ParseMode.MARKDOWN)
        return
    
    args = context.args
    
    if not args:
        # Create inline keyboard with channels
        keyboard = []
        for channel in CHANNELS:
            button_text = f"❌ {channel['title'][:30]}"
            callback_data = f"remove_{channel['id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🗑️ *Select a channel to remove:*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        channel_id = int(args[0])
        for i, channel in enumerate(CHANNELS):
            if channel['id'] == channel_id:
                removed = CHANNELS.pop(i)
                await update.message.reply_text(
                    f"✅ *Channel Removed:*\n`{removed['title']}`\n"
                    f"📊 *Remaining:* {len(CHANNELS)} channels",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        await update.message.reply_text("❌ *Channel not found.*", parse_mode=ParseMode.MARKDOWN)
    
    except ValueError:
        await update.message.reply_text("❌ *Invalid channel ID.*", parse_mode=ParseMode.MARKDOWN)

async def clearchannels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all channels"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    if not CHANNELS:
        await update.message.reply_text("📭 *No channels to clear.*", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Confirmation buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, clear all", callback_data="clear_yes"),
            InlineKeyboardButton("❌ No, cancel", callback_data="clear_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ *Confirm Clear All Channels*\n\n"
        f"This will remove *{len(CHANNELS)}* channels.\n"
        f"*This action cannot be undone!*",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⚠️ Unauthorized. Only owner can use this bot.")
        return
    
    uptime_seconds = time.time() - START_TIME
    uptime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime_seconds))
    
    stats_text = f"""
📊 *Bot Statistics*

🤖 *Bot Info:*
• Username: @{context.bot.username}
• Owner ID: `{OWNER_ID}`
• Uptime: {uptime_str}

📢 *Channels:*
• Total: {len(CHANNELS)} channels

🔄 *System:*
• Status: Running
• Mode: Polling
• Storage: Memory
• Restart: Channels reset on restart

🔗 *Render URL:*
{RENDER_URL}
    """
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def forward_to_channels(message, context: ContextTypes.DEFAULT_TYPE):
    """Forward message to all channels"""
    if not CHANNELS:
        if message.chat.type != 'private':
            await message.reply_text("📭 *No channels registered. Use /addchannel first.*", parse_mode=ParseMode.MARKDOWN)
        return
    
    total = len(CHANNELS)
    successful = 0
    failed = 0
    
    # Send processing message
    status_msg = await message.reply_text(f"📤 *Broadcasting to {total} channels...*", parse_mode=ParseMode.MARKDOWN)
    
    for channel in CHANNELS:
        try:
            # Forward based on message type
            if message.photo:
                await context.bot.send_photo(
                    chat_id=channel['id'],
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=channel['id'],
                    video=message.video.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=channel['id'],
                    document=message.document.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=channel['id'],
                    audio=message.audio.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.voice:
                await context.bot.send_voice(
                    chat_id=channel['id'],
                    voice=message.voice.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            elif message.sticker:
                await context.bot.send_sticker(
                    chat_id=channel['id'],
                    sticker=message.sticker.file_id
                )
            elif message.animation:
                await context.bot.send_animation(
                    chat_id=channel['id'],
                    animation=message.animation.file_id,
                    caption=message.caption,
                    caption_entities=message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            else:
                # Text message
                await context.bot.send_message(
                    chat_id=channel['id'],
                    text=message.text or message.caption or "📢 Broadcast",
                    entities=message.entities or message.caption_entities,
                    parse_mode=ParseMode.HTML
                )
            
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to send to channel {channel['id']}: {e}")
            failed += 1
            continue
    
    # Update status
    await status_msg.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"✅ *Successful:* {successful}\n"
        f"❌ *Failed:* {failed}\n"
        f"📊 *Total:* {total}",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user = update.effective_user
    
    # Check if owner
    if user.id != OWNER_ID:
        await update.message.reply_text("⚠️ *Unauthorized.* Only the owner can use this bot.", parse_mode=ParseMode.MARKDOWN)
        return
    
    # Skip commands
    if update.message.text and update.message.text.startswith('/'):
        return
    
    # Forward to all channels
    await forward_to_channels(update.message, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "add_channel":
        await query.edit_message_text(
            "📝 *Add Channel Instructions:*\n\n"
            "1. Add bot as admin to your channel\n"
            "2. Use command:\n"
            "`/addchannel @channel_username`\n"
            "or\n"
            "`/addchannel channel_id`\n\n"
            "Bot will verify admin status automatically.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "list_channels":
        if not CHANNELS:
            await query.edit_message_text("📭 *No channels registered yet.*", parse_mode=ParseMode.MARKDOWN)
            return
        
        message = "📋 *Registered Channels:*\n\n"
        for i, channel in enumerate(CHANNELS, 1):
            message += f"{i}. *{channel['title']}*\n"
            message += f"   • ID: `{channel['id']}`\n\n"
        
        message += f"📊 *Total:* {len(CHANNELS)} channels"
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
    
    elif data == "remove_channel":
        if not CHANNELS:
            await query.edit_message_text("📭 *No channels to remove.*", parse_mode=ParseMode.MARKDOWN)
            return
        
        keyboard = []
        for channel in CHANNELS:
            button_text = f"❌ {channel['title'][:30]}"
            callback_data = f"remove_{channel['id']}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗑️ *Select a channel to remove:*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "clear_all":
        if not CHANNELS:
            await query.edit_message_text("📭 *No channels to clear.*", parse_mode=ParseMode.MARKDOWN)
            return
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, clear all", callback_data="clear_yes"),
                InlineKeyboardButton("❌ No, cancel", callback_data="clear_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ *Confirm Clear All Channels*\n\n"
            f"This will remove *{len(CHANNELS)}* channels.\n"
            f"*This action cannot be undone!*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "stats_cmd":
        uptime_seconds = time.time() - START_TIME
        uptime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime_seconds))
        
        stats_text = f"""
📊 *Bot Statistics*

🤖 *Bot Info:*
• Username: @{context.bot.username}
• Owner ID: `{OWNER_ID}`
• Uptime: {uptime_str}

📢 *Channels:*
• Total: {len(CHANNELS)} channels

🔄 *System:*
• Status: Active
• Mode: Polling
• Storage: Memory
        """
        
        await query.edit_message_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    elif data.startswith("remove_"):
        channel_id = int(data.replace("remove_", ""))
        
        for i, channel in enumerate(CHANNELS):
            if channel['id'] == channel_id:
                removed = CHANNELS.pop(i)
                await query.edit_message_text(
                    f"✅ *Channel Removed:*\n`{removed['title']}`\n"
                    f"📊 *Remaining:* {len(CHANNELS)} channels",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        await query.edit_message_text("❌ *Channel not found.*", parse_mode=ParseMode.MARKDOWN)
    
    elif data == "clear_yes":
        channel_count = len(CHANNELS)
        CHANNELS.clear()
        await query.edit_message_text(
            f"✅ *All {channel_count} channels cleared.*\n"
            f"Use /addchannel to add new channels.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "clear_no":
        await query.edit_message_text(
            "✅ *Operation cancelled.*\n"
            f"Channels preserved: {len(CHANNELS)}",
            parse_mode=ParseMode.MARKDOWN
        )

# ─────────────────────────────
#  KEEP ALIVE SYSTEM (PREVENTS SLEEP)
# ─────────────────────────────
def keep_alive():
    """Ping Render service to prevent sleep"""
    urls_to_ping = [
        RENDER_URL,
        f"{RENDER_URL}/",
        f"{RENDER_URL}/ping",
        f"{RENDER_URL}/stats"
    ]
    
    logger.info("🔔 Starting keep-alive system...")
    
    while True:
        try:
            for url in urls_to_ping:
                try:
                    response = requests.get(url, timeout=10)
                    logger.info(f"✅ Pinged {url} - Status: {response.status_code}")
                except Exception as e:
                    logger.warning(f"⚠️ Ping failed for {url}: {e}")
            
            # Wait before next ping cycle
            time.sleep(120)  # Ping every 2 minutes
        
        except Exception as e:
            logger.error(f"❌ Keep-alive error: {e}")
            time.sleep(60)

# ─────────────────────────────
#  BOT HEALTH MONITOR
# ─────────────────────────────
def bot_health_monitor(application):
    """Monitor bot health"""
    logger.info("❤️ Starting health monitor...")
    
    while True:
        try:
            # Check bot status
            bot_info = application.bot.get_me()
            logger.info(f"🤖 Bot healthy: @{bot_info.username}")
            
            # Log channel count
            logger.info(f"📊 Channels: {len(CHANNELS)}")
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
        
        time.sleep(300)  # Check every 5 minutes

# ─────────────────────────────
#  RUN FASTAPI SERVER
# ─────────────────────────────
def run_fastapi():
    """Run FastAPI server"""
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Starting FastAPI on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

# ─────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────
def main():
    """Main function to start everything"""
    # Validate environment variables
    if not TOKEN:
        logger.error("❌ Missing BOT_TOKEN environment variable")
        raise ValueError("BOT_TOKEN is required")
    
    if not OWNER_ID:
        logger.error("❌ Missing OWNER_ID environment variable")
        raise ValueError("OWNER_ID is required")
    
    logger.info("=" * 50)
    logger.info("🤖 Starting Channel Manager Bot")
    logger.info(f"👤 Owner ID: {OWNER_ID}")
    logger.info(f"🌐 Render URL: {RENDER_URL}")
    logger.info("=" * 50)
    
    # Start FastAPI server in background thread
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    logger.info("✅ FastAPI server started")
    
    # Start keep-alive system
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("✅ Keep-alive system started")
    
    # Create and configure bot
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("addchannel", addchannel_cmd))
    application.add_handler(CommandHandler("listchannels", listchannels_cmd))
    application.add_handler(CommandHandler("removechannel", removechannel_cmd))
    application.add_handler(CommandHandler("clearchannels", clearchannels_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    
    # Add button handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Start health monitor
    health_thread = threading.Thread(target=bot_health_monitor, args=(application,), daemon=True)
    health_thread.start()
    logger.info("✅ Health monitor started")
    
    logger.info("✅ All systems started successfully!")
    logger.info("🤖 Bot is now running...")
    
    try:
        # Run bot with polling
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        logger.info("🔄 Attempting to restart in 30 seconds...")
        time.sleep(30)
        main()  # Auto-restart

if __name__ == "__main__":
    main()
