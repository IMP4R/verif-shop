import os
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from dirrrr import PROJECT_ROOT

class WithdrawalMethodsDB:
    def __init__(self, db_file: str = os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")):
        self.db_file = db_file
    
    def create_withdrawal_request(self, user_id: int, amount: float, details: str):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO referral_withdrawals (user_id, amount, details, status)
                VALUES (?, ?, ?, 'pending')
            ''', (user_id, amount, details))
            conn.commit()
    
    def get_user_withdrawals(self, user_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM referral_withdrawals 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                LIMIT 20
            ''', (user_id,))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'amount': row[2],
                    'status': row[3],
                    'details': row[4],
                    'admin_notes': row[5],
                    'created_at': row[6],
                    'processed_at': row[7]
                }
                for row in rows
            ]
    
    def get_withdrawal_requests(self, status: str = 'pending') -> List[Dict]:
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM referral_withdrawals 
                WHERE status = ? 
                ORDER BY created_at DESC
            ''', (status,))
            
            rows = cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'amount': row[2],
                    'status': row[3],
                    'details': row[4],
                    'admin_notes': row[5],
                    'created_at': row[6],
                    'processed_at': row[7]
                }
                for row in rows
            ]
    
    def update_withdrawal_status(self, withdrawal_id: int, status: str, admin_notes: str = ""):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE referral_withdrawals 
                SET status = ?, 
                    admin_notes = ?,
                    processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, admin_notes, withdrawal_id))
            conn.commit()