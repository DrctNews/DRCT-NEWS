import logging
from telegram import Update, Bot
from telegram.ext import ContextTypes
from telegram.error import TelegramError, Forbidden, BadRequest
from config import ADMIN_ID
from utils import GroupManager

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self):
        self.group_manager = GroupManager()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type == 'private':
            if user.id == ADMIN_ID:
                await update.message.reply_text(
                    "🎯 *Admin Panel*\n\n"
                    "Welcome! You can now send any message and it will be forwarded to all connected groups.\n\n"
                    "*Available Commands:*\n"
                    "/status - Check bot status\n"
                    "/groups - List connected groups\n"
                    "/help - Show help message",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "👋 Hello! I'm a news broadcasting bot.\n\n"
                    "Add me to your group as an admin to receive news updates!"
                )
        else:
            # Bot added to group
            await update.message.reply_text(
                "✅ Hello! I'm now connected to this group.\n\n"
                "I'll forward news and updates from my admin. "
                "Make sure I have admin permissions to send messages!"
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = update.effective_user
        
        if user.id == ADMIN_ID:
            help_text = (
                "🤖 *Admin Help*\n\n"
                "*How to use:*\n"
                "• Send any message to me and I'll forward it to all groups\n"
                "• Supports text, photos, videos, documents, etc.\n\n"
                "*Commands:*\n"
                "/start - Start the bot\n"
                "/status - Check bot status\n"
                "/groups - List connected groups\n"
                "/help - Show this help\n\n"
                "*Features:*\n"
                "• Automatic group detection\n"
                "• Error handling and logging\n"
                "• Support for all message types"
            )
        else:
            help_text = (
                "🤖 *Bot Help*\n\n"
                "I'm a news broadcasting bot that forwards updates from my admin.\n\n"
                "*To receive updates:*\n"
                "1. Add me to your group\n"
                "2. Make me an admin\n"
                "3. You'll receive news updates automatically!\n\n"
                "Contact my admin if you have any issues."
            )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user = update.effective_user
        
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Only admin can use this command.")
            return
        
        group_count = self.group_manager.get_group_count()
        status_text = (
            f"🤖 *Bot Status*\n\n"
            f"✅ Bot is running\n"
            f"📊 Connected groups: {group_count}\n"
            f"👤 Admin ID: {ADMIN_ID}\n\n"
            f"Ready to broadcast messages!"
        )
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /groups command"""
        user = update.effective_user
        
        if user.id != ADMIN_ID:
            await update.message.reply_text("❌ Only admin can use this command.")
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
        
        # Check if bot was removed from group
        if update.message and update.message.left_chat_member:
            bot_user = await context.bot.get_me()
            if update.message.left_chat_member.id == bot_user.id:
                # Bot was removed from group
                self.group_manager.remove_group(chat.id)
                logger.info(f"Bot removed from group: {chat.title} ({chat.id})")
    
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
                "📭 No active groups to broadcast to.\n"
                "Add the bot to groups as admin to start broadcasting!"
            )
            return
        
        success_count = 0
        failed_count = 0
        failed_groups = []
        
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
        
        # Send status update to admin
        status_text = f"📤 *Broadcast Complete*\n\n"
        status_text += f"✅ Sent to: {success_count} groups\n"
        
        if failed_count > 0:
            status_text += f"❌ Failed: {failed_count} groups\n"
            status_text += f"💡 Failed groups have been deactivated"
        
        await message.reply_text(status_text, parse_mode='Markdown')
