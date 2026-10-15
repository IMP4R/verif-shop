from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
from dirrrr import PROJECT_ROOT
from base.methods import get_user_language
from admin.methods import AdminMethodsDB
from admin.texts import get_admin_text
from shop.methods import ProductMethodsDB
from project.main_menu import show_main_menu

router = Router()
admin_db = AdminMethodsDB()
product_db = ProductMethodsDB()

ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))


class AdminStates(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_description = State()
    waiting_for_product_price = State()
    waiting_for_product_category = State()
    waiting_for_new_category = State()
    waiting_for_delivery_instruction = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(F.text == "/admin")
async def handle_admin_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Доступ запрещен")
        return
    
    language = get_user_language(user_id)
    await show_admin_panel(message, language, state)

async def show_admin_panel(update, language: str, state: FSMContext):
    total_users = admin_db.get_total_users()
    total_products = admin_db.get_total_products()
    active_products = admin_db.get_active_products()
    
    text = get_admin_text('admin_panel', language) + "\n\n"
    text += get_admin_text('admin_stats', language, 
                          users=total_users, 
                          products=total_products, 
                          active=active_products)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_admin_text('manage_products', language), callback_data="admin_products")],
        [InlineKeyboardButton(text=get_admin_text('add_product', language), callback_data="admin_add_product")],
        [InlineKeyboardButton(text=get_admin_text('manage_premium', language), callback_data="admin_manage_premium")],
        [InlineKeyboardButton(text=get_admin_text('view_orders', language), callback_data="admin_orders")],
        [InlineKeyboardButton(text=get_admin_text('delivery_settings', language), callback_data="admin_delivery_settings")],
        [InlineKeyboardButton(text="📝 Правила и инструкции", callback_data="admin_rules_instructions")],
        [InlineKeyboardButton(text=get_admin_text('broadcast', language), callback_data="admin_broadcast")],
        [InlineKeyboardButton(text=get_admin_text('statistics', language), callback_data="admin_statistics")],
        [InlineKeyboardButton(text=get_admin_text('reports', language), callback_data="admin_generate_report")],
        [InlineKeyboardButton(text=get_admin_text('text_editor', language), callback_data="admin_edit_texts")], 
        [InlineKeyboardButton(text=get_admin_text('back_to_main', language), callback_data="admin_back_to_main")]
    ])
    
    if isinstance(update, Message):
        await update.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await update.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")



@router.callback_query(F.data == "admin_products")
async def handle_admin_products(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    products = admin_db.get_all_products_admin()
    
    if not products:
        text = get_admin_text('product_list', language) + "\n\nНет товаров"
    else:
        text = get_admin_text('product_list', language) + "\n\n"
        for product in products:
            status = get_admin_text('product_active', language) if product.is_active else get_admin_text('product_inactive', language)
            text += get_admin_text('product_item', language, 
                                  id=product.id, 
                                  name=product.name, 
                                  price=product.price,
                                  status=status) + "\n"
    
    buttons = []
    for product in products:
        status_text = "❌" if product.is_active else "✅"
        action = "deactivate" if product.is_active else "activate"
        buttons.append([
            InlineKeyboardButton(text=f"{product.id}. {product.name}", callback_data=f"admin_view_product_{product.id}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"admin_delete_{product.id}"),
            InlineKeyboardButton(text="✏️ Инстр.", callback_data=f"edit_delivery_text_{product.id}")   # ← новая кнопка
        ])
    
    buttons.append([
        InlineKeyboardButton(text=get_admin_text('back_to_main', language), callback_data="admin_back"),
        InlineKeyboardButton(text=get_admin_text('add_product', language), callback_data="admin_add_product")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_delete_"))
async def handle_admin_delete(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    product_id = int(callback.data.replace("admin_delete_", ""))
    
    from payments.methods import PaymentMethodsDB
    payment_db = PaymentMethodsDB()
    
    try:
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM orders WHERE product_id = ? AND status = "paid"', (product_id,))
            active_orders = cursor.fetchone()[0]
            
            if active_orders > 0:
                await callback.answer(
                    f"❌ Нельзя удалить товар! Есть {active_orders} оплаченных заказов. "
                    "Сначала выполните все заказы или скройте товар.",
                    show_alert=True
                )
                return
    except:
        pass
    
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        result = cursor.fetchone()
        
        if not result:
            await callback.answer("❌ Товар не найден")
            return
        
        product_name = result[0]
    
    if admin_db.delete_product_permanently(product_id):
        await callback.answer(f"✅ Товар '{product_name}' удален")
        await handle_admin_products(callback, state)
    else:
        await callback.answer("❌ Ошибка при удалении товара")

@router.callback_query(F.data.startswith("admin_toggle_"))
async def handle_admin_toggle(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    product_id = int(callback.data.replace("admin_toggle_", ""))
    
    if admin_db.toggle_product_active(product_id):
        await callback.answer(get_admin_text('product_toggled', language))
        await handle_admin_products(callback, state)
    else:
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "admin_add_product")
async def handle_admin_add_product(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    await state.set_state(AdminStates.waiting_for_product_name)
    await callback.message.edit_text(
        get_admin_text('enter_product_name', language),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_admin_text('back_to_main', language), callback_data="admin_products")]
        ])
    )

@router.message(AdminStates.waiting_for_product_name)
async def handle_product_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.update_data(product_name=message.text)
    await state.set_state(AdminStates.waiting_for_product_description)
    
    await message.answer(
        get_admin_text('enter_product_description', language),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_admin_text('back_to_main', language), callback_data="admin_cancel")]
        ])
    )

