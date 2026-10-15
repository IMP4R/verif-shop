import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from typing import Callable, Dict, Any

from base.methods import get_user_language
from payments.methods import PaymentMethodsDB, SubscriptionMethodsDB
from shop.methods import ProductMethodsDB
from payments.texts import get_payment_text

router = Router()
payment_db = PaymentMethodsDB()
product_db = ProductMethodsDB()
subscription_db = SubscriptionMethodsDB()


async def on_product_payment_success(invoice_id: int, order_id: int, user_id: int):
    try:
        with payment_db.conn as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = 'paid', 
                    payment_method = 'cryptobot',
                    payment_id = ?,
                    paid_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (str(invoice_id), order_id))
            
            cursor.execute('SELECT product_id FROM orders WHERE id = ?', (order_id,))
            product_id = cursor.fetchone()[0]
            
            cursor.execute('SELECT name FROM admin.methods_data.products WHERE id = ?', (product_id,))
            product_name = cursor.fetchone()[0] if cursor.fetchone() else 'Товар'
            
            from profiles.methods import ReferralMethodsDB
            referral_db = ReferralMethodsDB()
            referral_db.add_referral_bonus(order_id)
            
            await notify_admin_payment_success(order_id, user_id, product_name, invoice_id)
            
    except Exception as e:
        print(f"Error processing product payment success: {e}")


async def on_subscription_payment_success(invoice_id: int, order_id: int, user_id: int):
    try:
        with payment_db.conn as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = 'paid', 
                    payment_method = 'cryptobot',
                    payment_id = ?,
                    paid_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (str(invoice_id), order_id))
            
            cursor.execute('SELECT product_id FROM orders WHERE id = ?', (order_id,))
            product_id = cursor.fetchone()[0]
            
            subscription_db.create_subscription(user_id, 1, 10.0)
            
            await notify_admin_subscription_success(order_id, user_id, invoice_id)
            
    except Exception as e:
        print(f"Error processing subscription payment success: {e}")


async def notify_admin_payment_success(order_id: int, user_id: int, product_name: str, invoice_id: str):
    from bot_instance import BotInstance
    import os
    
    admin_id = int(os.getenv('ADMIN_ID', '0'))
    if admin_id:
        bot = BotInstance.get_bot()
        
        message = f"✅ Новая оплата!\n\n"
        message += f"📦 Заказ #{order_id}\n"
        message += f"👤 Пользователь: {user_id}\n"
        message += f"🛒 Товар: {product_name}\n"
        message += f"💳 Invoice ID: {invoice_id}\n"
        message += f"💰 CryptoBot: {invoice_id}\n"
        
        try:
            await bot.send_message(admin_id, message)
        except Exception as e:
            print(f"Error sending admin notification: {e}")


async def notify_admin_subscription_success(order_id: int, user_id: int):
    from bot_instance import BotInstance
    import os
    
    admin_id = int(os.getenv('ADMIN_ID', '0'))
    if admin_id:
        bot = BotInstance.get_bot()
        
        message = f"✅ Новая Premium подписка!\n\n"
        message += f"📦 Заказ #{order_id}\n"
        message += f"👤 Пользователь: {user_id}\n"
        
        try:
            await bot.send_message(admin_id, message)
        except Exception as e:
            print(f"Error sending admin notification: {e}")







