import os
import asyncio
from datetime import datetime, timedelta
from bot_instance import BotInstance
from base.methods import get_user_language
from payments.texts import get_payment_text
import sqlite3
from dirrrr import PROJECT_ROOT
async def check_subscription_expiry():
    while True:
        try:
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    SELECT user_id, end_date FROM subscriptions
                    WHERE is_active = 1 AND end_date < ?
                ''', (now,))
                
                expired_subs = cursor.fetchall()
                
                for user_id, end_date in expired_subs:
                    language = get_user_language(user_id)
                    bot = BotInstance.get_bot()
                    
                    message = get_payment_text('subscription_expired', language).format(
                        end_date=end_date
                    )
                    
                    try:
                        await bot.send_message(user_id, message, parse_mode="HTML")
                    except:
                        pass
                    
                    cursor.execute('''
                        UPDATE subscriptions
                        SET is_active = 0
                        WHERE user_id = ?
                    ''', (user_id,))
                
                three_days_later = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    SELECT user_id, end_date FROM subscriptions 
                    WHERE is_active = 1 AND end_date <= ? AND end_date > ?
                ''', (three_days_later, now))
                
                expiring_3days = cursor.fetchall()
                
                for user_id, end_date in expiring_3days:
                    language = get_user_language(user_id)
                    bot = BotInstance.get_bot()
                    
                    message = get_payment_text('subscription_expiring_3days', language).format(
                        end_date=end_date
                    )
                    
                    try:
                        await bot.send_message(user_id, message, parse_mode="HTML")
                    except:
                        pass
                
                one_day_later = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute('''
                    SELECT user_id, end_date FROM subscriptions 
                    WHERE is_active = 1 AND end_date <= ? AND end_date > ?
                ''', (one_day_later, now))
                
                expiring_1day = cursor.fetchall()
                
                for user_id, end_date in expiring_1day:
                    language = get_user_language(user_id)
                    bot = BotInstance.get_bot()
                    
                    message = get_payment_text('subscription_expiring_1day', language).format(
                        end_date=end_date
                    )
                    
                    try:
                        pass
                        #await bot.send_message(user_id, message, parse_mode="HTML")
                    except:
                        pass
                
                conn.commit()
            
            await asyncio.sleep(3600)
        
        except Exception as e:
            print(f"Error in subscription check: {e}")
            await asyncio.sleep(60)