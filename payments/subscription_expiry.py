import os
import asyncio
import sqlite3
from datetime import datetime
from bot_instance import BotInstance
from base.methods import get_user_language
from dirrrr import PROJECT_ROOT

async def deactivate_expired_subscriptions():
    while True:
        try:
            print(f"[{datetime.now()}] Проверка просроченных подписок...")
            
            expired_subscriptions = []
            
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
                cursor = conn.cursor()
                
                # Проверяем только подписки, которые истекли И еще не были уведомлены
                cursor.execute('''
                    SELECT s.id, s.user_id, s.end_date, s.discount
                    FROM subscriptions s
                    LEFT JOIN subscription_notifications n ON s.id = n.subscription_id 
                        AND n.notification_type = 'expired'
                    WHERE s.is_active = 1 
                    AND datetime(s.end_date) < datetime('now')
                    AND n.id IS NULL  -- Еще не было уведомления об истечении
                ''')
                
                expired_subs = cursor.fetchall()
                
                if expired_subs:
                    # Деактивируем просроченные подписки
                    cursor.execute('''
                        UPDATE subscriptions 
                        SET is_active = 0 
                        WHERE is_active = 1 
                        AND datetime(end_date) < datetime('now')
                    ''')
                    
                    # Записываем уведомления в базу
                    for sub_id, user_id, end_date, discount in expired_subs:
                        cursor.execute('''
                            INSERT INTO subscription_notifications 
                            (subscription_id, user_id, notification_type, sent_at)
                            VALUES (?, ?, 'expired', CURRENT_TIMESTAMP)
                        ''', (sub_id, user_id))
                    
                    expired_subscriptions = expired_subs
                    conn.commit()
                    print(f"Деактивировано {len(expired_subs)} просроченных подписок")
            
            if expired_subscriptions:
                bot = BotInstance.get_bot()
                
                for sub_id, user_id, end_date, discount in expired_subscriptions:
                    try:
                        language = get_user_language(user_id)
                        
                        if language == 'ru':
                            message = f"⚠️ <b>Ваша Premium подписка истекла!</b>\n\n"
                            message += f"📅 Дата окончания: {end_date}\n"
                            message += f"🎯 Скидка {discount}% больше не действует\n\n"
                            message += f"🔄 Чтобы снова получать скидки, продлите подписку в разделе Premium"
                        else:
                            message = f"⚠️ <b>Your Premium subscription has expired!</b>\n\n"
                            message += f"📅 End date: {end_date}\n"
                            message += f"🎯 {discount}% discount is no longer active\n\n"
                            message += f"🔄 To get discounts again, renew your subscription in the Premium section"
                        
                        await bot.send_message(user_id, message, parse_mode="HTML")
                        print(f"Уведомление отправлено пользователю {user_id} об истечении подписки")
                        
                    except Exception as e:
                        print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")
            
            await notify_upcoming_expirations()
            
        except Exception as e:
            print(f"Ошибка при проверке просроченных подписок: {e}")
        
        await asyncio.sleep(3600)  # Проверяем каждый час

async def notify_upcoming_expirations():
    try:
        bot = BotInstance.get_bot()
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.id, s.user_id, s.end_date, s.discount
                FROM subscriptions s
                LEFT JOIN subscription_notifications n ON s.id = n.subscription_id AND n.notification_type = 'expiring'
                WHERE s.is_active = 1
                  AND datetime(s.end_date) BETWEEN datetime('now', '+1 day') AND datetime('now', '+3 days')
                  AND n.id IS NULL
            ''')
            subs = cursor.fetchall()

            for sub_id, user_id, end_date, discount in subs:
                language = get_user_language(user_id)
                days_left = (datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S") - datetime.now()).days

                if language == 'ru':
                    msg = f"⏳ <b>Ваша Premium подписка скоро истекает!</b>\n\nДействует до: {end_date}\nОсталось: {days_left} дней\nСкидка: {discount}%\n\nПродлите подписку, чтобы не потерять скидки!"
                else:
                    msg = f"⏳ <b>Your Premium subscription is expiring soon!</b>\n\nValid until: {end_date}\n{days_left} days left\nDiscount: {discount}%\n\nRenew to keep discounts!"

                await bot.send_message(user_id, msg, parse_mode="HTML")

                cursor.execute('''
                    INSERT INTO subscription_notifications (subscription_id, user_id, notification_type)
                    VALUES (?, ?, 'expiring')
                ''', (sub_id, user_id))
                conn.commit()
    except Exception as e:
        print(f"Upcoming expiry error: {e}")

async def start_subscription_checker():
    # Инициализируем таблицу уведомлений
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscription_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL, -- 'expired', '3days', '1day'
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subscription_id, notification_type)
            )
        ''')
        conn.commit()
    
    asyncio.create_task(deactivate_expired_subscriptions())
    print("Запущен планировщик проверки Premium подписок")