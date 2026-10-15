import os
import aiohttp
import asyncio
import sqlite3
from typing import Optional, Dict, List
from dirrrr import PROJECT_ROOT
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot_instance import BotInstance

CRYPTOBOT_API = "https://pay.crypt.bot/api"

class CryptoBot:
    def __init__(self):
        self.token = os.getenv('CRYPTOBOT_TOKEN')
        self.session = None
        self.db_file = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")
        self.init_db()
   
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS crypto_invoices (
                    invoice_id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    pay_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
   
    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={'Crypto-Pay-API-Token': self.token},
                connector=aiohttp.TCPConnector(ssl=False)
            )
       
        asyncio.create_task(self._check_payments_loop())
   
    async def create_invoice(self, order_id: int, user_id: int, amount: float, description: str = "") -> Optional[Dict]:
        if not self.token:
            print("CRYPTOBOT_TOKEN не найден в .env")
            return None
       
        if not self.session:
            await self.start()
       
        try:
            data = {
                "asset": "USDT",
                "amount": str(amount),
                "description": description,
                "payload": str(order_id),
                "expires_in": 1800,
                "allow_comments": True
            }
           
            async with self.session.post(
                f"{CRYPTOBOT_API}/createInvoice",
                json=data,
                ssl=False
            ) as response:
                result = await response.json()
               
                if result.get('ok'):
                    invoice_data = result['result']
                   
                    with sqlite3.connect(self.db_file) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO crypto_invoices (invoice_id, order_id, user_id, amount, pay_url, status)
                            VALUES (?, ?, ?, ?, ?, 'active')
                        ''', (
                            invoice_data['invoice_id'],
                            order_id,
                            user_id,
                            amount,
                            invoice_data['pay_url']
                        ))
                        conn.commit()
                   
                    return {
                        'pay_url': invoice_data['pay_url'],
                        'invoice_id': invoice_data['invoice_id'],
                        'status': invoice_data['status']
                    }
                else:
                    print(f"CryptoBot API error: {result}")
                    return None
               
        except Exception as e:
            print(f"CryptoBot error: {e}")
            return None
   
    async def check_invoice_status(self, invoice_id: int) -> Optional[str]:
        if not self.session:
            await self.start()
       
        try:
            async with self.session.get(
                f"{CRYPTOBOT_API}/getInvoices",
                params={"invoice_ids": str(invoice_id)},
                ssl=False
            ) as response:
                result = await response.json()
               
                if result.get('ok') and result['result']['items']:
                    status = result['result']['items'][0]['status']
                   
                    with sqlite3.connect(self.db_file) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE crypto_invoices SET status = ? WHERE invoice_id = ?
                        ''', (status, invoice_id))
                        conn.commit()
                   
                    return status
                return None
               
        except Exception as e:
            print(f"CryptoBot check error: {e}")
            return None
   
    async def get_invoice_by_order(self, order_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT invoice_id, status FROM crypto_invoices
                WHERE order_id = ? ORDER BY created_at DESC LIMIT 1
            ''', (order_id,))
            result = cursor.fetchone()
           
            if result:
                return {'invoice_id': result[0], 'status': result[1]}
            return None
   
    async def check_order_payment(self, order_id: int) -> Optional[str]:
        invoice = await self.get_invoice_by_order(order_id)
       
        if not invoice:
            return None
       
        if invoice['status'] == 'paid':
            return 'paid'
       
        current_status = await self.check_invoice_status(invoice['invoice_id'])
       
        if current_status == 'paid':
            await self._process_paid_order(order_id, invoice['invoice_id'])
       
        return current_status
   
    async def _activate_premium_subscription(self, user_id: int, order_id: int, days: int = None):
        try:
            from payments.methods import SubscriptionMethodsDB
            subscription_db = SubscriptionMethodsDB()
           
            with sqlite3.connect(self.db_file, timeout=30) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT final_price FROM orders WHERE id = ?', (order_id,))
                result = cursor.fetchone()
                price = result[0] if result else 10.0
           
            subscription = subscription_db.create_subscription(user_id, days, price)
           
            if subscription:
                print(f"✅ Premium подписка создана для user {user_id}, {days} дней")
                await self._notify_admin(f"Premium подписка! Заказ #{order_id} [{user_id}], {days} дней")
                await self._notify_user_premium(user_id, order_id, days)
            else:
                print(f"❌ Не удалось создать подписку для user {user_id}")
               
        except Exception as e:
            print(f"Error activating premium: {e}")
            import traceback
            traceback.print_exc()
   
    async def _process_product_payment(self, order_id: int, user_id: int, product_id: int):
        try:
            from profiles.methods import ReferralMethodsDB
            referral_db = ReferralMethodsDB()
            referral_db.add_referral_bonus(order_id)
           
            await self._notify_admin(f"Товар оплачен! Заказ #{order_id}, пользователь {user_id}, товар #{product_id}")
           
        except Exception as e:
            print(f"Error processing product payment: {e}")
   
    async def _notify_admin(self, message: str, user_id: int = None):
        import os
       
        admin_id = int(os.getenv('ADMIN_ID', '0'))
        if admin_id and admin_id > 0:
            try:
                bot = BotInstance.get_bot()
               
                if user_id:
                    user_link = f"tg://user?id={user_id}"
                    message = message.replace(f"Пользователь: {user_id}",
                                            f"Пользователь: <a href='{user_link}'>{user_id}</a>")
               
                await bot.send_message(admin_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Error notifying admin: {e}")
   
    async def _notify_user_premium(self, user_id: int, order_id: int, days: int = None):
        try:
            bot = BotInstance.get_bot()
           
            message = "⭐ <b>Ваша Premium подписка успешно активирована!</b>\n\n"
            message += "🎯 Теперь вы получаете скидку на все товары в магазине.\n"
           
            await bot.send_message(user_id, message, parse_mode="HTML")
            print(f"Notified user {user_id} about premium activation")
           
        except Exception as e:
            print(f"Error notifying user about premium: {e}")
   
    async def _notify_user_product(self, user_id: int, order_id: int):
        bot = BotInstance.get_bot()
        print(f"[ЗАКАЗ {order_id}] Начинаем выдачу пользователю {user_id}")
        try:
            db_path = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")
            print(f"[DEBUG] Путь к БД заказов: {db_path}")
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        o.product_id,
                        (SELECT name FROM admin.methods_data.products WHERE id = o.product_id) AS product_name,
                        (SELECT delivery_instruction FROM admin.methods_data.products WHERE id = o.product_id) AS delivery_instruction
                    FROM orders o
                    WHERE o.id = ?
                ''', (order_id,))
                
                row = cursor.fetchone()
                
                if row:
                    product_id, product_name, custom_instruction = row
                    print(f"[DEBUG] Заказ #{order_id} | Товар ID: {product_id} | Название: {product_name}")
                    print(f"[DEBUG] Индивидуальная инструкция: {custom_instruction!r}")
                else:
                    print(f"[DEBUG] Заказ #{order_id} не найден")
                    custom_instruction = None
                    product_name = "Товар"
            
            message = f"✅ <b>Оплата получена!</b>\n\n"
            message += f"<b>Ваш номер заказа: №{order_id}</b>\n\n"
            
            if custom_instruction and custom_instruction.strip():
                message += custom_instruction.replace("{order_number}", str(order_id))
                print("[DEBUG] → Взята ИНДИВИДУАЛЬНАЯ инструкция")
            else:
                print("[DEBUG] → Индивидуальной инструкции НЕТ, идём к общей")
                from admin.methods import RulesAndInstructionsDB
                rules_db = RulesAndInstructionsDB()
                active = rules_db.get_active_post_payment_instruction()
                if active and active.get('instruction_text'):
                    txt = active['instruction_text'].replace("{order_number}", str(order_id))
                    if active.get('delivery_bot_username'):
                        txt = txt.replace("{bot_username}", active['delivery_bot_username'].lstrip('@'))
                    message += txt
                    print("[DEBUG] → Взята ОБЩАЯ инструкция")
                else:
                    message += "Спасибо за покупку! Свяжитесь с поддержкой."
                    print("[DEBUG] → Нет ни одной инструкции")
            
            message += "\n\n"
            
            buttons = [[InlineKeyboardButton(text="🛒 В магазин", callback_data="shop_m")]]
            
            # Кнопка "Отправить данные"
            if active and active.get('delivery_bot_username'):
                bot_un = active['delivery_bot_username'].lstrip('@')
                buttons.insert(0, [InlineKeyboardButton(
                    text="📤 Отправить данные",
                    url=f"https://t.me/{bot_un}?start=order_{order_id}"
                )])
                print(f"[DEBUG] → Добавлена кнопка отправки данных на @{bot_un}")
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await bot.send_message(user_id, message, reply_markup=keyboard, parse_mode="HTML")
            print("[DEBUG] Сообщение отправлено успешно")
        
        except Exception as e:
            print(f"[ОШИБКА ВЫДАЧИ ЗАКАЗА {order_id}]: {e}")
            await bot.send_message(user_id, f"✅ Оплата получена! Заказ №{order_id}")
   
    async def _check_payments_loop(self):
        while True:
            try:
                with sqlite3.connect(self.db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT invoice_id, order_id, user_id
                        FROM crypto_invoices
                        WHERE status = 'active'
                    ''')
                    active_invoices = cursor.fetchall()
               
                for invoice_id, order_id, user_id in active_invoices:
                    status = await self.check_invoice_status(invoice_id)
                    if status == 'paid':
                        print(f"Invoice {invoice_id} for order {order_id} paid!")
                        await self._process_paid_order(order_id, invoice_id)
                    elif status == 'expired':
                        print(f"Invoice {invoice_id} expired")
               
                await asyncio.sleep(10)
               
            except Exception as e:
                print(f"Error in payment check loop: {e}")
                await asyncio.sleep(60)
   
    async def _notify_group_chat(self, message: str):
        group_chat_id = os.getenv('NOTIFICATION_CHAT_ID')
        if group_chat_id:
            try:
                bot = BotInstance.get_bot()
                await bot.send_message(group_chat_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Error sending notification to group chat: {e}")
   
    async def _process_paid_order(self, order_id: int, invoice_id: int):
        print(f"[PROCESS] Начало обработки оплаченного заказа #{order_id} (invoice {invoice_id})")
        db_path = self.db_file
        print(f"[PROCESS] Путь к БД: {db_path}")
        
        for attempt in range(5):
            try:
                conn = sqlite3.connect(db_path, timeout=60)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA busy_timeout=60000")
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE orders
                    SET status = 'paid',
                        payment_method = 'cryptobot',
                        payment_id = ?,
                        paid_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (str(invoice_id), order_id))
                
                updated_rows = cursor.rowcount
                print(f"[UPDATE] Затронуто строк: {updated_rows}")
                
                cursor.execute('''
                    SELECT user_id, product_id, final_price, discount_percent
                    FROM orders
                    WHERE id = ?
                ''', (order_id,))
                order_data = cursor.fetchone()
                
                if not order_data:
                    print(f"[ERROR] Заказ {order_id} пропал после UPDATE")
                    conn.close()
                    return
                
                user_id, product_id, final_price, discount = order_data
                print(f"[DATA] user_id={user_id}, product_id={product_id}, сумма={final_price}")
                
                # Получаем имя товара
                product_name = "Товар"
                if product_id > 0:
                    try:
                        admin_db_path = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")
                        with sqlite3.connect(admin_db_path, timeout=10) as admin_conn:
                            admin_cursor = admin_conn.cursor()
                            admin_cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
                            res = admin_cursor.fetchone()
                            if res:
                                product_name = res[0]
                    except Exception as e:
                        print(f"[WARNING] Не удалось получить имя товара: {e}")
                        product_name = f"Товар ID {product_id}"
                
                conn.commit()
                conn.close()
                print(f"[SUCCESS] Заказ #{order_id} обработан (статус paid)")
                
                # Старое сообщение админу с кнопками
                from datetime import datetime
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                admin_message = f"💰 <b>НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ!</b>\n\n"
                admin_message += f"📦 Заказ: <b>№{order_id}</b>\n"
                admin_message += f"👤 Пользователь: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
                admin_message += f"🛒 Товар: {product_name}\n"
                admin_message += f"💵 Сумма: ${final_price:.2f}\n"
                if discount and discount > 0:
                    admin_message += f"🎯 Скидка: {discount}%\n"
                admin_message += f"💳 Invoice: {invoice_id}\n"
                admin_message += f"⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
                
                admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ Заказ выполнен",
                        callback_data=f"order_completed_{order_id}"
                    )],
                    [InlineKeyboardButton(
                        text="📋 Детали заказа",
                        callback_data=f"order_details_{order_id}"
                    )]
                ])
                
                admin_id = int(os.getenv('ADMIN_ID', '0'))
                group_chat_id = os.getenv('NOTIFICATION_CHAT_ID')
                
                if product_id > 0 and admin_id:
                    await self._notify_admin_with_keyboard(admin_id, admin_message, admin_keyboard)
                
                if product_id > 0 and group_chat_id:
                    await self._notify_group_with_keyboard(group_chat_id, admin_message, admin_keyboard)
                
                # Выдача товара
                if product_id < 0:
                    days = abs(product_id)
                    await self._activate_premium_subscription(user_id, order_id, days)
                else:
                    await self._process_product_payment(order_id, user_id, product_id)
                    await self._notify_user_product(user_id, order_id)
                
                return  # успех
                
            except sqlite3.OperationalError as e:
                print(f"[RETRY {attempt+1}/5] Ошибка БД: {e}")
                if "locked" in str(e).lower() or "timeout" in str(e).lower():
                    await asyncio.sleep(3 + attempt * 2)
                    continue
                break
            
            except Exception as e:
                print(f"[CRITICAL] Ошибка обработки заказа #{order_id}: {e}")
                import traceback
                traceback.print_exc()
                break
    
    async def _notify_admin_with_keyboard(self, admin_id: int, message: str, keyboard):
        bot = BotInstance.get_bot()
        try:
            await bot.send_message(admin_id, message, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending admin notification with keyboard: {e}")
    
    async def _notify_group_with_keyboard(self, chat_id: str, message: str, keyboard):
        bot = BotInstance.get_bot()
        try:
            await bot.send_message(chat_id, message, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending group notification with keyboard: {e}")
    
    async def _notify_group_chat(self, message: str, user_id: int = None):
        group_chat_id = os.getenv('NOTIFICATION_CHAT_ID')
       
        if not group_chat_id:
            print("NOTIFICATION_CHAT_ID не установлен в .env файле")
            return
       
        try:
            bot = BotInstance.get_bot()
           
            if user_id:
                user_link = f"tg://user?id={user_id}"
                message_with_link = message.replace(f"👤 Пользователь: {user_id}",
                                                f"👤 Пользователь: <a href='{user_link}'>{user_id}</a>")
            else:
                message_with_link = message
           
            await bot.send_message(group_chat_id, message_with_link, parse_mode="HTML")
            print(f"Уведомление отправлено в групповой чат {group_chat_id}")
           
        except Exception as e:
            print(f"Ошибка при отправке уведомления в групповой чат: {e}")

cryptobot = CryptoBot()