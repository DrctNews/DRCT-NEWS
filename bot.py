import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN, ADMIN_ID
from handlers import BotHandlers

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class NewsBot:
    def __init__(self):
        self.handlers = BotHandlers()
        self.application = None
    
    def setup_handlers(self):
        """Set up all bot handlers"""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.handlers.start_command))
        app.add_handler(CommandHandler("help", self.handlers.help_command))
        app.add_handler(CommandHandler("status", self.handlers.status_command))
        app.add_handler(CommandHandler("groups", self.handlers.groups_command))
        
        # Group membership changes
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER,
            self.handlers.handle_group_update
        ))
        
        # Admin message broadcasting (all message types)
        app.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND & filters.User(ADMIN_ID),
            self.handlers.broadcast_message
        ))
        
        logger.info("All handlers set up successfully")
    
    async def post_init(self, application):
        """Post initialization setup"""
        bot_info = await application.bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} ({bot_info.first_name})")
        logger.info(f"Admin ID: {ADMIN_ID}")
        
        # Update bot username in config if needed
        import config
        config.BOT_USERNAME = bot_info.username
    
    def run(self):
        """Start the bot"""
        try:
            # Create application
            self.application = Application.builder().token(BOT_TOKEN).post_init(self.post_init).build()
            
            # Set up handlers
            self.setup_handlers()
            
            logger.info("Starting news broadcasting bot...")
            logger.info(f"Admin ID: {ADMIN_ID}")
            
            # Run the bot
            self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

def main():
    """Main function to start the bot"""
    try:
        bot = NewsBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()
