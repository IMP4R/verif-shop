from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import os
import sqlite3
from datetime import datetime

from base.methods import get_user_language
from bot_instance import BotInstance
from dirrrr import PROJECT_ROOT
from admin.methods import RulesAndInstructionsDB

router = Router()
rules_db = RulesAndInstructionsDB()

ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))
REVIEW_CHANNEL = "https://t.me/repvaguro"  # Канал для отзывов

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

@router.callback_query(F.data.startswith("order_completed_"))
async def handle_order_completed(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    order_id = int(callback.data.split("_")[2])
    
    # Обновляем статус заказа на "completed"
    try:
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = 'completed'
                WHERE id = ?
            ''', (order_id,))
            
            # Получаем данные о пользователе
            cursor.execute('SELECT user_id FROM orders WHERE id = ?', (order_id,))
            result = cursor.fetchone()
            
            if not result:
                await callback.answer("❌ Заказ не найден")
                return
            
            target_user_id = result[0]
            
            # Отправляем уведомление пользователю
            bot = BotInstance.get_bot()
            
            user_message = "✅ <b>Заказ успешно выполнен!</b>\n\n"
            user_message += f"📦 Ваш заказ №{order_id} был выполнен.\n"
            user_message += "🙏 Пожалуйста, оставьте отзыв о нашей работе.\n\n"
            user_message += "Ваш отзыв поможет нам стать лучше! 💫"
            
            # Создаем кнопку для отзыва
            review_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⭐ Оставить отзыв",
                    url=REVIEW_CHANNEL
                )],
                [InlineKeyboardButton(
                    text="🛒 Вернуться в магазин",
                    callback_data="shop_m"
                )]
            ])
            
            try:
                await bot.send_message(target_user_id, user_message, reply_markup=review_keyboard, parse_mode="HTML")
                
                # Отмечаем кнопку как выполненную
                await callback.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Заказ выполнен (отправлено)",
                            callback_data="no_action"
                        )],
                        [InlineKeyboardButton(
                            text="📋 Детали заказа",
                            callback_data=f"order_details_{order_id}"
                        )]
                    ])
                )
                
                await callback.answer("✅ Пользователь уведомлен о выполнении заказа")
                
            except Exception as e:
                print(f"Не удалось уведомить пользователя: {e}")
                await callback.answer(f"❌ Не удалось уведомить пользователя: {e}")
    
    except Exception as e:
        print(f"Error completing order: {e}")
        await callback.answer("❌ Ошибка при обработке заказа")

@router.callback_query(F.data.startswith("order_details_"))
async def handle_order_details(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    order_id = int(callback.data.split("_")[2])
    
    try:
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT o.user_id, o.product_id, o.final_price, o.discount_percent, 
                    o.status, o.created_at, o.paid_at,
                    (SELECT name FROM admin.methods_data.products WHERE id = o.product_id) as product_name
                FROM orders o
                WHERE o.id = ?
            ''', (order_id,))
            
            order_data = cursor.fetchone()
            
            if not order_data:
                await callback.answer("❌ Заказ не найден")
                return
            
            (user_id_db, product_id, final_price, discount_percent, 
            status, created_at, paid_at, product_name) = order_data
            
            product_name = product_name or "Товар"
            
            text = f"📋 <b>Детали заказа #{order_id}</b>\n\n"
            text += f"👤 Пользователь: <a href='tg://user?id={user_id_db}'>{user_id_db}</a>\n"
            text += f"🛒 Товар: {product_name} (ID: {product_id})\n"
            text += f"💰 Сумма: ${final_price:.2f}\n"
            
            if discount_percent and discount_percent > 0:
                text += f"🎯 Скидка: {discount_percent}%\n"
            
            text += f"📊 Статус: {status}\n"
            text += f"📅 Создан: {created_at}\n"
            
            if paid_at:
                text += f"💰 Оплачен: {paid_at}\n"
            
            
            # Добавляем кнопки действий
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_orders"
                )]
            ])
            
            if status == 'paid':
                keyboard.inline_keyboard.insert(0, [
                    InlineKeyboardButton(
                        text="✅ Заказ выполнен",
                        callback_data=f"order_completed_{order_id}"
                    )
                ]) 
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    
    except Exception as e:
        print(f"Error getting order details: {e}")
        await callback.answer("❌ Ошибка при получении данных")

@router.callback_query(F.data == "no_action")
async def handle_no_action(callback: CallbackQuery):
    await callback.answer("Действие уже выполнено")