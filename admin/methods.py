import os
import sqlite3
from typing import List, Dict, Any
from shop.product import Product
from dirrrr import PROJECT_ROOT

DB_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")

class AdminMethodsDB:
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
    
    def get_total_users(self) -> int:
        with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db")) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_languages")
            return cursor.fetchone()[0]
    
    def get_total_products(self) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            return cursor.fetchone()[0]
    
    def get_active_products(self) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
            return cursor.fetchone()[0]
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        # TODO: Реализовать таблицу заказов
        return []
    

#tovary    
    def get_all_products_admin(self) -> List[Product]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, description, price, category, is_active, created_at, 
                       delivery_instruction 
                FROM products ORDER BY id DESC
            ''')
            rows = cursor.fetchall()
           
            return [
                Product(
                    id=row[0], name=row[1], description=row[2], price=row[3],
                    category=row[4], is_active=bool(row[5]), created_at=row[6],
                    delivery_instruction=row[7]
                )
                for row in rows
            ]

    def get_product_by_id(self, product_id: int):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, description, price, category, is_active, created_at, 
                       delivery_instruction 
                FROM products WHERE id = ?
            ''', (product_id,))
            row = cursor.fetchone()
           
            if row:
                return Product(
                    id=row[0], name=row[1], description=row[2], price=row[3],
                    category=row[4], is_active=bool(row[5]), created_at=row[6],
                    delivery_instruction=row[7]
                )
            return None
    
    def toggle_product_active(self, product_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM products WHERE id = ?', (product_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            new_status = 0 if result[0] else 1
            cursor.execute('UPDATE products SET is_active = ? WHERE id = ?', (new_status, product_id))
            conn.commit()
            return True
    
    def get_product_categories(self) -> List[str]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT category FROM products ORDER BY category')
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        
    def delete_product_permanently(self, product_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            conn.commit()
            return cursor.rowcount > 0
        
import sqlite3
from typing import Dict, Any

class DeliveryMethodsDB:
    def __init__(self, db_file: str = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS delivery_settings (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    bot_username TEXT DEFAULT '',
                    delivery_link TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT single_row CHECK (id = 1)
                )
            ''')
            
            cursor.execute('SELECT COUNT(*) FROM delivery_settings')
            if cursor.fetchone()[0] == 0:
                cursor.execute('''
                    INSERT INTO delivery_settings (bot_username, delivery_link)
                    VALUES ('', '')
                ''')
            conn.commit()
    
    def get_delivery_settings(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT bot_username, delivery_link FROM delivery_settings WHERE id = 1')
            result = cursor.fetchone()
            return {
                'bot_username': result[0] if result else '',
                'delivery_link': result[1] if result else ''
            }
    
    def update_delivery_bot(self, bot_username: str) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE delivery_settings 
                SET bot_username = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (bot_username,))
            conn.commit()
            return cursor.rowcount > 0
    
    def update_delivery_link(self, delivery_link: str) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE delivery_settings 
                SET delivery_link = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (delivery_link,))
            conn.commit()
            return cursor.rowcount > 0
        
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import csv
import io

class StatisticsMethodsDB:
    def __init__(self):
        self.users_db = os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db")
        self.payments_db = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")
        self.admin_db = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")
    
    def get_bot_statistics(self) -> Dict[str, Any]:
        stats = {}
        
        try:
            with sqlite3.connect(self.users_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM user_languages")
                stats['total_users'] = cursor.fetchone()[0] or 0
            
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) FROM orders 
                    WHERE created_at >= ? OR status = 'paid'
                ''', (thirty_days_ago,))
                stats['active_users'] = cursor.fetchone()[0] or 0
            
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
                stats['total_orders'] = cursor.fetchone()[0] or 0
            
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(final_price) FROM orders WHERE status = 'paid'")
                revenue = cursor.fetchone()[0]
                stats['total_revenue'] = float(revenue) if revenue else 0.0
            
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM subscriptions 
                    WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP
                ''')
                stats['active_subscriptions'] = cursor.fetchone()[0] or 0
            
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(rw.amount) 
                    FROM referral_withdrawals rw
                    WHERE rw.status = 'pending'
                ''')
                pending = cursor.fetchone()[0]
                stats['available_balance'] = float(pending) if pending else 0.0
            
            stats['sales_by_day'] = self.get_sales_by_day(7)
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
        
        return stats
    
    def get_sales_by_day(self, days: int = 7) -> List[Dict]:
        sales = []
        try:
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DATE(created_at) as date, 
                           COUNT(*) as orders,
                           SUM(final_price) as revenue
                    FROM orders 
                    WHERE status = 'paid' 
                    AND created_at >= date('now', ? || ' days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                ''', (f'-{days}',))
                
                for row in cursor.fetchall():
                    sales.append({
                        'date': row[0],
                        'orders': row[1],
                        'revenue': row[2] if row[2] else 0.0
                    })
        except Exception as e:
            print(f"Error getting sales by day: {e}")
        
        return sales
    
    def generate_report(self, start_date: str, end_date: str) -> Optional[io.StringIO]:
        try:
            with sqlite3.connect(self.payments_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT o.id, o.user_id, o.product_id, o.final_price, 
                           o.discount_percent, o.status, o.created_at,
                           p.name as product_name
                    FROM orders o
                    LEFT JOIN admin.methods_data.products p ON o.product_id = p.id
                    WHERE o.created_at BETWEEN ? AND ?
                    ORDER BY o.created_at DESC
                ''', (start_date, end_date))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return None
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                writer.writerow(['ID заказа', 'ID пользователя', 'ID товара', 
                                'Название товара', 'Сумма', 'Скидка %', 
                                'Статус', 'Дата создания'])
                
                for row in rows:
                    writer.writerow([
                        row[0], row[1], row[2], row[7] if row[7] else 'N/A',
                        row[3], row[4], row[5], row[6]
                    ])
                
                output.seek(0)
                return output
                
        except Exception as e:
            print(f"Error generating report: {e}")
            return None


class TextEditorMethodsDB:
    def __init__(self, db_file: str = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_texts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    text_key TEXT NOT NULL,
                    language TEXT NOT NULL,
                    text_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, text_key, language)
                )
            ''')
            conn.commit()
    
    def get_categories(self) -> List[str]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT category FROM custom_texts ORDER BY category')
            return [row[0] for row in cursor.fetchall()]
    
    def get_texts_by_category(self, category: str, language: str = 'ru') -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT text_key, text_value FROM custom_texts
                WHERE category = ? AND language = ?
            ''', (category, language))
            custom = {row[0]: row[1] for row in cursor.fetchall()}

        # Берём дефолтные тексты
        from shop.texts import TEXTS as SHOP_TEXTS
        from payments.texts import TEXTS as PAYMENT_TEXTS
        from profiles.texts import TEXTS as PROFILE_TEXTS
        from settings.texts import TEXTS as SETTINGS_TEXTS
        from .texts import TEXTS as ADMIN_TEXTS

        sources = {
            'shop': SHOP_TEXTS, 'payment': PAYMENT_TEXTS, 'premium': PAYMENT_TEXTS,
            'profile': PROFILE_TEXTS, 'settings': SETTINGS_TEXTS, 'admin': ADMIN_TEXTS
        }
        source = sources.get(category, {}).get(language, sources.get(category, {}).get('ru', {}))

        return [
            {'key': k, 'value': custom.get(k, v)}
            for k, v in source.items()
        ]
    
    def save_text(self, category: str, text_key: str, language: str, text_value: str) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO custom_texts (category, text_key, language, text_value, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (category, text_key, language, text_value))
            conn.commit()
            return True
    
    def get_text(self, category: str, text_key: str, language: str) -> Optional[str]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT text_value FROM custom_texts 
                WHERE category = ? AND text_key = ? AND language = ?
            ''', (category, text_key, language))
            result = cursor.fetchone()
            return result[0] if result else None
        
