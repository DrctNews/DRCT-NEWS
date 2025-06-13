import json
import logging
from typing import Dict, List, Set
from config import GROUPS_FILE

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

from datetime import datetime
