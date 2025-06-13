#!/usr/bin/env python3
import json
import logging
import time
import requests
from datetime import datetime
from typing import Dict, List

# Import configuration
from config import BOT_TOKEN, ADMIN_ID, GROUPS_FILE, BOT_USERNAME

# Bot configuration
ADMIN_IDS = [ADMIN_ID, 5716244784, 6654985327, 6510157572]  # Multiple admins including primary
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

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

class TelegramBot:
    def __init__(self):
        self.group_manager = GroupManager()
        self.base_url = BASE_URL
        self.last_update_id = 0
        self.bot_username = None
        
    def make_request(self, method: str, params: dict = None) -> dict:
        """Make a request to Telegram API"""
        url = f"{self.base_url}/{method}"
        try:
            response = requests.post(url, json=params or {}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {method}, retrying...")
            return {"ok": False, "error": "timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"ok": False, "error": str(e)}
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = None, reply_to_message_id: int = None) -> dict:
        """Send a message to a chat"""
        params = {
            "chat_id": chat_id,
            "text": text[:4096]  # Telegram message limit
        }
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_to_message_id:
            params["reply_to_message_id"] = reply_to_message_id
            
        return self.make_request("sendMessage", params)
    
    def copy_message(self, chat_id: int, from_chat_id: int, message_id: int, caption: str = None) -> dict:
        """Copy a message to a chat (without forwarded label)"""
        params = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id
        }
        if caption:
            params["caption"] = caption
        return self.make_request("copyMessage", params)
    
    def forward_message(self, chat_id: int, from_chat_id: int, message_id: int) -> dict:
        """Forward a message to a chat"""
        params = {
            "chat_id": chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id
        }
        return self.make_request("forwardMessage", params)
    
    def get_updates(self, offset: int = None, timeout: int = 10) -> dict:
        """Get updates from Telegram"""
        params = {"timeout": timeout}
        if offset:
            params["offset"] = offset
        return self.make_request("getUpdates", params)
    
    def get_me(self) -> dict:
        """Get bot information"""
        return self.make_request("getMe")
    
    def handle_start_command(self, update: dict):
        """Handle /start command"""
        chat = update["message"]["chat"]
        user = update["message"]["from"]
        chat_id = chat["id"]
        
        if chat["type"] == "private":
            if user["id"] in ADMIN_IDS:
                self.send_message(
                    chat_id,
                    "🎯 *Admin Panel*\n\n"
                    "Aap ab koi bhi message send kar sakte hain aur yeh sabhi connected groups mein forward ho jayega.\n\n"
                    "*Available Commands:*\n"
                    "/status - Bot ki status check karein\n"
                    "/groups - Connected groups ki list dekhen\n"
                    "/help - Help message dekhen",
                    parse_mode="Markdown"
                )
            else:
                self.send_message(
                    chat_id,
                    "👋 Namaste! Main ek news broadcasting bot hun.\n\n"
                    "Mujhe apne group mein admin banake add kariye news updates receive karne ke liye!"
                )
        else:
            # Bot added to group
            self.send_message(
                chat_id,
                "✅ Namaste! Main ab is group se connected hun.\n\n"
                "Main apne admin se news aur updates forward karunga. "
                "Please mujhe admin permissions dein messages send karne ke liye!"
            )
    
    def handle_help_command(self, update: dict):
        """Handle /help command"""
        user = update["message"]["from"]
        chat_id = update["message"]["chat"]["id"]
        
        if user["id"] in ADMIN_IDS:
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
        
        self.send_message(chat_id, help_text, parse_mode="Markdown")
    
    def handle_status_command(self, update: dict):
        """Handle /status command"""
        user = update["message"]["from"]
        chat_id = update["message"]["chat"]["id"]
        
        if user["id"] not in ADMIN_IDS:
            self.send_message(chat_id, "❌ Sirf admin hi yeh command use kar sakte hain.")
            return
        
        group_count = self.group_manager.get_group_count()
        status_text = (
            f"🤖 *Bot Status*\n\n"
            f"✅ Bot chal raha hai\n"
            f"📊 Connected groups: {group_count}\n"
            f"👥 Admins: {len(ADMIN_IDS)}\n\n"
            f"Messages broadcast karne ke liye ready!"
        )
        
        self.send_message(chat_id, status_text, parse_mode="Markdown")
    
    def handle_groups_command(self, update: dict):
        """Handle /groups command"""
        user = update["message"]["from"]
        chat_id = update["message"]["chat"]["id"]
        
        if user["id"] not in ADMIN_IDS:
            self.send_message(chat_id, "❌ Sirf admin hi yeh command use kar sakte hain.")
            return
        
        groups_info = self.group_manager.get_groups_info()
        self.send_message(chat_id, groups_info, parse_mode="Markdown")
    
    def handle_group_updates(self, update: dict):
        """Handle bot being added to or removed from groups"""
        message = update.get("message", {})
        chat = message.get("chat", {})
        
        # Check if bot was added to group
        if "new_chat_members" in message:
            for member in message["new_chat_members"]:
                if member.get("username") == self.bot_username:
                    # Bot was added to group
                    self.group_manager.add_group(
                        chat["id"], 
                        chat.get("title", "Unknown Group"), 
                        chat["type"]
                    )
                    logger.info(f"Bot added to group: {chat.get('title')} ({chat['id']})")
                    
                    # Notify all admins
                    admin_message = f"🎉 *Naya Group Connected!*\n\n"
                    admin_message += f"📝 Name: {chat.get('title', 'Unknown')}\n"
                    admin_message += f"🆔 ID: {chat['id']}\n"
                    admin_message += f"📊 Total Groups: {self.group_manager.get_group_count()}"
                    
                    for admin_id in ADMIN_IDS:
                        self.send_message(admin_id, admin_message, parse_mode="Markdown")
        
        # Check if bot was removed from group
        if "left_chat_member" in message:
            left_member = message["left_chat_member"]
            if left_member.get("username") == self.bot_username:
                # Bot was removed from group
                self.group_manager.remove_group(chat["id"])
                logger.info(f"Bot removed from group: {chat.get('title')} ({chat['id']})")
                
                # Notify all admins
                admin_message = f"❌ *Group Disconnected*\n\n"
                admin_message += f"📝 Name: {chat.get('title', 'Unknown')}\n"
                admin_message += f"🆔 ID: {chat['id']}\n"
                admin_message += f"📊 Total Groups: {self.group_manager.get_group_count()}"
                
                for admin_id in ADMIN_IDS:
                    self.send_message(admin_id, admin_message, parse_mode="Markdown")
    
    def broadcast_message(self, update: dict):
        """Handle messages from admin and broadcast to all groups"""
        message = update["message"]
        user = message["from"]
        chat_id = message["chat"]["id"]
        
        # Only allow admins to broadcast
        if user["id"] not in ADMIN_IDS:
            return
        
        # Don't broadcast commands
        if message.get("text", "").startswith('/'):
            return
        
        active_groups = self.group_manager.get_active_groups()
        
        if not active_groups:
            self.send_message(
                chat_id,
                "📭 Koi active groups nahi hain broadcast karne ke liye.\n"
                "Bot ko groups mein admin banake add kariye broadcasting start karne ke liye!"
            )
            return
        
        success_count = 0
        failed_count = 0
        
        # Send "sending" notification to admin
        sending_response = self.send_message(
            chat_id,
            f"📤 Message broadcast kar raha hun {len(active_groups)} groups mein...",
            parse_mode="Markdown"
        )
        
        # Broadcast to all active groups
        for group_id in active_groups:
            try:
                # Copy the message to the group (without "Forwarded from" label)
                result = self.copy_message(group_id, chat_id, message["message_id"])
                if result.get("ok"):
                    success_count += 1
                    logger.info(f"Message copied to group {group_id}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to copy to group {group_id}: {result}")
                    if "chat not found" in str(result).lower() or "bot was blocked" in str(result).lower():
                        self.group_manager.deactivate_group(group_id)
                        
            except Exception as e:
                failed_count += 1
                logger.error(f"Unexpected error for group {group_id}: {e}")
        
        # Update the status message
        status_text = f"📤 *Broadcast Complete!*\n\n"
        status_text += f"✅ Successfully sent: {success_count} groups\n"
        
        if failed_count > 0:
            status_text += f"❌ Failed: {failed_count} groups\n"
            status_text += f"💡 Failed groups have been deactivated"
        
        # Edit the sending message to show results
        if sending_response.get("ok"):
            message_id = sending_response["result"]["message_id"]
            edit_params = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": status_text,
                "parse_mode": "Markdown"
            }
            self.make_request("editMessageText", edit_params)
    
    def process_update(self, update: dict):
        """Process a single update"""
        try:
            if "message" not in update:
                return
            
            message = update["message"]
            text = message.get("text", "")
            
            # Handle commands
            if text.startswith("/start"):
                self.handle_start_command(update)
            elif text.startswith("/help"):
                self.handle_help_command(update)
            elif text.startswith("/status"):
                self.handle_status_command(update)
            elif text.startswith("/groups"):
                self.handle_groups_command(update)
            
            # Handle group membership changes
            if "new_chat_members" in message or "left_chat_member" in message:
                self.handle_group_updates(update)
            
            # Handle admin messages for broadcasting
            if message["chat"]["type"] == "private":
                self.broadcast_message(update)
                
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def start_polling(self):
        """Start the bot and begin polling for updates"""
        # Get bot info
        me_response = self.get_me()
        if me_response.get("ok"):
            bot_info = me_response["result"]
            self.bot_username = bot_info["username"]
            logger.info(f"Bot started: @{bot_info['username']} ({bot_info['first_name']})")
            logger.info(f"Admin IDs: {ADMIN_IDS}")
            
            # Send startup notification to all admins (with error handling)
            startup_msg = f"🤖 *Bot Successfully Started!*\n\n"
            startup_msg += f"🏷️ Username: @{bot_info['username']}\n"
            startup_msg += f"📊 Connected Groups: {self.group_manager.get_group_count()}\n"
            startup_msg += f"👥 Admins: {len(ADMIN_IDS)}\n\n"
            startup_msg += f"✅ Ready for broadcasting!"
            
            for admin_id in ADMIN_IDS:
                try:
                    result = self.send_message(admin_id, startup_msg, parse_mode="Markdown")
                    if not result.get("ok"):
                        logger.warning(f"Failed to send startup message to admin {admin_id}: {result}")
                except Exception as e:
                    logger.warning(f"Error sending startup message to admin {admin_id}: {e}")
        else:
            logger.error("Failed to get bot info")
            return
        
        logger.info("Starting to poll for updates...")
        
        while True:
            try:
                # Get updates
                updates_response = self.get_updates(offset=self.last_update_id + 1, timeout=10)
                
                if not updates_response.get("ok"):
                    error = updates_response.get("error", "unknown error")
                    if "timeout" in error.lower():
                        # Timeout is normal, just continue
                        continue
                    else:
                        logger.error(f"Failed to get updates: {updates_response}")
                        time.sleep(5)
                        continue
                
                updates = updates_response.get("result", [])
                
                for update in updates:
                    self.last_update_id = update["update_id"]
                    self.process_update(update)
                
                if not updates:
                    # No new updates, continue polling
                    continue
                    
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)

def main():
    """Main function to start the bot"""
    try:
        bot = TelegramBot()
        bot.start_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == "__main__":
    main()