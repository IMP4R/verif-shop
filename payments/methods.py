import sqlite3
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from dirrrr import PROJECT_ROOT

PAYMENT_DB_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")

@dataclass
class Order:
    id: Optional[int] = None
    user_id: int = 0
    product_id: int = 0
    original_price: float = 0.0
    final_price: float = 0.0
    discount_percent: float = 0.0
    status: str = "pending"  # pending, paid, cancelled, completed
    payment_method: str = ""
    payment_id: str = ""
    created_at: Optional[str] = None
    paid_at: Optional[str] = None

@dataclass
class Subscription:
    id: Optional[int] = None
    user_id: int = 0
    plan_days: int = 1
    price: float = 0.0
    discount: float = 0.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: bool = True
    auto_renew: bool = False
    created_at: Optional[str] = None
    
    def check_active(self) -> bool: 
        if not self.is_active:
            return False
        if not self.end_date:
            return False
        
        end_date = datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
        return datetime.now() < end_date
    
    def days_until_expiry(self) -> int:
        if not self.end_date:
            return 0
        
        end_date = datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
        delta = end_date - datetime.now()
        return max(0, delta.days)


class PaymentMethodsDB:
    def __init__(self, db_file: str = PAYMENT_DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    original_price REAL NOT NULL,
                    final_price REAL NOT NULL,
                    discount_percent REAL DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    payment_method TEXT,
                    payment_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    order_id INTEGER,
                    type TEXT NOT NULL, -- 'product', 'subscription', 'ref_bonus'
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    status TEXT DEFAULT 'pending',
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    

    def create_order(self, user_id: int, product_id: int, 
                    original_price: float, final_price: float, 
                    discount_percent: float = 0) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (user_id, product_id, original_price, 
                                  final_price, discount_percent, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
            ''', (user_id, product_id, original_price, final_price, discount_percent))
            conn.commit()
            
            order_id = cursor.lastrowid
            
            
            return order_id


    def get_order(self, order_id: int) -> Optional[Order]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
            row = cursor.fetchone()
            
            if row:
                return Order(
                    id=row[0],
                    user_id=row[1],
                    product_id=row[2],
                    original_price=row[3],
                    final_price=row[4],
                    discount_percent=row[5],
                    status=row[6],
                    payment_method=row[7],
                    payment_id=row[8],
                    created_at=row[9],
                    paid_at=row[10]
                )
            return None


class SubscriptionMethodsDB:
    def __init__(self, db_file: str = PAYMENT_DB_FILE):
        self.db_file = db_file
        self.BASE_DISCOUNT = 20
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    plan_days INTEGER NOT NULL,
                    price REAL NOT NULL,
                    discount REAL NOT NULL,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    auto_renew INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    days INTEGER NOT NULL,
                    price REAL NOT NULL,
                    discount REAL NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            cursor.execute('SELECT COUNT(*) FROM subscription_plans')
            if cursor.fetchone()[0] == 0:
                plans = [
                    (1, 0.02, self.BASE_DISCOUNT),
                    (3, 25.0, self.BASE_DISCOUNT),
                    (6, 45.0, self.BASE_DISCOUNT)  
                ]
                cursor.executemany('INSERT INTO subscription_plans (days, price, discount) VALUES (?, ?, ?)', plans)
                conn.commit()
    
    def get_subscription_plans(self) -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT days, price, discount FROM subscription_plans WHERE is_active = 1 ORDER BY days')
            rows = cursor.fetchall()
            
            return [
                {'days': row[0], 'price': row[1], 'discount': row[2]}
                for row in rows
            ]
    
    def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM subscriptions 
                WHERE user_id = ? AND is_active = 1
                ORDER BY end_date DESC
                LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            
            if row:
                return Subscription(
                    id=row[0],
                    user_id=row[1],
                    plan_days=row[2],
                    price=row[3],
                    discount=row[4],
                    start_date=row[5],
                    end_date=row[6],
                    is_active=bool(row[7]),
                    auto_renew=bool(row[8]),
                    created_at=row[9]
                )
            return None
    
    def get_user_discount(self, user_id: int) -> float:
        subscription = self.get_user_subscription(user_id)
        if subscription and subscription.check_active():
            return subscription.discount
        return 0.0
    
    def create_subscription(self, user_id: int, plan_days: int, price: float) -> Optional[Subscription]:
        try:
            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT discount FROM subscription_plans WHERE days = ?', (plan_days,))
                plan = cursor.fetchone()
                
                if not plan:
                    return None
                
                discount = plan[0]
                start_date = datetime.now()
                end_date = start_date + timedelta(days=plan_days)
                
                cursor.execute('''
                    SELECT * FROM subscriptions 
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY end_date DESC
                    LIMIT 1
                ''', (user_id,))
                
                current_sub = cursor.fetchone()
                
                if current_sub:
                    current_end_date = datetime.strptime(current_sub[6], "%Y-%m-%d %H:%M:%S")
                    current_price = current_sub[3]
                    current_days = current_sub[2]
                    current_discount = current_sub[4]
                    
                    new_end_date = current_end_date + timedelta(days=plan_days)
                    new_price = current_price + price
                    new_days = current_days + plan_days
                    new_discount = max(discount, current_discount)
                    
                    cursor.execute('''
                        UPDATE subscriptions 
                        SET plan_days = ?,
                            price = ?,
                            discount = ?,
                            end_date = ?,
                            is_active = 1
                        WHERE id = ?
                    ''', (new_days, new_price, new_discount, 
                        new_end_date.strftime("%Y-%m-%d %H:%M:%S"),
                        current_sub[0]))
                    
                    subscription_id = current_sub[0]
                    
                else:
                    cursor.execute('''
                        INSERT INTO subscriptions (user_id, plan_days, price, discount, 
                                                start_date, end_date, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (user_id, plan_days, price, discount, 
                        start_date.strftime("%Y-%m-%d %H:%M:%S"),
                        end_date.strftime("%Y-%m-%d %H:%M:%S")))
                    
                    subscription_id = cursor.lastrowid
                
                conn.commit()
                
                cursor.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,))
                row = cursor.fetchone()
                
                if row:
                    return Subscription(
                        id=row[0],
                        user_id=row[1],
                        plan_days=row[2],
                        price=row[3],
                        discount=row[4],
                        start_date=row[5],
                        end_date=row[6],
                        is_active=bool(row[7]),
                        auto_renew=bool(row[8]),
                        created_at=row[9]
                    )
                return None
                
            finally:
                conn.close()
                
        except Exception as e:
            return None
        
    def create_manual_subscription(self, user_id: int, days: int, discount: float, price: float):
        try:
            conn = sqlite3.connect(self.db_file, timeout=30)
            cursor = conn.cursor()
            
            start_date = datetime.now()
            end_date = start_date + timedelta(days=days)
            
            cursor.execute('''
                SELECT * FROM subscriptions 
                WHERE user_id = ? AND is_active = 1
                ORDER BY end_date DESC
                LIMIT 1
            ''', (user_id,))
            
            current_sub = cursor.fetchone()
            
            if current_sub:
                current_end_date = datetime.strptime(current_sub[6], "%Y-%m-%d %H:%M:%S")
                current_price = current_sub[3]
                current_days = current_sub[2]
                current_discount = current_sub[4]
                
                new_end_date = current_end_date + timedelta(days=days)
                new_price = current_price + price
                new_days = current_days + days
                new_discount = max(discount, current_discount)
                
                cursor.execute('''
                    UPDATE subscriptions 
                    SET plan_days = ?,
                        price = ?,
                        discount = ?,
                        end_date = ?,
                        is_active = 1
                    WHERE id = ?
                ''', (new_days, new_price, new_discount, 
                    new_end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    current_sub[0]))
                
                subscription_id = current_sub[0]
                
            else:
                cursor.execute('''
                    INSERT INTO subscriptions (user_id, plan_days, price, discount, 
                                            start_date, end_date, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (user_id, days, price, discount, 
                    start_date.strftime("%Y-%m-%d %H:%M:%S"),
                    end_date.strftime("%Y-%m-%d %H:%M:%S")))
                
                subscription_id = cursor.lastrowid
            
            conn.commit()
            
            cursor.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,))
            row = cursor.fetchone()
            
            conn.close()
            
            if row:
                return Subscription(
                    id=row[0],
                    user_id=row[1],
                    plan_days=row[2],
                    price=row[3],
                    discount=row[4],
                    start_date=row[5],
                    end_date=row[6],
                    is_active=bool(row[7]),
                    auto_renew=bool(row[8]),
                    created_at=row[9]
                )
            return None
            
        except Exception as e:
            print(f"Error creating manual subscription: {e}")
            return None
    
    def get_active_subscriptions_count(self) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM subscriptions 
                WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP
            ''')
            return cursor.fetchone()[0] or 0
    
    def get_total_subscriptions_count(self) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM subscriptions')
            return cursor.fetchone()[0] or 0
            