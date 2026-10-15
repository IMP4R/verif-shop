from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

class BotInstance:
    _bot = None
    _dp = None
    
    @classmethod
    def init(cls, token: str):
        cls._bot = Bot(token=token)
        cls._dp = Dispatcher(storage=MemoryStorage())
    
    @classmethod
    def get_bot(cls):
        return cls._bot
    
    @classmethod
    def get_dp(cls):
        return cls._dp