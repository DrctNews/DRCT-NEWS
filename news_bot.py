#!/usr/bin/env python3
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, Forbidden, BadRequest

# Bot configuration
BOT_TOKEN = "7887089972:AAGn8PdS5JaaUZt1KO_tGwOw0yGmdwJ-vIw"
ADMIN_ID = 958576807
GROUPS_FILE = "groups.json"

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class GroupManager:
    def __init__(self):
        self.groups_file = GROUPS_FILE
        self.groups = self.load_groups()
    
    def load_groups(self) -> Dict:
        """Load groups from JSON file"""
        try:
            with open(self.groups_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.info("Groups file not found, creating new one")
            return {}
        except json.JSONDecodeError:
            logger.error("Invalid JSON in groups file, starting fresh")
            return {}
    
    def save_groups(self):
        """Save groups to JSON file"""
        try:
            with open(self.groups_file, 'w') as f:
                json.dump(self.groups, f, indent=2)
            logger.info(f"Saved {len(self.groups)} groups to file")
        except Exception as e:
            logger.error(f"Error saving groups: {e}")
    
    def add_group(self, chat_id: int, chat_title: str, chat_type: str):
        """Add a new group to tracking"""
        group_id = str(chat_id)
        self.groups[group_id] = {
            'id': chat_id,
            'title': chat_title,
            'type': chat_type,
            'active': True,
            'added_date': str(datetime.now())
        }
        self.save_groups()
        logger.info(f"Added group: {chat_title} ({chat_id})")
    
    def remove_group(self, chat_id: int):
        """Remove a group from tracking"""
        group_id = str(chat_id)
        if group_id in self.groups:
            del self.groups[group_id]
            self.save_groups()
            logger.info(f"Removed group: {chat_id}")
    
    def deactivate_group(self, chat_id: int):
        """Mark a group as inactive (bot removed/blocked)"""
        group_id = str(chat_id)
        if group_id in self.groups:
            self.groups[group_id]['active'] = False
            self.save_groups()
            logger.info(f"Deactivated group: {chat_id}")
    
    def get_active_groups(self) -> List[int]:
        """Get list of active group IDs"""
        return [
            group['id'] for group in self.groups.values() 
            if group.get('active', True)
        ]
    
    def get_group_count(self) -> int:
        """Get count of active groups"""
        return len([g for g in self.groups.values() if g.get('active', True)])
    
    def get_groups_info(self) -> str:
        """Get formatted string with groups information"""
        active_groups = [g for g in self.groups.values() if g.get('active', True)]
        if not active_groups:
            return "📭 No active groups connected"
        
        info = f"📊 *Active Groups: {len(active_groups)}*\n\n"
        for group in active_groups:
            info += f"• {group['title']} ({group['type']})\n"
        
        return info

class NewsBot:
    def __init__(self):
        self.group_manager = GroupManager()
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == 'private':
            if user.id == ADMIN_ID:
                await update.message.reply_text(
                    "🎯 *Admin Panel*\n\n"
                    "Aap ab koi bhi message send kar sakte hain aur yeh sabhi connected groups mein forward ho jayega.\n\n"
                    "*Available Commands:*\n"
                    "/status - Bot ki status check karein\n"
                    "/groups - Connected groups ki list dekhen\n"
                    "/help - Help message dekhen",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "👋 Namaste! Main ek news broadcasting bot hun.\n\n"
                    "Mujhe apne group mein admin banake add kariye news updates receive karne ke liye!"
                )
        else:
            # Bot added to group
            await update.message.reply_text(
                "✅ Namaste! Main ab is group se connected hun.\n\n"
                "Main apne admin se news aur updates forward karunga. "
                "Please mujhe admin permissions dein messages send karne ke liye!"
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = update.effective_user
        
        if user.id == ADMIN_ID:
            help_text = (
                "🤖 *Admin Help*\n\n"
                "*Kaise use karein:*\n"
                "• Koi bhi message mujhe send kariye aur main sabhi groups mein forward kar dunga\n"
                "• Text, photos, videos, documents sab support hai\n\n"
                "*Commands:*\n"
                "/start - Bot start karein\n"
                "/status - Bot status check karein\n"
                "/groups - Connected groups list\n"
                "/help - Yeh help message\n\n"
                "*Features:*\n"
                "• Automatic group detection\n"
                "• Error handling aur logging\n"
                "• Sabhi message types ka support"
            )
        else:
            help_text = (
                "🤖 *Bot Help*\n\n"
                "Main ek news broadcasting bot hun jo apne admin se updates forward karta hun.\n\n"
                "*Updates receive karne ke liye:*\n"
                "1. Mujhe apne group mein add kariye\n"
                "2. Mujhe admin banayiye\n"
                "3. Aap automatically news updates receive karenge!\n\n"
                "Koi issue ho to mere admin se contact kariye."
            )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Sirf admin hi yeh command use kar sakte hain.")
            return
        
        group_count = self.group_manager.get_group_count()
        status_text = (
            f"🤖 *Bot Status*\n\n"
            f"✅ Bot chal raha hai\n"
            f"📊 Connected groups: {group_count}\n"
            f"👤 Admin ID: {ADMIN_ID}\n\n"
            f"Messages broadcast karne ke liye ready!"
        )
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /groups command"""
        user = update.effective_user
        
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Sirf admin hi yeh command use kar sakte hain.")
            return
        
        groups_info = self.group_manager.get_groups_info()
        await update.message.reply_text(groups_info, parse_mode='Markdown')
    
    async def handle_group_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle bot being added to or removed from groups"""
        chat = update.effective_chat
        
        # Check if bot was added to group
        if update.message and update.message.new_chat_members:
            bot_user = await context.bot.get_me()
            for member in update.message.new_chat_members:
                if member.id == bot_user.id:
                    # Bot was added to group
                    self.group_manager.add_group(
                        chat.id, 
                        chat.title or "Unknown Group", 
                        chat.type
                    )
                    logger.info(f"Bot added to group: {chat.title} ({chat.id})")
                    
                    # Notify admin
                    try:
                        admin_message = f"🎉 *Naya Group Connected!*\n\n"
                        admin_message += f"📝 Name: {chat.title}\n"
                        admin_message += f"🆔 ID: {chat.id}\n"
                        admin_message += f"📊 Total Groups: {self.group_manager.get_group_count()}"
                        
                        await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=admin_message,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify admin: {e}")
        
        # Check if bot was removed from group
        if update.message and update.message.left_chat_member:
            bot_user = await context.bot.get_me()
            if update.message.left_chat_member.id == bot_user.id:
                # Bot was removed from group
                self.group_manager.remove_group(chat.id)
                logger.info(f"Bot removed from group: {chat.title} ({chat.id})")
                
                # Notify admin
                try:
                    admin_message = f"❌ *Group Disconnected*\n\n"
                    admin_message += f"📝 Name: {chat.title}\n"
                    admin_message += f"🆔 ID: {chat.id}\n"
                    admin_message += f"📊 Total Groups: {self.group_manager.get_group_count()}"
                    
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=admin_message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin: {e}")
    
    async def broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages from admin and broadcast to all groups"""
        user = update.effective_user
        message = update.message
        
        # Only allow admin to broadcast
        if user.id != ADMIN_ID:
            return
        
        # Don't broadcast commands
        if message.text and message.text.startswith('/'):
            return
        
        active_groups = self.group_manager.get_active_groups()
        
        if not active_groups:
            await message.reply_text(
                "📭 Koi active groups nahi hain broadcast karne ke liye.\n"
                "Bot ko groups mein admin banake add kariye broadcasting start karne ke liye!"
            )
            return
        
        success_count = 0
        failed_count = 0
        failed_groups = []
        
        # Send "sending" notification to admin
        sending_msg = await message.reply_text(
            f"📤 Message broadcast kar raha hun {len(active_groups)} groups mein...",
            parse_mode='Markdown'
        )
        
        # Broadcast to all active groups
        for group_id in active_groups:
            try:
                # Forward the message to the group
                await message.forward(group_id)
                success_count += 1
                logger.info(f"Message forwarded to group {group_id}")
                
            except Forbidden:
                # Bot was blocked or removed
                self.group_manager.deactivate_group(group_id)
                failed_count += 1
                failed_groups.append(group_id)
                logger.warning(f"Bot blocked in group {group_id}")
                
            except BadRequest as e:
                # Other errors (insufficient permissions, etc.)
                failed_count += 1
                failed_groups.append(group_id)
                logger.error(f"Failed to send to group {group_id}: {e}")
                
            except Exception as e:
                # Unexpected errors
                failed_count += 1
                failed_groups.append(group_id)
                logger.error(f"Unexpected error for group {group_id}: {e}")
        
        # Update the status message
        status_text = f"📤 *Broadcast Complete!*\n\n"
        status_text += f"✅ Successfully sent: {success_count} groups\n"
        
        if failed_count > 0:
            status_text += f"❌ Failed: {failed_count} groups\n"
            status_text += f"💡 Failed groups have been deactivated"
        
        await sending_msg.edit_text(status_text, parse_mode='Markdown')
    
    async def post_init(self, application):
        """Post initialization setup"""
        bot_info = await application.bot.get_me()
        logger.info(f"Bot started: @{bot_info.username} ({bot_info.first_name})")
        logger.info(f"Admin ID: {ADMIN_ID}")
        
        # Send startup notification to admin
        try:
            startup_msg = f"🤖 *Bot Successfully Started!*\n\n"
            startup_msg += f"🏷️ Username: @{bot_info.username}\n"
            startup_msg += f"📊 Connected Groups: {self.group_manager.get_group_count()}\n"
            startup_msg += f"👤 Admin: {ADMIN_ID}\n\n"
            startup_msg += f"✅ Ready for broadcasting!"
            
            await application.bot.send_message(
                chat_id=ADMIN_ID,
                text=startup_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    def setup_handlers(self):
        """Set up all bot handlers"""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("groups", self.groups_command))
        
        # Group membership changes
        app.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER,
            self.handle_group_update
        ))
        
        # Admin message broadcasting (all message types except commands)
        app.add_handler(MessageHandler(
            filters.ALL & ~filters.COMMAND & filters.User(ADMIN_ID),
            self.broadcast_message
        ))
        
        logger.info("All handlers set up successfully")
    
    def run(self):
        """Start the bot"""
        try:
            # Create application
            self.application = Application.builder().token(BOT_TOKEN).post_init(self.post_init).build()
            
            # Set up handlers
            self.setup_handlers()
            
            logger.info("Starting Hindi news broadcasting bot...")
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