@router.message(AdminStates.waiting_for_product_description)
async def handle_product_description(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.update_data(product_description=message.text)
    await state.set_state(AdminStates.waiting_for_product_price)
    
    await message.answer(
        get_admin_text('enter_product_price', language),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_admin_text('back_to_main', language), callback_data="admin_cancel")]
        ])
    )

@router.message(AdminStates.waiting_for_product_price)
async def handle_product_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(get_admin_text('invalid_price', language))
        return
    
    await state.update_data(product_price=price)
    await state.set_state(AdminStates.waiting_for_product_category)
    
    categories = admin_db.get_product_categories()
    
    buttons = []
    for category in categories:
        buttons.append([InlineKeyboardButton(
            text=category,
            callback_data=f"admin_category_{category}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="➕ Новая категория",
        callback_data="admin_new_category"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        get_admin_text('enter_product_category', language),
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("admin_category_"))
async def handle_product_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    category = callback.data.replace("admin_category_", "")
    
    data = await state.get_data()
    product_name = data.get('product_name')
    product_description = data.get('product_description')
    product_price = data.get('product_price')
    
    product_id = product_db.add_product(
        name=product_name,
        description=product_description,
        price=product_price,
        category=category
    )
    
    await state.clear()
    
    await callback.message.edit_text(
        get_admin_text('product_added', language) + f"\nID: {product_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_admin_text('back_to_main', language), callback_data="admin_products")]
        ])
    )

@router.callback_query(F.data == "admin_new_category")
async def handle_new_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.set_state(AdminStates.waiting_for_new_category)
    
    await callback.message.edit_text(
        "Введите название новой категории:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_cancel_category")]
        ])
    )

@router.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await show_admin_panel(callback, language, state)

@router.callback_query(F.data == "admin_back_to_main")
async def handle_admin_back_to_main(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    await show_main_menu(callback, language, state)

@router.callback_query(F.data == "admin_cancel")
async def handle_admin_cancel(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.clear()
    await show_admin_panel(callback, language, state)

@router.message(AdminStates.waiting_for_new_category)
async def handle_new_category_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    new_category = message.text.strip()
    
    if not new_category:
        await message.answer("❌ Название категории не может быть пустым")
        return
    
    data = await state.get_data()
    product_name = data.get('product_name')
    product_description = data.get('product_description')
    product_price = data.get('product_price')
    
    if not all([product_name, product_description, product_price]):
        await message.answer("❌ Ошибка: данные товара потеряны")
        await state.clear()
        return
    
    product_id = product_db.add_product(
        name=product_name,
        description=product_description,
        price=product_price,
        category=new_category
    )
    
    await state.clear()
    
    await message.answer(
        f"✅ Товар добавлен в новую категорию '{new_category}'\nID: {product_id}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ В админ панель", callback_data="admin_products")]
        ])
    )

