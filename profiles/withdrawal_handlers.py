from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from base.methods import get_user_language
from .methods import ReferralMethodsDB
from .withdrawals import WithdrawalMethodsDB
from .texts import get_profile_text

router = Router()
referral_db = ReferralMethodsDB()
withdrawal_db = WithdrawalMethodsDB()

class WithdrawalStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_details = State()
    waiting_for_confirmation = State()

@router.callback_query(F.data.startswith("withdraw_"))
async def handle_withdraw_amount(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    available_balance = referral_db.get_available_balance(user_id)
    
    if callback.data == "withdraw_custom":
        await state.set_state(WithdrawalStates.waiting_for_amount)
        
        text = get_profile_text('withdraw_custom_amount', language, available=available_balance)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="withdraw_funds")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    amount_map = {
        "withdraw_10": 10.0,
        "withdraw_20": 20.0
    }
    
    if callback.data in amount_map:
        amount = amount_map[callback.data]
        
        if amount > available_balance:
            await callback.answer(f"❌ Недостаточно средств. Доступно: ${available_balance}", show_alert=True)
            return
        
        await state.update_data(amount=amount)
        await state.set_state(WithdrawalStates.waiting_for_details)
        
        text = get_profile_text('withdraw_enter_details', language, amount=amount)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="withdraw_funds")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(WithdrawalStates.waiting_for_amount)
async def handle_custom_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    available_balance = referral_db.get_available_balance(user_id)
    
    try:
        amount = float(message.text.strip())
        
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        if amount > available_balance:
            await message.answer(f"❌ Недостаточно средств. Доступно: ${available_balance:.2f}")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(WithdrawalStates.waiting_for_details)
        
        text = get_profile_text('withdraw_enter_details', language, amount=amount)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="withdraw_funds")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Неверная сумма. Введите число (например: 15.50)")

@router.message(WithdrawalStates.waiting_for_details)
async def handle_withdraw_details(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    details = message.text.strip()
    
    if len(details) < 5:
        await message.answer("❌ Пожалуйста, укажите более подробные реквизиты для выплаты:")
        return
    
    await state.update_data(details=details)
    await state.set_state(WithdrawalStates.waiting_for_confirmation)
    
    data = await state.get_data()
    amount = data['amount']
    
    text = get_profile_text('withdraw_confirmation', language, amount=amount, details=details)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_withdrawal"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="withdraw_funds")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "confirm_withdrawal")
async def handle_confirm_withdrawal(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    data = await state.get_data()
    amount = data['amount']
    details = data['details']
    
    withdrawal_db.create_withdrawal_request(user_id, amount, details)
    
    from bot_instance import BotInstance
    import os
    from datetime import datetime
    
    admin_id = int(os.getenv('ADMIN_ID', '0'))
    group_chat_id = os.getenv('NOTIFICATION_CHAT_ID')
    
    admin_message = f"📋 <b>Новая заявка на вывод!</b>\n\n"
    admin_message += f"👤 Пользователь: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
    admin_message += f"💰 Сумма: ${amount}\n"
    admin_message += f"📝 Реквизиты: {details}\n\n"
    admin_message += f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    
    if admin_id:
        bot = BotInstance.get_bot()
        try:
            await bot.send_message(admin_id, admin_message, parse_mode="HTML")
        except:
            pass
    
    if group_chat_id:
        try:
            await bot.send_message(group_chat_id, admin_message, parse_mode="HTML")
        except:
            pass
    
    await state.clear()
    
    text = get_profile_text('withdraw_success', language, amount=amount)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_withdrawals")],
        [InlineKeyboardButton(text="⬅️ В профиль", callback_data="profile")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
@router.callback_query(F.data == "my_withdrawals")
async def handle_my_withdrawals(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    withdrawals = withdrawal_db.get_user_withdrawals(user_id)
    
    text = "📋 <b>Мои заявки на вывод</b>\n\n"
    
    if not withdrawals:
        text += "У вас нет заявок на вывод"
    else:
        for wd in withdrawals:
            status_text = {
                'pending': '⏳ Ожидает',
                'approved': '✅ Одобрена',
                'rejected': '❌ Отклонена'
            }.get(wd['status'], wd['status'])
            
            text += f"💰 ${wd['amount']} - {status_text}\n"
            text += f"📅 {wd['created_at']}\n"
            if wd['admin_notes']:
                text += f"📝 {wd['admin_notes']}\n"
            text += "\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В профиль", callback_data="profile")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")