import os
import aiohttp
import asyncio
import sqlite3
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from bot_instance import BotInstance
from base.methods import get_user_language
import qrcode
from io import BytesIO
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from dirrrr import PROJECT_ROOT
from admin.methods import RulesAndInstructionsDB

TONAPI_BASE = "https://tonapi.io/v2"
MERCHANT_ADDRESS = os.getenv("MERCHANT_TON_ADDRESS")
API_KEY = os.getenv("TONAPI_KEY")

_last_transactions = []
_last_tx_fetch_time = datetime.min
_tx_lock = asyncio.Lock()

async def fetch_recent_transactions():
    global _last_transactions, _last_tx_fetch_time
    async with _tx_lock:
        now = datetime.utcnow()
        if (now - _last_tx_fetch_time) < timedelta(seconds=5):
            return _last_transactions
        url = f"{TONAPI_BASE}/blockchain/accounts/{MERCHANT_ADDRESS}/transactions?limit=100"
        try:
            async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {API_KEY}"}) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        txs = data.get("transactions", [])
                        _last_transactions = txs
                        _last_tx_fetch_time = now
                        return txs
                    else:
                        return _last_transactions
        except Exception:
            return _last_transactions

_last_ton_price = None
_last_price_fetch_time = datetime.min
_price_lock = asyncio.Lock()

async def get_ton_price_usd():
    global _last_ton_price, _last_price_fetch_time
    async with _price_lock:
        now = datetime.utcnow()
        if _last_ton_price is not None and (now - _last_price_fetch_time) < timedelta(seconds=5):
            return _last_ton_price
        url = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = float(data["the-open-network"]["usd"])
                        _last_ton_price = price
                        _last_price_fetch_time = now
                        return price
                    else:
                        return _last_ton_price if _last_ton_price is not None else 1.2
        except Exception:
            return _last_ton_price if _last_ton_price is not None else 1.2