@router.callback_query(F.data == "admin_cancel_category")
async def handle_cancel_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.clear()
    await show_admin_panel(callback, language, state)


@router.callback_query(F.data == "admin_orders")
async def handle_admin_orders(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    from profiles.withdrawals import WithdrawalMethodsDB
    withdrawal_db = WithdrawalMethodsDB()
    
    pending_withdrawals = withdrawal_db.get_withdrawal_requests('pending')
    
    text = "📋 <b>Заявки на вывод</b>\n\n"
    
    if not pending_withdrawals:
        text += "Нет заявок на вывод"
    else:
        for wd in pending_withdrawals:
            text += f"#{wd['id']} - {wd['user_id']} - ${wd['amount']}\n"
            text += f"Детали: {wd['details']}\n"
            text += f"Дата: {wd['created_at']}\n\n"
    
    buttons = []
    for wd in pending_withdrawals:
        buttons.append([
            InlineKeyboardButton(
                text=f"✅ #{wd['id']} ({wd['user_id']})",
                callback_data=f"admin_approve_withdraw_{wd['id']}"
            ),
            InlineKeyboardButton(
                text=f"❌ Отклонить",
                callback_data=f"admin_reject_withdraw_{wd['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

import sqlite3
@router.callback_query(F.data.startswith("admin_approve_withdraw_"))
async def handle_approve_withdraw(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    withdrawal_id = int(callback.data.split("_")[3])
    
    from profiles.withdrawals import WithdrawalMethodsDB
    withdrawal_db = WithdrawalMethodsDB()
    
    withdrawal_db.update_withdrawal_status(withdrawal_id, 'approved', 'Заявка одобрена')
    
    from bot_instance import BotInstance
    bot = BotInstance.get_bot()
    
    try:
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount FROM referral_withdrawals WHERE id = ?', (withdrawal_id,))
            result = cursor.fetchone()
            
            if result:
                target_user_id, amount = result
                await bot.send_message(target_user_id, f"✅ Ваша заявка на вывод ${amount} одобрена!")
    except:
        pass
    
    await callback.answer("✅ Заявка одобрена")
    await handle_admin_orders(callback, None)

@router.callback_query(F.data.startswith("admin_reject_withdraw_"))
async def handle_reject_withdraw(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    withdrawal_id = int(callback.data.split("_")[3])
    
    from profiles.withdrawals import WithdrawalMethodsDB
    withdrawal_db = WithdrawalMethodsDB()
    
    withdrawal_db.update_withdrawal_status(withdrawal_id, 'rejected', 'Заявка отклонена')
    
    from bot_instance import BotInstance
    bot = BotInstance.get_bot()
    
    try:
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount FROM referral_withdrawals WHERE id = ?', (withdrawal_id,))
            result = cursor.fetchone()
            
            if result:
                target_user_id, amount = result
                await bot.send_message(target_user_id, f"❌ Ваша заявка на вывод ${amount} отклонена.")
    except:
        pass
    
    await callback.answer("❌ Заявка отклонена")
    await handle_admin_orders(callback, None)

from aiogram.fsm.state import State, StatesGroup
from admin.methods import DeliveryMethodsDB

class DeliverySettingsStates(StatesGroup):
    waiting_for_bot_username = State()
    waiting_for_delivery_link = State()

delivery_db = DeliveryMethodsDB()

@router.callback_query(F.data == "admin_delivery_settings")
async def handle_delivery_settings(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    settings = delivery_db.get_delivery_settings()
    
    text = get_admin_text('delivery_settings', language) + "\n\n"
    text += get_admin_text('current_delivery_bot', language, bot_username=settings['bot_username'] or "Не указан") + "\n"
    text += get_admin_text('current_delivery_link', language, link=settings['delivery_link'] or "Не указана")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_admin_text('edit_delivery_bot', language), callback_data="edit_delivery_bot")],
        [InlineKeyboardButton(text=get_admin_text('delivery_bot_link', language), callback_data="edit_delivery_link")],
        [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "edit_delivery_bot")
async def handle_edit_delivery_bot(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.set_state(DeliverySettingsStates.waiting_for_bot_username)
    
    text = get_admin_text('enter_delivery_bot', language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_delivery_settings")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.message(DeliverySettingsStates.waiting_for_bot_username)
async def handle_delivery_bot_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    bot_username = message.text.strip()
    
    if not bot_username.startswith('@'):
        await message.answer("❌ Username должен начинаться с @. Попробуйте еще раз:")
        return
    
    if delivery_db.update_delivery_bot(bot_username):
        await state.clear()
        
        settings = delivery_db.get_delivery_settings()
        
        text = get_admin_text('delivery_bot_saved', language) + "\n\n"
        text += get_admin_text('current_delivery_bot', language, bot_username=settings['bot_username'])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_delivery_settings")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("❌ Ошибка при сохранении настроек")

@router.callback_query(F.data == "edit_delivery_link")
async def handle_edit_delivery_link(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.set_state(DeliverySettingsStates.waiting_for_delivery_link)
    
    text = get_admin_text('enter_delivery_link', language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_delivery_settings")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.message(DeliverySettingsStates.waiting_for_delivery_link)
async def handle_delivery_link_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    delivery_link = message.text.strip()
    
    if not (delivery_link.startswith('http://') or delivery_link.startswith('https://') or 
            delivery_link.startswith('tg://') or delivery_link.startswith("t.me/")):
        await message.answer("❌ Некорректная ссылка. Используйте http://, https://, tg:// или t.me/")
        return
    
    if delivery_db.update_delivery_link(delivery_link):
        await state.clear()
        
        settings = delivery_db.get_delivery_settings()
        
        text = get_admin_text('delivery_link_saved', language) + "\n\n"
        text += get_admin_text('current_delivery_link', language, link=settings['delivery_link'])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_delivery_settings")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("❌ Ошибка при сохранении ссылки")


from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
from admin.methods import StatisticsMethodsDB, TextEditorMethodsDB
import datetime
from datetime import timedelta

stats_db = StatisticsMethodsDB()
text_editor_db = TextEditorMethodsDB()

class ReportStates(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()

class TextEditorStates(StatesGroup):
    waiting_for_text_input = State()


@router.callback_query(F.data == "admin_statistics")
async def handle_statistics(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    stats = stats_db.get_bot_statistics()
    
    text = get_admin_text('statistics_title', language) + "\n\n"
    text += f"📊 <b>Основная статистика:</b>\n"
    text += f"• {get_admin_text('total_users', language)}: {stats.get('total_users', 0)}\n"
    text += f"• {get_admin_text('active_users', language)}: {stats.get('active_users', 0)}\n"
    text += f"• {get_admin_text('total_orders', language)}: {stats.get('total_orders', 0)}\n"
    text += f"• {get_admin_text('total_revenue', language)}: ${stats.get('total_revenue', 0):.2f}\n"
    text += f"• {get_admin_text('active_subscriptions', language)}: {stats.get('active_subscriptions', 0)}\n"
    text += f"• {get_admin_text('available_balance', language)}: ${stats.get('available_balance', 0):.2f}\n\n"
    
    sales = stats.get('sales_by_day', [])
    if sales:
        text += "📈 <b>Продажи за последние 7 дней:</b>\n"
        for sale in sales[:7]:
            text += f"• {sale['date']}: {sale['orders']} заказов (${sale['revenue']:.2f})\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_admin_text('generate_report', language), callback_data="admin_generate_report")],
        [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "admin_generate_report")
async def handle_generate_report(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    text = get_admin_text('select_period', language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_admin_text('today', language), callback_data="report_today")],
        [InlineKeyboardButton(text=get_admin_text('week', language), callback_data="report_week")],
        [InlineKeyboardButton(text=get_admin_text('month', language), callback_data="report_month")],
        [InlineKeyboardButton(text=get_admin_text('year', language), callback_data="report_year")],
        [InlineKeyboardButton(text=get_admin_text('custom', language), callback_data="report_custom")],
        [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_statistics")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("report_"))
async def handle_report_period(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    period = callback.data.replace("report_", "")
    now = datetime.now()
    
    if period == 'today':
        start_date = now.strftime('%Y-%m-%d 00:00:00')
        end_date = now.strftime('%Y-%m-%d 23:59:59')
    elif period == 'week':
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
        end_date = now.strftime('%Y-%m-%d 23:59:59')
    elif period == 'month':
        start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d 00:00:00')
        end_date = now.strftime('%Y-%m-%d 23:59:59')
    elif period == 'year':
        start_date = (now - timedelta(days=365)).strftime('%Y-%m-%d 00:00:00')
        end_date = now.strftime('%Y-%m-%d 23:59:59')
    elif period == 'custom':
        await state.set_state(ReportStates.waiting_for_start_date)
        await callback.message.edit_text(
            "Введите начальную дату (формат: ГГГГ-ММ-ДД):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_generate_report")]
            ])
        )
        return
    
    await generate_and_send_report(callback, start_date, end_date, language)

@router.message(ReportStates.waiting_for_start_date)
async def handle_start_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    try:
        start_date = datetime.strptime(message.text.strip(), '%Y-%m-%d')
        await state.update_data(start_date=start_date.strftime('%Y-%m-%d 00:00:00'))
        await state.set_state(ReportStates.waiting_for_end_date)
        
        await message.answer(
            "Введите конечную дату (формат: ГГГГ-ММ-ДД):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_generate_report")]
            ])
        )
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")

@router.message(ReportStates.waiting_for_end_date)
async def handle_end_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    try:
        end_date = datetime.strptime(message.text.strip(), '%Y-%m-%d')
        data = await state.get_data()
        start_date = data['start_date']
        
        await state.clear()
        await generate_and_send_report(message, start_date, end_date.strftime('%Y-%m-%d 23:59:59'), language)
        
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")

async def generate_and_send_report(update, start_date: str, end_date: str, language: str):
    report_file = stats_db.generate_report(start_date, end_date)
    
    if report_file:
        csv_data = report_file.getvalue()
        
        if csv_data:
            # Создаем файл для отправки
            file = BufferedInputFile(
                csv_data.encode('utf-8'),
                filename=f"report_{start_date[:10]}_{end_date[:10]}.csv"
            )
            
            text = get_admin_text('report_generated', language) + "\n\n"
            text += f"📅 Период: {start_date[:10]} - {end_date[:10]}\n"
            text += f"📄 Файл готов к скачиванию"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_statistics")]
            ])
            
            if isinstance(update, CallbackQuery):
                await update.message.answer_document(
                    document=file,
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await update.answer_document(
                    document=file,
                    caption=text,
                    reply_markup=keyboard
                )
        else:
            text = get_admin_text('no_data', language)
            if isinstance(update, CallbackQuery):
                await update.message.edit_text(text)
            else:
                await update.answer(text)
    else:
        text = get_admin_text('no_data', language)
        if isinstance(update, CallbackQuery):
            await update.message.edit_text(text)
        else:
            await update.answer(text)

@router.callback_query(F.data == "admin_edit_texts")
async def handle_text_editor(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    categories = text_editor_db.get_categories()
    
    text = get_admin_text('text_categories', language) + "\n\n"
    text += get_admin_text('select_text_category', language)
    
    buttons = []
    standard_categories = ['shop', 'payment', 'premium', 'profile', 'settings']
    
    for category in standard_categories:
        button_text = get_admin_text(f'edit_{category}_texts', language)
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"edit_texts_{category}")])
    
    for category in categories:
        if category not in standard_categories:
            buttons.append([InlineKeyboardButton(
                text=f"📝 {category}",
                callback_data=f"edit_texts_{category}"
            )])
    
    buttons.append([InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("edit_texts_"))
async def handle_edit_texts_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    category = callback.data.replace("edit_texts_", "")
    
    texts = text_editor_db.get_texts_by_category(category, language)
    
    if not texts:
        from shop.texts import TEXTS as SHOP_TEXTS
        from payments.texts import TEXTS as PAYMENT_TEXTS
        from profiles.texts import TEXTS as PROFILE_TEXTS
        from settings.texts import TEXTS as SETTINGS_TEXTS
        from base.texts import TEXTS as BASE_TEXTS
        
        text_sources = {
            'shop': SHOP_TEXTS,
            'payment': PAYMENT_TEXTS,
            'premium': PAYMENT_TEXTS,
            'profile': PROFILE_TEXTS,
            'settings': SETTINGS_TEXTS,
            'base': BASE_TEXTS
        }
        
        if category in text_sources:
            source_texts = text_sources[category].get(language, text_sources[category]['ru'])
            texts = [{'key': key, 'value': value} for key, value in source_texts.items()]
        else:
            texts = []
    
    text = get_admin_text(f'edit_{category}_texts', language) + "\n\n"
    text += f"Категория: <b>{category}</b>\nЯзык: <b>{language}</b>\n\n"
    
    buttons = []
    for text_item in texts:
        preview = text_item['value'][:30] + "..." if len(text_item['value']) > 30 else text_item['value']
        button_text = f"✏️ {text_item['key']}: {preview}"
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"edit_text_{category}_{text_item['key']}"
        )])
    
    buttons.append([InlineKeyboardButton(text=get_admin_text('back', language), callback_data="admin_edit_texts")])
    
    if len(buttons) > 1:
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Нет текстов для редактирования в этой категории")

