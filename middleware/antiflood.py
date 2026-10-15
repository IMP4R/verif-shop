from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
import time
import asyncio

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit_period: float = 0.5, block_duration: float = 10.0):
        self.limit_period = limit_period
        self.block_duration = block_duration
        self.users = {}
    
    async def __call__(
        self,
        handler: Callable,
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        current_time = time.time()
        
        if user_id in self.users:
            user_data = self.users[user_id]
            
            if 'blocked_until' in user_data and current_time < user_data['blocked_until']:
                if isinstance(event, Message) and not user_data.get('warning_sent', False):
                    try:
                        await event.answer(
                            f"⏳ Слишком много действий! Подождите {int(user_data['blocked_until'] - current_time)} секунд...",
                            show_alert=False
                        )
                        self.users[user_id]['warning_sent'] = True
                    except:
                        pass
                return
            
            if 'blocked_until' in user_data and current_time >= user_data['blocked_until']:
                self.users[user_id] = {'last_time': current_time}
                user_data = self.users[user_id]
        
        if user_id in self.users:
            user_data = self.users[user_id]
            last_time = user_data.get('last_time', 0)
            
            if current_time - last_time < self.limit_period:
                self.users[user_id] = {
                    'last_time': current_time,
                    'blocked_until': current_time + self.block_duration,
                    'warning_sent': False
                }
                
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            f"⚠️ Слишком быстрые действия! Бот будет игнорировать вас {int(self.block_duration)} секунд.",
                            show_alert=False
                        )
                    except:
                        pass
                
                return
        
        self.users[user_id] = {'last_time': current_time}
        
        self._cleanup_old_entries()
        
        return await handler(event, data)
    
    def _cleanup_old_entries(self):
        current_time = time.time()
        cleanup_time = 300 
        
        keys_to_remove = []
        for user_id, user_data in self.users.items():
            last_time = user_data.get('last_time', 0)
            if current_time - last_time > cleanup_time:
                keys_to_remove.append(user_id)
        
        for key in keys_to_remove:
            del self.users[key]
    
    async def reset_user_flood(self, user_id: int):
        if user_id in self.users:
            del self.users[user_id]