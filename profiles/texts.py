TEXTS = {
    'ru': {
        'profile_title': '👤 <b>Профиль</b>\n\n🆔 ID: {user_id}\n📦 Заказов: {total_orders}\n💰 Потрачено: ${total_spent}',
        'premium_status_active': '⭐ <b>Premium активен!</b>\n🎯 Скидка: {discount}%\n📅 Действует до: {end_date}',
        'premium_status_inactive': '⭐ <b>Premium не активен</b>\n💡 Приобретите подписку для получения скидки!',
        'referral_stats': '👥 <b>Реферальная система</b>\n\n👤 Рефералов: {referrals_count}\n💰 Заработано: ${earned}\n💵 Доступно для вывода: <b>${available}</b>',
        'my_orders': '📦 Мои заказы',
        'referral_link': '🔗 Реферальная ссылка',
        'withdraw_funds': '💸 Вывести средства',
        'withdraw_title': '💸 <b>Вывод средств</b>\n\n💰 Доступно для вывода: <b>${available}</b>\n\nВыберите сумму для вывода:',
        'withdraw_10': '$10',
        'withdraw_20': '$20',
        'withdraw_custom': 'Другая сумма',
        'orders_title': '📦 <b>Мои заказы</b>\n\nПоследние 10 заказов:',
        'no_orders': '📭 У вас пока нет заказов',
        'back_to_profile': '⬅️ Назад в профиль',
        'back_to_menu': '🏠 В главное меню',

        'withdraw_custom_amount': '💸 <b>Другая сумма</b>\n\n💰 Доступно: <b>${available}</b>\n\nВведите сумму для вывода:',
        'withdraw_enter_details': '📝 <b>Введите реквизиты для выплаты ${amount}</b>\n\nУкажите, куда перевести средства:\n• Номер карты\n• Кошелек (USDT TRC20/ERC20)\n• Другие реквизиты',
        'withdraw_confirmation': '✅ <b>Подтвердите заявку на вывод</b>\n\n💰 Сумма: <b>${amount}</b>\n📝 Реквизиты: {details}\n\nПосле подтверждения заявка будет отправлена владельцу.',
        'withdraw_success': '✅ <b>Заявка на вывод создана!</b>\n\n💰 Сумма: <b>${amount}</b>\n\nЗаявка отправлена владельцу бота. Обычно выплаты производятся в течение 24 часов.',
        'withdraw_status_pending': '⏳ Ожидает',
        'withdraw_status_approved': '✅ Одобрена',
        'withdraw_status_rejected': '❌ Отклонена'
    },
    'en': {
        'profile_title': '👤 <b>Profile</b>\n\n🆔 ID: {user_id}\n📦 Orders: {total_orders}\n💰 Spent: ${total_spent}',
        'premium_status_active': '⭐ <b>Premium active!</b>\n🎯 Discount: {discount}%\n📅 Valid until: {end_date}',
        'premium_status_inactive': '⭐ <b>Premium not active</b>\n💡 Buy subscription to get discount!',
        'referral_stats': '👥 <b>Referral system</b>\n\n👤 Referrals: {referrals_count}\n💰 Earned: ${earned}\n💵 Available for withdrawal: <b>${available}</b>',
        'my_orders': '📦 My orders',
        'referral_link': '🔗 Referral link',
        'withdraw_funds': '💸 Withdraw funds',
        'withdraw_title': '💸 <b>Withdraw funds</b>\n\n💰 Available: <b>${available}</b>\n\nChoose amount to withdraw:',
        'withdraw_10': '$10',
        'withdraw_20': '$20',
        'withdraw_custom': 'Other amount',
        'orders_title': '📦 <b>My orders</b>\n\nLast 10 orders:',
        'no_orders': '📭 No orders yet',
        'back_to_profile': '⬅️ Back to profile',
        'back_to_menu': '🏠 Back to main',

        'withdraw_custom_amount': '💸 <b>Other amount</b>\n\n💰 Available: <b>${available}</b>\n\nEnter withdrawal amount:',
        'withdraw_enter_details': '📝 <b>Enter payment details for ${amount}</b>\n\nSpecify where to transfer funds:\n• Card number\n• Wallet (USDT TRC20/ERC20)\n• Other details',
        'withdraw_confirmation': '✅ <b>Confirm withdrawal request</b>\n\n💰 Amount: <b>${amount}</b>\n📝 Details: {details}\n\nAfter confirmation the request will be sent to the owner.',
        'withdraw_success': '✅ <b>Withdrawal request created!</b>\n\n💰 Amount: <b>${amount}</b>\n\nRequest sent to bot owner. Payouts are usually made within 24 hours.',
        'withdraw_status_pending': '⏳ Pending',
        'withdraw_status_approved': '✅ Approved',
        'withdraw_status_rejected': '❌ Rejected'
    }
}

def get_profile_text(text_key: str, language: str = 'ru', **kwargs) -> str:
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