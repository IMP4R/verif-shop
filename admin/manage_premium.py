from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import os
import sqlite3
from dirrrr import PROJECT_ROOT

from base.methods import get_user_language
from payments.methods import SubscriptionMethodsDB
from bot_instance import BotInstance

router = Router()
subscription_db = SubscriptionMethodsDB()

from aiogram.fsm.state import State, StatesGroup

class PlanStates(StatesGroup):
    waiting_for_days = State()
    waiting_for_price = State()
    waiting_for_discount = State()
    waiting_for_confirm_delete = State()

ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class ManualPremiumStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_days = State()
    waiting_for_discount = State()
    waiting_for_price = State()
    waiting_for_confirmation = State()


@router.callback_query(F.data == "admin_manage_premium")
async def handle_manage_premium(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    total_active = subscription_db.get_active_subscriptions_count()
    total_subscriptions = subscription_db.get_total_subscriptions_count()
    
    text = "⭐ <b>Управление Premium подписками</b>\n\n"
    text += f"📊 Статистика:\n"
    text += f"• Активных подписок: {total_active}\n"
    text += f"• Всего подписок: {total_subscriptions}\n\n"
    text += "Выберите действие:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить подписку", callback_data="admin_add_premium")],
        [InlineKeyboardButton(text="📋 Список подписок", callback_data="admin_list_premium")],
        [InlineKeyboardButton(text="🔧 Управление планами", callback_data="admin_manage_plans")],  # ← новая кнопка
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_add_premium")
async def handle_add_premium_start(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.set_state(ManualPremiumStates.waiting_for_user_id)
    
    text = "➕ <b>Добавление Premium подписки</b>\n\n"
    text += "Введите Telegram ID пользователя:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_premium")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(ManualPremiumStates.waiting_for_user_id)
async def handle_user_id_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    try:
        target_user_id = int(message.text.strip())
        await state.update_data(target_user_id=target_user_id)
        await state.set_state(ManualPremiumStates.waiting_for_days)
        
        text = "📅 Введите количество дней подписки:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="1 день", callback_data="days_1")],
            [InlineKeyboardButton(text="7 дней", callback_data="days_7")],
            [InlineKeyboardButton(text="30 дней", callback_data="days_30")],
            [InlineKeyboardButton(text="90 дней", callback_data="days_90")],
            [InlineKeyboardButton(text="365 дней", callback_data="days_365")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_premium")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except ValueError:
        await message.answer("❌ Неверный ID пользователя. Введите числовой ID:")


@router.callback_query(F.data.startswith("days_"))
async def handle_days_selection(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    days = int(callback.data.split("_")[1])
    await state.update_data(days=days)
    await state.set_state(ManualPremiumStates.waiting_for_discount)
    
    text = f"🎯 Введите размер скидки (в %):\n\n"
    text += f"• Стандартная скидка: 20%\n"
    text += f"• Можно указать от 5% до 50%"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="20% (стандарт)", callback_data="discount_20")],
        [InlineKeyboardButton(text="10%", callback_data="discount_10")],
        [InlineKeyboardButton(text="30%", callback_data="discount_30")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_premium")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("discount_"))
async def handle_discount_selection(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    discount = float(callback.data.split("_")[1])
    await state.update_data(discount=discount)
    await state.set_state(ManualPremiumStates.waiting_for_price)
    
    text = f"💰 Введите цену подписки (в $):\n\n"
    text += f"• Для {discount}% скидки обычно ${discount * 0.5:.2f}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Автоцена", callback_data="auto_price")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_premium")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.message(ManualPremiumStates.waiting_for_price)
async def handle_price_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError
        
        await state.update_data(price=price)
        await state.set_state(ManualPremiumStates.waiting_for_confirmation)
        
        data = await state.get_data()
        target_user_id = data['target_user_id']
        days = data['days']
        discount = data['discount']
        
        text = f"✅ <b>Подтвердите добавление Premium подписки</b>\n\n"
        text += f"👤 Пользователь ID: {target_user_id}\n"
        text += f"📅 Срок: {days} дней\n"
        text += f"🎯 Скидка: {discount}%\n"
        text += f"💰 Цена: ${price:.2f}\n\n"
        text += f"📅 Дата окончания: {(datetime.now() + timedelta(days=days)).strftime('%d.%m.%Y')}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_premium")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_premium")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Неверная цена. Введите число (например: 10.99):")


@router.callback_query(F.data == "auto_price")
async def handle_auto_price(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    data = await state.get_data()
    discount = data.get('discount', 20)
    
    auto_price = discount * 0.5
    
    await state.update_data(price=auto_price)
    await state.set_state(ManualPremiumStates.waiting_for_confirmation)
    
    target_user_id = data['target_user_id']
    days = data['days']
    
    text = f"✅ <b>Подтвердите добавление Premium подписки</b>\n\n"
    text += f"👤 Пользователь ID: {target_user_id}\n"
    text += f"📅 Срок: {days} дней\n"
    text += f"🎯 Скидка: {discount}%\n"
    text += f"💰 Цена: ${auto_price:.2f} (авто)\n\n"
    text += f"📅 Дата окончания: {(datetime.now() + timedelta(days=days)).strftime('%d.%m.%Y')}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_premium")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_manage_premium")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "confirm_premium")
