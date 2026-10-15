import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from bot_instance import BotInstance
from handlers.start import router as start_router
from base.methods import router as base_router
from shop.handlers import router as shop_router
from admin.handlers import router as admin_router
from payments.handlers import router as payments_router
from profiles.handlers import router as profile_router
from settings.handlers import router as settings_router
from payments.cryptobot_handlers import router as cryptobot_router
from admin.broadcast import router as broadcast_router
from admin.manage_premium import router as manage_premium_router
from payments.subscription_expiry import start_subscription_checker
from dirrrr import PROJECT_ROOT
from admin.rules_instructions import router as rules_router
from admin.order_completion import router as order_completion_router

import os
import sqlite3
from dirrrr import PROJECT_ROOT

# ──────────────────────────────────────────────────────────────
# Один раз добавляем колонку delivery_instruction (безопасно)
# ──────────────────────────────────────────────────────────────
db_path = os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db")
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'delivery_instruction' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN delivery_instruction TEXT DEFAULT NULL")
        conn.commit()
        print("✅ Колонка delivery_instruction успешно добавлена")
    else:
        print("Колонка delivery_instruction уже существует")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    try:
        import sqlite3
        
        dbs = [
            os.path.join(os.path.dirname(PROJECT_ROOT), "base", "methods_data.db"),
            os.path.join(os.path.dirname(PROJECT_ROOT), "admin", "methods_data.db"),
            os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db"), 
            os.path.join(os.path.dirname(PROJECT_ROOT), "settings", "settings_data.db")
        ]
        
        logger.info("Инициализация баз данных...")
        for db_path in dbs:
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                conn.close()
                logger.info(f"База данных {db_path} инициализирована")
            except Exception as e:
                logger.error(f"Ошибка при инициализации {db_path}: {e}")

        BOT_TOKEN = os.getenv('BOT_TOKEN')
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN не найден")
        
        logger.info("Инициализация бота...")
        BotInstance.init(BOT_TOKEN)
        
        dp = BotInstance.get_dp()
        
        from middleware.antiflood import AntiFloodMiddleware
        antiflood_middleware = AntiFloodMiddleware(limit_period=0.5, block_duration=10.0)
        #dp.message.middleware(antiflood_middleware)
        dp.callback_query.middleware(antiflood_middleware)
        
        dp.include_router(start_router)
        dp.include_router(base_router)
        dp.include_router(shop_router)
        dp.include_router(payments_router)
        dp.include_router(profile_router)
        dp.include_router(settings_router)
        dp.include_router(admin_router)
        dp.include_router(cryptobot_router)
        dp.include_router(broadcast_router)
        dp.include_router(manage_premium_router)
        dp.include_router(rules_router)
        dp.include_router(order_completion_router)
        
        logger.info("Все роутеры подключены")

        from payments.cryptobot import cryptobot
        await cryptobot.start()
        logger.info("CryptoBot инициализирован")
        
        await start_subscription_checker()
        logger.info("Планировщик проверки Premium подписок запущен")

        from payments.ton_direct import ton_direct
        await ton_direct.start()
        logger.info("TonDirectPayments инициализирован")
        
        logger.info("Бот запускается...")
        await dp.start_polling(BotInstance.get_bot())
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}", exc_info=True)
        sys.exit(1)