import sqlite3
from typing import List, Dict, Optional

class RulesAndInstructionsDB:
    def __init__(self, db_file: str = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            # Таблица правил перед оплатой (ссылки на Telegraph)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pre_payment_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, 
                    telegraph_url TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица инструкций после оплаты
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS post_payment_instructions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    instruction_text TEXT NOT NULL,
                    delivery_bot_username TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица отзывов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rating INTEGER DEFAULT 5,
                    review_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                )
            ''')
            
            conn.commit()
    
    # ===== МЕТОДЫ ДЛЯ ПРАВИЛ =====
    def add_pre_payment_rule(self, name: str, telegraph_url: str) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pre_payment_rules (name, telegraph_url)
                VALUES (?, ?)
            ''', (name, telegraph_url))
            conn.commit()
            return cursor.lastrowid
    
    def get_pre_payment_rules(self) -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, telegraph_url, is_active FROM pre_payment_rules ORDER BY id DESC')
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'telegraph_url': row[2],
                    'is_active': bool(row[3])
                }
                for row in rows
            ]
    
    def get_active_pre_payment_rule(self) -> Optional[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, telegraph_url FROM pre_payment_rules 
                WHERE is_active = 1 ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'telegraph_url': row[2]
                }
            return None
    
    def toggle_rule_active(self, rule_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM pre_payment_rules WHERE id = ?', (rule_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            new_status = 0 if result[0] else 1
            cursor.execute('UPDATE pre_payment_rules SET is_active = ? WHERE id = ?', (new_status, rule_id))
            conn.commit()
            return True
    
    def delete_rule(self, rule_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pre_payment_rules WHERE id = ?', (rule_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_post_payment_instruction(self, name: str, instruction_text: str, delivery_bot_username: str = "") -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO post_payment_instructions (name, instruction_text, delivery_bot_username)
                VALUES (?, ?, ?)
            ''', (name, instruction_text, delivery_bot_username))
            conn.commit()
            return cursor.lastrowid
    
    def get_post_payment_instructions(self) -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, instruction_text, delivery_bot_username, is_active FROM post_payment_instructions ORDER BY id DESC')
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'instruction_text': row[2],
                    'delivery_bot_username': row[3],
                    'is_active': bool(row[4])
                }
                for row in rows
            ]
    
    def get_active_post_payment_instruction(self) -> Optional[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, instruction_text, delivery_bot_username 
                FROM post_payment_instructions 
                WHERE is_active = 1 ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'instruction_text': row[2],
                    'delivery_bot_username': row[3]
                }
            return None
    
    def toggle_instruction_active(self, instruction_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active FROM post_payment_instructions WHERE id = ?', (instruction_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            new_status = 0 if result[0] else 1
            cursor.execute('UPDATE post_payment_instructions SET is_active = ? WHERE id = ?', (new_status, instruction_id))
            conn.commit()
            return True
    
    def delete_instruction(self, instruction_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM post_payment_instructions WHERE id = ?', (instruction_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_review(self, order_id: int, user_id: int, rating: int, review_text: str = "") -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO order_reviews (order_id, user_id, rating, review_text)
                VALUES (?, ?, ?, ?)
            ''', (order_id, user_id, rating, review_text))
            conn.commit()
            return cursor.lastrowid
    
    def get_order_reviews(self, order_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, user_id, rating, review_text, created_at FROM order_reviews WHERE order_id = ? ORDER BY created_at DESC', (order_id,))
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'rating': row[2],
                    'review_text': row[3],
                    'created_at': row[4]
                }
                for row in rows
            ]

rules_db = RulesAndInstructionsDB()