import os
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from dirrrr import PROJECT_ROOT

PROFILE_DB_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")


class ProfileMethodsDB:
    def __init__(self, db_file: str = PROFILE_DB_FILE):
        self.db_file = db_file
    
    def get_user_profile(self, user_id: int) -> Dict:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            profile_data = {
                'user_id': user_id,
                'total_orders': 0,
                'total_spent': 0.0,
                'premium_active': False,
                'premium_discount': 0.0,
                'premium_end_date': None
            }
            
            cursor.execute('''
                SELECT COUNT(*), SUM(final_price) 
                FROM orders 
                WHERE user_id = ? AND status = 'paid'
            ''', (user_id,))
            
            orders_result = cursor.fetchone()
            if orders_result and orders_result[0]:
                profile_data['total_orders'] = orders_result[0]
                profile_data['total_spent'] = orders_result[1] if orders_result[1] else 0.0
            
            cursor.execute('''
                SELECT discount, end_date 
                FROM subscriptions 
                WHERE user_id = ? AND is_active = 1 
                ORDER BY end_date DESC 
                LIMIT 1
            ''', (user_id,))
            
            subscription_result = cursor.fetchone()
            if subscription_result:
                profile_data['premium_active'] = True
                profile_data['premium_discount'] = subscription_result[0]
                profile_data['premium_end_date'] = subscription_result[1]
            
            return profile_data
    
    def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, product_id, final_price, discount_percent, created_at
                FROM orders 
                WHERE user_id = ? AND status = 'paid'
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            orders_data = cursor.fetchall()
            
            if not orders_data:
                return []
            
            orders = []
            
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")) as admin_conn:
                admin_cursor = admin_conn.cursor()
                
                for order_row in orders_data:
                    order_id, product_id, final_price, discount_percent, created_at = order_row
                    
                    product_name = 'Товар'
                    if product_id:
                        admin_cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
                        product_result = admin_cursor.fetchone()
                        if product_result:
                            product_name = product_result[0]
                    
                    orders.append({
                        'id': order_id,
                        'final_price': final_price,
                        'discount': discount_percent,
                        'created_at': created_at,
                        'product_name': product_name
                    })
            
            return orders


class ReferralMethodsDB:
    def __init__(self, db_file: str = PROFILE_DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    bonus_earned REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referral_withdrawals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending', -- pending, approved, rejected
                    details TEXT,
                    admin_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    async def generate_referral_link(self, user_id: int) -> str:
        from base.methods import get_bot_username
        bot_un = await get_bot_username()
        return f"https://t.me/{bot_un}?start=ref_{user_id}"
    
    def process_referral_registration(self, referred_user_id: int, start_param: str):
        if start_param.startswith("ref_"):
            referrer_id = int(start_param.split("_")[1])
            
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 1 FROM referrals 
                    WHERE referred_id = ? 
                    LIMIT 1
                ''', (referred_user_id,))
                
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO referrals (referrer_id, referred_id, status)
                        VALUES (?, ?, 'active')
                    ''', (referrer_id, referred_user_id))
                    
                    conn.commit()
    
    def get_user_referral_stats(self, user_id: int) -> Dict:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) 
                FROM referrals 
                WHERE referrer_id = ? AND status = 'active'
            ''', (user_id,))
            referrals_count = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT SUM(bonus_earned) 
                FROM referrals 
                WHERE referrer_id = ?
            ''', (user_id,))
            total_earned = cursor.fetchone()[0] or 0.0
            
            cursor.execute('''
                SELECT COALESCE(SUM(amount), 0) 
                FROM referral_withdrawals 
                WHERE user_id = ? AND status = 'approved'
            ''', (user_id,))
            withdrawn = cursor.fetchone()[0] or 0.0
            
            available = max(0, total_earned - withdrawn)
            
            return {
                'referrals_count': referrals_count,
                'earned': total_earned,
                'withdrawn': withdrawn,
                'available': available
            }
    
    def add_referral_bonus(self, order_id: int):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, final_price 
                FROM orders 
                WHERE id = ?
            ''', (order_id,))
            
            order_result = cursor.fetchone()
            if not order_result:
                return
            
            buyer_id = order_result[0]
            order_amount = order_result[1]
            
            cursor.execute('''
                SELECT referrer_id 
                FROM referrals 
                WHERE referred_id = ? AND status = 'active'
            ''', (buyer_id,))
            
            referrer_result = cursor.fetchone()
            if not referrer_result:
                return
            
            referrer_id = referrer_result[0]
            
            bonus = 0.5  # or order_amount * 0.1
            
            cursor.execute('''
                UPDATE referrals 
                SET bonus_earned = bonus_earned + ?
                WHERE referrer_id = ? AND referred_id = ?
            ''', (bonus, referrer_id, buyer_id))
            
            conn.commit()
    
    def get_available_balance(self, user_id: int) -> float:
        stats = self.get_user_referral_stats(user_id)
        return stats['available']