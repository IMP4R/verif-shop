from config.languages import SUPPORTED_LANGUAGES

TEXTS = {
    'ru': {
        'settings_title': '⚙️ <b>Настройки</b>',
        'current_settings': '📋 <b>Текущие настройки:</b>\n\n🌐 Язык: {language}\n',#🔔 Уведомления: {notifications}',
        'change_language': '🌐 Сменить язык',
        'toggle_notifications': '🔔 Уведомления',
        'about_bot': 'ℹ️ О боте',
        'back_to_menu': '🏠 В главное меню',
        'back_to_settings': '⬅️ Назад в настройки',
        'back': '⬅️ Назад',
        
        'choose_language': '🌐 <b>Выберите язык:</b>',
        'language_changed': '✅ <b>Язык успешно изменен!</b>',
        
        'notifications_on': 'Включены',
        'notifications_off': 'Выключены',
        'notifications_toggled': '🔔 Уведомления {status}!',
        
        'about_title': 'ℹ️ <b>О боте Verif Shop</b>',
        'features': '🚀 <b>Возможности:</b>\n{features}',
        'feature_shop': 'Магазин с различными товарами',
        'feature_premium': 'Premium подписка со скидками',
        'feature_referrals': 'Реферальная система с выплатами',
        'feature_multilanguage': 'Поддержка нескольких языков',
        
        'bot_stats': '📊 <b>Статистика бота:</b>\n👥 Пользователей: {users}\n🛒 Товаров: {products}\n📦 Заказов: {orders}',
        'version': '📱 <b>Версия:</b> {version}',
        
        'contact_info': '📞 <b>Контактная информация:</b>\n\nПо вопросам сотрудничества и поддержки обращайтесь к администратору.',
        'contact_support': '💬 Написать в поддержку',
        
        'notification_types': '🔔 <b>Типы уведомлений:</b>\n\n• Новые товары\n• Акции и скидки\n• Обновления бота\n• Статус заказов',
        
        'privacy_title': '🔒 <b>Политика конфиденциальности</b>',
        'privacy_text': 'Мы уважаем вашу конфиденциальность. Все ваши данные используются исключительно для работы бота и не передаются третьим лицам.',
        
        'help_title': '❓ <b>Помощь</b>',
        'help_text': 'Если у вас возникли проблемы с использованием бота:\n\n1. Проверьте, подписаны ли вы на обязательный канал\n2. Убедитесь, что у вас стабильное интернет-соединение\n3. Перезапустите бота командой /start\n4. Если проблема не решена, обратитесь в поддержку'
    },
    'en': {
        'settings_title': '⚙️ <b>Settings</b>',
        'current_settings': '📋 <b>Current settings:</b>\n\n🌐 Language: {language}\n',#🔔 Notifications: {notifications}',
        'change_language': '🌐 Change language',
        'toggle_notifications': '🔔 Notifications',
        'about_bot': 'ℹ️ About bot',
        'back_to_menu': '🏠 Back to main',
        'back_to_settings': '⬅️ Back to settings',
        'back': '⬅️ Back',
        
        'choose_language': '🌐 <b>Choose language:</b>',
        'language_changed': '✅ <b>Language successfully changed!</b>',
        
        'notifications_on': 'Enabled',
        'notifications_off': 'Disabled',
        'notifications_toggled': '🔔 Notifications {status}!',
        
        'about_title': 'ℹ️ <b>About Verif Shop Bot</b>',
        'features': '🚀 <b>Features:</b>\n{features}',
        'feature_shop': 'Shop with various products',
        'feature_premium': 'Premium subscription with discounts',
        'feature_referrals': 'Referral system with payouts',
        'feature_multilanguage': 'Multi-language support',
        
        'bot_stats': '📊 <b>Bot statistics:</b>\n👥 Users: {users}\n🛒 Products: {products}\n📦 Orders: {orders}',
        'version': '📱 <b>Version:</b> {version}',
        
        'contact_info': '📞 <b>Contact information:</b>\n\nFor cooperation and support, contact the administrator.',
        'contact_support': '💬 Contact support',
        
        'notification_types': '🔔 <b>Notification types:</b>\n\n• New products\n• Sales and discounts\n• Bot updates\n• Order statuses',
        
        'privacy_title': '🔒 <b>Privacy Policy</b>',
        'privacy_text': 'We respect your privacy. All your data is used exclusively for the bot\'s operation and is not shared with third parties.',
        
        'help_title': '❓ <b>Help</b>',
        'help_text': 'If you have problems using the bot:\n\n1. Check if you are subscribed to the required channel\n2. Make sure you have a stable internet connection\n3. Restart the bot with the /start command\n4. If the problem persists, contact support'
    }
}


def get_settings_text(text_key: str, language: str = 'ru', **kwargs) -> str:
    if language in TEXTS and text_key in TEXTS[language]:
        text = TEXTS[language][text_key]
        if kwargs:
            return text.format(**kwargs)
        return text
    
    if text_key in TEXTS['ru']:
        text = TEXTS['ru'][text_key]
        if kwargs:
            return text.format(**kwargs)
        return text
    
    return f"[{text_key}]"


def get_language_name(language_code: str, target_language: str = 'ru') -> str:
    if language_code in SUPPORTED_LANGUAGES:
        lang_data = SUPPORTED_LANGUAGES[language_code]
        
        if target_language == 'ru':
            return lang_data['native']
        elif target_language == 'en':
            return lang_data['name']
    
    return language_code