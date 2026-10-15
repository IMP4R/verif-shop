import os
from typing import Dict
from dotenv import load_dotenv
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatMemberStatus

from .texts import get_text
from config.languages import SUPPORTED_LANGUAGES
from bot_instance import BotInstance
from project.main_menu import show_main_menu
from base.states import UserStates
from dirrrr import PROJECT_ROOT
load_dotenv()

DB_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db")

import sqlite3
from typing import Optional

class BaseMethodsDB:
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_languages (
                    user_id INTEGER PRIMARY KEY,
                    language TEXT DEFAULT 'ru',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def get_language(self, user_id: int) -> Optional[str]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT language FROM user_languages WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def set_language(self, user_id: int, language: str):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_languages (user_id, language, created_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, language))
            conn.commit()
    
    def user_exists(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM user_languages WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None

methods_db = BaseMethodsDB()

class UserStates(StatesGroup):
    language_selection = State()
    subscription_check = State()
    main_menu = State()

router = Router()
REQUIRED_CHANNEL = os.getenv('REQUIRED_CHANNEL', '')
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

#…yazyki
def update_user_language(user_id: int, language: str):
    methods_db.set_language(user_id, language)

def get_user_language(user_id: int, default: str = 'ru') -> str:
    lang = methods_db.get_language(user_id)
    return lang if lang else default

async def show_language_selection(message: Message, state: FSMContext):
    await state.set_state(UserStates.language_selection)
    
    text = get_text('language_selection', 'ru')
    
    buttons = []
    for lang_code, lang_data in SUPPORTED_LANGUAGES.items():
        buttons.append(InlineKeyboardButton(text=lang_data['emoji'] + " " + lang_data['native'], callback_data=f"lang_{lang_code}"))
    
    keyboard_rows = []
    for i in range(0, len(buttons), 2):
        keyboard_rows.append(buttons[i:i+2])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await message.answer(text, reply_markup=keyboard)

async def handle_language_selection(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = callback.data.split("_")[1]
    
    update_user_language(user_id, language)
    
    is_subscribed = await check_channel_subscription(user_id)
    
    if not is_subscribed:
        await show_subscription_request(callback, language, state)
    else:
        await show_main_menu(callback, language, state)
    
    await callback.answer()


#…podpiska
async def check_channel_subscription(user_id: int) -> bool:
    try:
        bot = BotInstance.get_bot()
        chat_member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except:
        return False

async def show_subscription_request(update, language: str, state: FSMContext):
    await state.set_state(UserStates.subscription_check)
    
    text = get_text('subscription_request', language).format(channel=REQUIRED_CHANNEL)
    
    button_text = get_text('check_subscription_button', language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=button_text, callback_data="check_subscription")]])
    
    if isinstance(update, Message):
        await update.answer(text, reply_markup=keyboard)
    else:
        await update.message.edit_text(text, reply_markup=keyboard)

async def handle_check_subscription(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    is_subscribed = await check_channel_subscription(user_id)
    
    if is_subscribed:
        await show_main_menu(callback, language, state)
    else:
        alert_text = get_text('not_subscribed_alert', language)
        await callback.answer(alert_text, show_alert=True)
    
    await callback.answer()

#bot
async def get_bot_username():
    bot_info = await BotInstance._bot.get_me()
    bot_un = bot_info.username
    return bot_un

#routers
router.callback_query.register(handle_language_selection, lambda c: c.data.startswith("lang_"))
router.callback_query.register(handle_check_subscription, lambda c: c.data == "check_subscription")