@router.callback_query(F.data.startswith("edit_text_"))
async def handle_edit_text(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    parts = callback.data.split("_")
    if len(parts) >= 4:
        category = parts[2]
        text_key = "_".join(parts[3:])
        
        current_text = text_editor_db.get_text(category, text_key, language)
        
        if not current_text:
            # Получаем текст из стандартных источников
            from shop.texts import TEXTS as SHOP_TEXTS
            from payments.texts import TEXTS as PAYMENT_TEXTS
            from profiles.texts import TEXTS as PROFILE_TEXTS
            from settings.texts import TEXTS as SETTINGS_TEXTS
            from base.texts import TEXTS as BASE_TEXTS
            
            text_sources = {
                'shop': SHOP_TEXTS,
                'payment': PAYMENT_TEXTS,
                'premium': PAYMENT_TEXTS,
                'profile': PROFILE_TEXTS,
                'settings': SETTINGS_TEXTS,
                'base': BASE_TEXTS
            }
            
            if category in text_sources:
                source_texts = text_sources[category].get(language, text_sources[category]['ru'])
                current_text = source_texts.get(text_key, f"[{text_key}]")
        
        await state.update_data(category=category, text_key=text_key)
        await state.set_state(TextEditorStates.waiting_for_text_input)
        
        text = get_admin_text('text_key', language, key=text_key) + "\n\n"
        text += get_admin_text('current_text', language) + ":\n"
        text += f"<code>{current_text}</code>\n\n"
        text += get_admin_text('enter_new_text', language)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_texts_{category}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.message(TextEditorStates.waiting_for_text_input)
async def handle_new_text_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    data = await state.get_data()
    category = data['category']
    text_key = data['text_key']
    new_text = message.text.strip()
    
    if text_editor_db.save_text(category, text_key, language, new_text):
        await state.clear()
        
        text = get_admin_text('text_saved', language) + "\n\n"
        text += get_admin_text('text_key', language, key=text_key) + "\n"
        text += f"Новый текст: <code>{new_text}</code>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать другой текст", callback_data=f"edit_texts_{category}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_edit_texts")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await message.answer("❌ Ошибка при сохранении текста")


