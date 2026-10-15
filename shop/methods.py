import os
import sqlite3
from typing import List, Optional
from .product import Product
from dirrrr import PROJECT_ROOT

DB_FILE = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")

class ProductMethodsDB:
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    price REAL NOT NULL,
                    category TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            default_cats = ["Биржи", "Кошельки", "Букмекерские"]
            
            for cat in default_cats:
                cursor.execute("SELECT 1 FROM products WHERE category = ? LIMIT 1", (cat,))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO products (name, description, price, category, is_active)
                        VALUES (?, ?, ?, ?, 0)
                    ''', (f"[Категория: {cat}]", "Служебная запись", 0.0, cat))
            
            conn.commit()
    
    def add_product(self, name: str, description: str, price: float, category: str) -> int:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO products (name, description, price, category)
                VALUES (?, ?, ?, ?)
            ''', (name, description, price, category))
            conn.commit()
            return cursor.lastrowid
    
    def get_product(self, product_id: int) -> Optional[Product]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            
            if row:
                return Product(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    price=row[3],
                    category=row[4],
                    is_active=bool(row[5]),
                    created_at=row[6]
                )
        return None
    
    def get_all_products(self) -> List[Product]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM products WHERE is_active = 1 ORDER BY id DESC')
            rows = cursor.fetchall()
            
            products = []
            for row in rows:
                products.append(Product(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    price=row[3],
                    category=row[4],
                    is_active=bool(row[5]),
                    created_at=row[6]
                ))
            return products
    
    def get_products_by_category(self, category: str) -> List[Product]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM products 
                WHERE category = ? AND is_active = 1 
                ORDER BY id DESC
            ''', (category,))
            rows = cursor.fetchall()
            
            products = []
            for row in rows:
                products.append(Product(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    price=row[3],
                    category=row[4],
                    is_active=bool(row[5]),
                    created_at=row[6]
                ))
            return products
    
    def get_all_categories(self) -> List[str]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT category FROM products 
                WHERE is_active = 1 
                ORDER BY category
            ''')
            rows = cursor.fetchall()
            return [row[0] for row in rows]
    
    def has_active_products_in_category(self, category: str) -> bool:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM products 
                WHERE category = ? AND is_active = 1
            ''', (category,))
            result = cursor.fetchone()
            return result[0] > 0 if result else False
    
    def update_product(self, product_id: int, **kwargs):
        allowed_fields = ['name', 'description', 'price', 'category', 'is_active']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return
        
        values.append(product_id)
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, tuple(values))
            conn.commit()
    
    def delete_product(self, product_id: int):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE products SET is_active = 0 WHERE id = ?', (product_id,))
            conn.commit()