async def handle_confirm_premium(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    data = await state.get_data()
    target_user_id = data['target_user_id']
    days = data['days']
    discount = data['discount']
    price = data['price']
    
    subscription = subscription_db.create_manual_subscription(target_user_id, days, discount, price)
    
    if subscription:
        try:
            bot = BotInstance.get_bot()
            user_message = f"⭐ <b>Вам активирована Premium подписка!</b>\n\n"
            user_message += f"🎯 Ваша скидка: {discount}%\n"
            user_message += f"📅 Подписка действует до: {subscription.end_date}\n\n"
            user_message += f"Спасибо за покупку! Теперь вы получаете скидку на все товары."
            
            await bot.send_message(target_user_id, user_message, parse_mode="HTML")
            
            import os
            from datetime import datetime
            
            admin_id = int(os.getenv('ADMIN_ID', '0'))
            group_chat_id = os.getenv('NOTIFICATION_CHAT_ID')
            
            admin_message = f"⭐ <b>Premium подписка активирована вручную</b>\n\n"
            admin_message += f"👤 Пользователь: <a href='tg://user?id={target_user_id}'>{target_user_id}</a>\n"
            admin_message += f"📅 Срок: {days} дней\n"
            admin_message += f"🎯 Скидка: {discount}%\n"
            admin_message += f"💰 Цена: ${price:.2f}\n"
            admin_message += f"📅 Окончание: {subscription.end_date}\n\n"
            admin_message += f"👑 Активировал: {user_id}\n"
            admin_message += f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            
            if admin_id:
                await bot.send_message(admin_id, admin_message, parse_mode="HTML")
            
            if group_chat_id:
                await bot.send_message(group_chat_id, admin_message, parse_mode="HTML")
                
        except Exception as e:
            print(f"Не удалось уведомить пользователя: {e}")
        
        await callback.message.edit_text(
            f"✅ Premium подписка успешно активирована для пользователя {target_user_id}\n\n"
            f"📅 Срок: {days} дней\n"
            f"🎯 Скидка: {discount}%\n"
            f"💰 Цена: ${price:.2f}\n"
            f"📅 Окончание: {subscription.end_date}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_premium")]
            ])
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при создании подписки",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_premium")]
            ])
        )
    
    await state.clear()


@router.callback_query(F.data == "admin_list_premium")
async def handle_list_premium(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, plan_days, discount, end_date, is_active 
            FROM subscriptions 
            ORDER BY end_date DESC 
            LIMIT 20
        ''')
        subscriptions = cursor.fetchall()
    
    text = "📋 <b>Список Premium подписок</b>\n\n"
    
    if not subscriptions:
        text += "Нет активных подписок"
    else:
        for sub in subscriptions:
            user_id, plan_days, discount, end_date, is_active = sub
            status = "✅ Активна" if is_active and datetime.now() < datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S") else "❌ Истекла"
            text += f"👤 {user_id} - {plan_days}д - {discount}% - до {end_date}\n"
            text += f"   {status}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_premium")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_manage_plans")
async def handle_manage_plans(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    plans = subscription_db.get_subscription_plans()
    
    text = "🔧 <b>Управление планами Premium</b>\n\n"
    if not plans:
        text += "Планов пока нет"
    else:
        text += "Текущие планы:\n\n"
        for plan in plans:
            text += f"• {plan['days']} дней — ${plan['price']} (скидка {plan['discount']}%)\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить новый план", callback_data="add_plan")],
        [InlineKeyboardButton(text="🗑 Удалить план", callback_data="delete_plan")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_manage_premium")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "add_plan")
async def start_add_plan(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PlanStates.waiting_for_days)
    await callback.message.edit_text(
        "Введите количество дней для нового плана:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="admin_manage_plans")]
        ])
    )

@router.message(PlanStates.waiting_for_days)
async def process_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
        await state.update_data(days=days)
        await state.set_state(PlanStates.waiting_for_price)
        await message.answer("Введите цену в $:")
    except:
        await message.answer("Введите положительное число (дни):")

@router.message(PlanStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
        if price <= 0:
            raise ValueError
        await state.update_data(price=price)
        await state.set_state(PlanStates.waiting_for_discount)
        await message.answer("Введите скидку в % (например 20):")
    except:
        await message.answer("Введите положительное число (цена):")

@router.message(PlanStates.waiting_for_discount)
async def process_discount(message: Message, state: FSMContext):
    try:
        discount = float(message.text.strip())
        if discount < 0 or discount > 100:
            raise ValueError
        
        data = await state.get_data()
        days = data['days']
        price = data['price']
        
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO subscription_plans (days, price, discount, is_active)
                VALUES (?, ?, ?, 1)
            ''', (days, price, discount))
            conn.commit()
        
        await state.clear()
        await message.answer(
            f"✅ Новый план добавлен:\n{days} дней — ${price} (скидка {discount}%)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К планам", callback_data="admin_manage_plans")]
            ])
        )
    except:
        await message.answer("Введите число от 0 до 100:")

@router.callback_query(F.data == "delete_plan")
async def start_delete_plan(callback: CallbackQuery):
    plans = subscription_db.get_subscription_plans()
    
    if not plans:
        await callback.answer("Нет планов для удаления", show_alert=True)
        return
    
    text = "Выберите план для удаления:"
    buttons = []
    for plan in plans:
        buttons.append([InlineKeyboardButton(
            text=f"{plan['days']} дней — ${plan['price']}",
            callback_data=f"confirm_delete_plan_{plan['days']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="admin_manage_plans")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("confirm_delete_plan_"))
async def confirm_delete_plan(callback: CallbackQuery):
    days = int(callback.data.split("_")[3])
    
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscription_plans WHERE days = ?", (days,))
        conn.commit()
    
    await callback.message.edit_text(
        f"✅ План на {days} дней удалён",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ К планам", callback_data="admin_manage_plans")]
        ])
    )