# ==================== РЕДАКТИРОВАНИЕ ИНСТРУКЦИИ ВЫДАЧИ ТОВАРА ====================

@router.callback_query(F.data.startswith("edit_delivery_text_"))
async def edit_delivery_instruction(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[3])
    language = get_user_language(callback.from_user.id)
   
    product = product_db.get_product_by_id(product_id)   # product_db уже импортирован выше
   
    text = f"📦 Товар: <b>{product.name}</b>\n\n"
    text += "Введите новый текст выдачи после оплаты (можно использовать HTML):\n"
    text += "Переменные: {order_number} — номер заказа\n\n"
    text += f"Текущий текст:\n<code>{product.delivery_instruction or 'Не задан (будет использоваться общий)'}</code>"
   
    await state.update_data(product_id=product_id)
    await state.set_state(AdminStates.waiting_for_delivery_instruction)  # новый стейт
   
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_view_product_{product_id}")]
    ]))

@router.message(AdminStates.waiting_for_delivery_instruction)
async def save_delivery_instruction(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data['product_id']
    new_text = message.text.strip()
   
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET delivery_instruction = ? WHERE id = ?", (new_text, product_id))
        conn.commit()
   
    await state.clear()
    await message.answer("✅ Текст выдачи сохранён!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к товару", callback_data=f"admin_view_product_{product_id}")]
    ]))