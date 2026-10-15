from config.languages import SUPPORTED_LANGUAGES

TEXTS = {
    'ru': {
        'language_selection': 'Выберите язык / Choose your language:',
        'subscription_request': 'Для использования бота необходимо подписаться на канал:\n{channel}\n\nПосле подписки нажмите кнопку ниже:',
        'check_subscription_button': 'Я подписался',
        'not_subscribed_alert': 'Вы ещё не подписались на канал!',
        'welcome_message': 'Добро пожаловать! Вы в главном меню.',
        'main_menu_button': 'Главное меню'
    },
    'en': {
        'language_selection': 'Выберите язык / Choose your language:',
        'subscription_request': 'To use the bot, you need to subscribe to the channel:\n{channel}\n\nAfter subscribing, click the button below:',
        'check_subscription_button': 'I\'ve subscribed',
        'not_subscribed_alert': 'You haven\'t subscribed to the channel yet!',
        'welcome_message': 'Welcome! You are in the main menu.',
        'main_menu_button': 'Main Menu'
    }
}

def get_text(text_key: str, language: str = 'ru') -> str:
    if language in TEXTS and text_key in TEXTS[language]:
        return TEXTS[language][text_key]
    
    if text_key in TEXTS['ru']:
        return TEXTS['ru'][text_key]
    
    return f"[{text_key}]"