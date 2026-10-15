import os
import sqlite3
from typing import Dict, Any
from datetime import datetime
from dirrrr import PROJECT_ROOT

SETTINGS_DB_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "settings", "settings_data.db")


class SettingsMethodsDB:
    def __init__(self, db_file: str = SETTINGS_DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    notifications INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_user_settings_timestamp 
                AFTER UPDATE ON user_settings
                BEGIN
                    UPDATE user_settings 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = NEW.user_id;
                END;
            ''')
            
            conn.commit()
    
    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM user_settings WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone() is not None
            
            if not exists:
                cursor.execute('''
                    INSERT INTO user_settings (user_id, notifications)
                    VALUES (?, 1)
                ''', (user_id,))
                conn.commit()
                
                return {
                    'user_id': user_id,
                    'notifications': True,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            cursor.execute('''
                SELECT notifications, created_at, updated_at 
                FROM user_settings 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            
            return {
                'user_id': user_id,
                'notifications': bool(result[0]),
                'created_at': result[1],
                'updated_at': result[2]
            }
    
    def toggle_notifications(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT notifications FROM user_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                cursor.execute('''
                    INSERT INTO user_settings (user_id, notifications)
                    VALUES (?, 1)
                ''', (user_id,))
                conn.commit()
                return True
            
            current_status = bool(result[0])
            new_status = not current_status
            
            cursor.execute('''
                UPDATE user_settings 
                SET notifications = ?
                WHERE user_id = ?
            ''', (1 if new_status else 0, user_id))
            
            conn.commit()
            return new_status
    
    def set_notifications(self, user_id: int, status: bool) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT 1 FROM user_settings WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                cursor.execute('''
                    UPDATE user_settings 
                    SET notifications = ?
                    WHERE user_id = ?
                ''', (1 if status else 0, user_id))
            else:
                cursor.execute('''
                    INSERT INTO user_settings (user_id, notifications)
                    VALUES (?, ?)
                ''', (user_id, 1 if status else 0))
            
            conn.commit()
            return status
    
    def get_notification_status(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT notifications FROM user_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if result:
                return bool(result[0])
            
            cursor.execute('''
                INSERT INTO user_settings (user_id, notifications)
                VALUES (?, 1)
            ''', (user_id,))
            conn.commit()
            
            return True
    
    def get_bot_stats(self) -> Dict[str, Any]:
        stats = {
            'total_users': 0,
            'active_products': 0,
            'total_orders': 0,
            'active_subscriptions': 0
        }
        
        try:
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM user_languages")
                stats['total_users'] = cursor.fetchone()[0] or 0
            
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
                stats['active_products'] = cursor.fetchone()[0] or 0
            
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
                stats['total_orders'] = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1")
                stats['active_subscriptions'] = cursor.fetchone()[0] or 0
                
        except Exception as e:
            print(f"Error getting bot stats: {e}")
        
        return stats
    
    def get_user_activity(self, user_id: int) -> Dict[str, Any]:
        activity = {
            'last_login': None,
            'total_logins': 0,
            'orders_count': 0,
            'premium_active': False
        }
        
        # TODO: Добавить логирование активности при входе
        # Временно возвращаем базовые данные
        
        try:
            with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id = ?", (user_id,))
                activity['orders_count'] = cursor.fetchone()[0] or 0
                
                cursor.execute('''
                    SELECT 1 FROM subscriptions 
                    WHERE user_id = ? AND is_active = 1
                ''', (user_id,))
                activity['premium_active'] = cursor.fetchone() is not None
                
        except Exception as e:
            print(f"Error getting user activity: {e}")
        
        return activity