class TonDirectPayments:
    def __init__(self):
        self.session = None
        self.db_file = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ton_direct_payments (
                    order_id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    comment TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'pending',
                    tx_hash TEXT,
                    paid_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
        asyncio.create_task(self._polling_loop())

    def generate_comment(self, order_id: int) -> str:
        return f"VerifOrder#{order_id}"

    async def register_order(self, order_id: int, user_id: int, amount: float) -> str:
        comment = self.generate_comment(order_id)
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO ton_direct_payments
                (order_id, user_id, amount, comment, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (order_id, user_id, amount, comment))
            conn.commit()
        return comment

    async def check_order_payment(self, order_id: int) -> Optional[str]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT comment, amount, status FROM ton_direct_payments WHERE order_id = ?
            ''', (order_id,))
            row = cursor.fetchone()
            if not row:
                return None
            comment, expected_usd, current_status = row
            if current_status == 'paid':
                return 'paid'

        recent_transactions = await fetch_recent_transactions()
        ton_price = await get_ton_price_usd()
        min_ton_needed = (expected_usd / ton_price) * 0.9

        for tx in recent_transactions:
            in_msg = tx.get("in_msg", {})
            if not in_msg:
                continue
            msg_comment = (
                in_msg.get("decoded_body", {}).get("text", "") or
                in_msg.get("message", "") or
                in_msg.get("raw_body", "")
            )
            tx_value_nano = int(in_msg.get("value", 0))
            tx_value_ton = tx_value_nano / 1_000_000_000
            if comment in msg_comment and tx_value_ton >= min_ton_needed:
                tx_hash = tx["hash"]
                with sqlite3.connect(self.db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE ton_direct_payments
                        SET status = 'paid', tx_hash = ?, paid_at = CURRENT_TIMESTAMP
                        WHERE order_id = ?
                    ''', (tx_hash, order_id))
                    conn.commit()
                await self._process_paid_order(order_id, tx_hash)
                return 'paid'
        return 'pending'

    async def _process_paid_order(self, order_id: int, tx_hash: str):
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE orders
                    SET status = 'paid',
                        payment_method = 'tonkeeper',
                        payment_id = ?,
                        paid_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (tx_hash, order_id))
                cursor.execute('''
                    SELECT user_id, product_id, final_price, discount_percent
                    FROM orders
                    WHERE id = ?
                ''', (order_id,))
                order_data = cursor.fetchone()
                if not order_data:
                    print(f"[TON PROCESS] Заказ {order_id} не найден после UPDATE")
                    return
                user_id, product_id, final_price, discount = order_data
                conn.commit()

            from profiles.methods import ReferralMethodsDB
            referral_db = ReferralMethodsDB()
            referral_db.add_referral_bonus(order_id)

            product_name = "Товар"
            if product_id > 0:
                admin_db_path = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")
                with sqlite3.connect(admin_db_path) as admin_conn:
                    admin_cursor = admin_conn.cursor()
                    admin_cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
                    res = admin_cursor.fetchone()
                    if res:
                        product_name = res[0]

            admin_message = (
                f"💰 <b>НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ TON!</b>\n\n"
                f"📦 Заказ: <b>№{order_id}</b>\n"
                f"👤 Пользователь: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
                f"🛒 Товар: {product_name}\n"
                f"💵 Сумма: ${final_price:.2f}\n"
                f"💳 Tx: {tx_hash}\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
            )
            if discount > 0:
                admin_message += f"\n🎯 Скидка: {discount}%"

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

            bot = BotInstance.get_bot()
            admin_id = int(os.getenv('ADMIN_ID', '0'))
            group_chat_id = os.getenv('NOTIFICATION_CHAT_ID')

            if product_id > 0 and admin_id:
                try:
                    await bot.send_message(
                        admin_id,
                        admin_message,
                        reply_markup=admin_keyboard,
                        parse_mode="HTML"
                    )
                    print("[TON] Уведомление админу отправлено")
                except Exception as e:
                    print(f"[TON] Ошибка отправки админу: {e}")

            if product_id > 0 and group_chat_id:
                try:
                    await bot.send_message(
                        group_chat_id,
                        admin_message,
                        reply_markup=admin_keyboard,
                        parse_mode="HTML"
                    )
                    print("[TON] Уведомление в группу отправлено")
                except Exception as e:
                    print(f"[TON] Ошибка отправки в группу: {e}")

            if product_id < 0:
                days = abs(product_id)
                from payments.methods import SubscriptionMethodsDB
                subscription_db = SubscriptionMethodsDB()
                subscription_db.create_subscription(user_id, days, final_price)
                await self._notify_user_premium(user_id, order_id, days)
            else:
                await self._notify_user_product(user_id, order_id)

        except Exception as e:
            print(f"Ошибка обработки оплаты TON: {e}")

    async def _notify_user_premium(self, user_id: int, order_id: int, days: int):
        try:
            bot = BotInstance.get_bot()
           
            message = "⭐ <b>Ваша Premium подписка успешно активирована!</b>\n\n"
            message += f"📅 Срок: {days} дней\n"
            message += "🎯 Теперь вы получаете скидку на все товары в магазине!"
           
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Перейти в магазин", callback_data="shop_m")]
            ])
           
            await bot.send_message(user_id, message, reply_markup=keyboard, parse_mode="HTML")
            print(f"[TON PREMIUM] Уведомление пользователю {user_id} отправлено")
           
        except Exception as e:
            print(f"[TON PREMIUM] Ошибка уведомления премиум: {e}")

    async def _notify_user_product(self, user_id: int, order_id: int):
        try:
            bot = BotInstance.get_bot()
            print(f"[TON] [ЗАКАЗ {order_id}] Начинаем выдачу пользователю {user_id}")
            
            db_path = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")
            admin_db_path = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")

            # 1. Получаем product_id из orders
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT product_id FROM orders WHERE id = ?", (order_id,))
                order_row = cursor.fetchone()

            if not order_row:
                print(f"[TON] Заказ #{order_id} → не найден в orders")
                await bot.send_message(user_id, f"✅ Оплата получена! Заказ №{order_id}")
                return

            product_id = order_row[0]
            print(f"[TON] Заказ #{order_id} → product_id = {product_id}")

            # 2. Получаем имя и инструкцию товара
            product_name = "Товар"
            custom_instruction = None

            with sqlite3.connect(admin_db_path) as admin_conn:
                admin_cursor = admin_conn.cursor()
                admin_cursor.execute("""
                    SELECT name, delivery_instruction
                    FROM products
                    WHERE id = ?
                """, (product_id,))
                prod_row = admin_cursor.fetchone()

            if prod_row:
                product_name = prod_row[0] or "Товар"
                custom_instruction = prod_row[1]
                print(f"[TON] Товар найден: {product_name}")
                print(f"[TON] Индивидуальная инструкция: {custom_instruction!r}")
            else:
                print(f"[TON] Товар {product_id} не найден в products")

            # 3. Формируем сообщение — приоритет индивидуальной
            message = f"✅ <b>Оплата получена!</b>\n\n"
            message += f"<b>Ваш номер заказа: №{order_id}</b>\n\n"

            if custom_instruction is not None:
                cleaned = str(custom_instruction).strip()
                print(f"[TON] raw = {custom_instruction!r}, cleaned = {cleaned!r}")
                if cleaned:
                    message += cleaned.replace("{order_number}", str(order_id))
                    print("[TON] → Взята ИНДИВИДУАЛЬНАЯ инструкция товара")
                else:
                    message += "Спасибо за покупку! Свяжитесь с поддержкой."
                    print("[TON] → Индивидуальная инструкция пустая после strip")
            else:
                print("[TON] → Индивидуальной инструкции НЕТ, идём к общей")
                rules_db = RulesAndInstructionsDB()
                active = rules_db.get_active_post_payment_instruction()
                if active and active.get('instruction_text'):
                    txt = active['instruction_text'].replace("{order_number}", str(order_id))
                    message += txt
                    print("[TON] → Взята ОБЩАЯ инструкция")
                else:
                    message += "Спасибо за покупку! Свяжитесь с поддержкой."
                    print("[TON] → Нет инструкций вообще")

            message += "\n\n"

            # 4. Кнопки — active загружаем ВСЕГДА
            buttons = []

            rules_db = RulesAndInstructionsDB()
            active = rules_db.get_active_post_payment_instruction()

            delivery_bot_username = None
            if active and active.get('delivery_bot_username'):
                delivery_bot_username = active['delivery_bot_username'].lstrip('@')
                print(f"[TON] → Бот из общей инструкции: @{delivery_bot_username}")

            if delivery_bot_username:
                buttons.append([
                    InlineKeyboardButton(
                        text="📤 Отправить данные",
                        url=f"https://t.me/{delivery_bot_username}?start=order_{order_id}"
                    )
                ])
            else:
                print("[TON] → Нет бота в общей инструкции")

            buttons.append([
                InlineKeyboardButton(
                    text="🛒 Вернуться в магазин",
                    callback_data="shop_m"
                )
            ])

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await bot.send_message(
                user_id,
                message,
                reply_markup=keyboard,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            print("[TON] Сообщение отправлено успешно")

        except Exception as e:
            print(f"[ОШИБКА ВЫДАЧИ TON ЗАКАЗА {order_id}]: {e}")
            import traceback
            traceback.print_exc()
            await bot.send_message(user_id, f"✅ Оплата получена! Заказ №{order_id}")

    async def _polling_loop(self):
        while True:
            try:
                with sqlite3.connect(self.db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT order_id FROM ton_direct_payments WHERE status = 'pending'")
                    pending = [row[0] for row in cursor.fetchall()]
                for order_id in pending:
                    await self.check_order_payment(order_id)
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(60)

ton_direct = TonDirectPayments()