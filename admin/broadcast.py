from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import sqlite3

from base.methods import get_user_language
from bot_instance import BotInstance
from dirrrr import PROJECT_ROOT
import os

router = Router()

ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_recipients = State()

@router.callback_query(F.data == "admin_broadcast")
async def handle_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    text = "📢 <b>Рассылка сообщений</b>\n\n"
    text += "Выберите тип рассылки:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всем пользователям", callback_data="broadcast_all")],
        [InlineKeyboardButton(text="⭐ Только Premium", callback_data="broadcast_premium")],
        [InlineKeyboardButton(text="👤 Только обычные", callback_data="broadcast_regular")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("broadcast_"))
async def handle_broadcast_type(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        return
    
    broadcast_type = callback.data.replace("broadcast_", "")
    await state.update_data(broadcast_type=broadcast_type)
    await state.set_state(BroadcastStates.waiting_for_message)
    
    types_text = {
        'all': 'всем пользователям',
        'premium': 'только Premium пользователям',
        'regular': 'только обычным пользователям'
    }
    
    text = f"📢 Рассылка: {types_text.get(broadcast_type)}\n\n"
    text += "Введите сообщение для рассылки:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(BroadcastStates.waiting_for_message)
async def handle_broadcast_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    await state.update_data(broadcast_message=message.text)
    
    data = await state.get_data()
    broadcast_type = data['broadcast_type']
    
    text = "📢 <b>Предпросмотр сообщения:</b>\n\n"
    text += message.text + "\n\n"
    text += f"Тип рассылки: {broadcast_type}\n\n"
    text += "Отправить рассылку?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "confirm_broadcast")
async def handle_confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        return
    
    data = await state.get_data()
    broadcast_type = data['broadcast_type']
    broadcast_message = data['broadcast_message']
    
    await callback.message.edit_text("⏳ Начинаю рассылку...")
    
    success_count = 0
    fail_count = 0
    
    user_ids = await get_user_ids_for_broadcast(broadcast_type)
    
    bot = BotInstance.get_bot()
    
    for target_user_id in user_ids:
        try:
            await bot.send_message(target_user_id, broadcast_message, parse_mode="HTML")
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            fail_count += 1
        
        if success_count % 10 == 0:
            await callback.message.edit_text(f"⏳ Отправлено: {success_count}, Ошибок: {fail_count}")
    
    await state.clear()
    
    text = f"✅ Рассылка завершена!\n\n"
    text += f"📤 Успешно отправлено: {success_count}\n"
    text += f"❌ Не отправлено: {fail_count}\n"
    text += f"📊 Всего получателей: {len(user_ids)}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В админ панель", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def get_user_ids_for_broadcast(broadcast_type: str):
    user_ids = []
    
    try:
        if broadcast_type == 'all':
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM user_languages")
                rows = cursor.fetchall()
                user_ids = [row[0] for row in rows]
                
        elif broadcast_type == 'premium':
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT user_id FROM subscriptions 
                    WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP
                ''')
                rows = cursor.fetchall()
                user_ids = [row[0] for row in rows]
                
        elif broadcast_type == 'regular':
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM user_languages")
                all_users = [row[0] for row in cursor.fetchall()]
            
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT user_id FROM subscriptions 
                    WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP
                ''')
                premium_users = [row[0] for row in cursor.fetchall()]
                
                premium_set = set(premium_users)
                user_ids = [uid for uid in all_users if uid not in premium_set]
                
    except Exception as e:
        print(f"Error getting user IDs for broadcast: {e}")
    
    return user_ids