TEXTS = {
    'ru': {
        'buy_product': '📦 <b>{name}</b>\n\n📝 <b>Описание:</b>\n{description}\n\n💰 <b>Цена:</b> ${original_price}\n🎯 <b>Ваша скидка:</b> {discount}%\n💵 <b>Итого к оплате:</b> <b>${final_price}</b>',
        'premium_info': '⭐ <b>Premium Подписка</b>\n\n🚀 <b>Преимущества:</b>\n✅ Скидка {discount}% на все товары\n✅ Приоритетная поддержка\n✅ Эксклюзивные предложения\n\n🎯 <b>Выберите тариф:</b>',
        'premium_active': '⭐ <b>Ваша Premium Подписка активна!</b>\n\n✅ <b>Скидка:</b> {discount}%\n📅 <b>Действует до:</b> {until}\n⏳ <b>Осталось дней:</b> {days_left}\n\n🎯 <b>Хотите продлить?</b>',
        'premium_plan': '{days} дней - ${price}',
        'pay_cryptobot': '💳 Оплатить через CryptoBot',
        'pay_tonkeeper': '💳 Оплатить через Tonkeeper',
        'crypto_payment': '💳 <b>Оплата через CryptoBot</b>\n\nСсылка для оплаты: {url}\n\nПосле оплаты нажмите кнопку "Проверить оплату"',
        'open_payment_link': '🔗 Открыть ссылку для оплаты',
        'check_payment': '✅ Проверить оплату',
        'payment_success': '✅ <b>Оплата успешно завершена!</b>\n\n🛒 <b>Ваш заказ:</b> {product_name}\n💰 <b>Сумма:</b> ${amount}\n🎯 <b>Скидка:</b> {discount}%\n\n📦 Для получения товара перейдите по ссылке:',
        'renew_premium': '🔄 Продлить Premium',
        'product_unavailable': '❌ Товар временно недоступен',
        'back': '⬅️ Назад',
        'back_to_menu': '🏠 В главное меню',
        'subscription_expired': '⚠️ <b>Ваша Premium подписка истекла!</b>\n\n'
                               '📅 Дата окончания: {end_date}\n'
                               '🎯 Скидка {discount}% больше не действует\n\n'
                               '🔄 Чтобы снова получать скидки, продлите подписку в разделе Premium',
        
        'subscription_expiring_3days': '⏳ <b>Ваша Premium подписка скоро истекает!</b>\n\n'
                                      '📅 Действует до: {end_date}\n'
                                      '⏰ Осталось дней: 3\n'
                                      '🔄 Чтобы продолжить получать скидки, продлите подписку нажав на Premium в меню',
        
        'subscription_expiring_1day': '⏳ <b>Ваша Premium подписка заканчивается завтра!</b>\n\n'
                                     '📅 Действует до: {end_date}\n'
                                     '🔄 Срочно продлите подписку чтобы не потерять скидки!',

        'crypto_payment_created': '💳 <b>CryptoBot платеж создан</b>\n\n💰 Сумма: {amount} {currency}\n🔗 Ссылка для оплаты: {url}\n\n⚠️ Ссылка действительна 30 минут',
        'premium_payment_created': '⭐ <b>Оплата Premium подписки</b>\n\n📅 Срок: {days} дней\n💰 Сумма: {price} USDT\n🔗 Ссылка для оплаты: {url}',
        'payment_success': '✅ Оплата успешно получена!\n\nСпасибо за покупку! Ваш товар готов к выдаче.',
        'payment_pending': '⏳ Платеж ожидает оплаты',
        'payment_expired': '❌ Срок оплаты истек',
        'payment_not_found': '❌ Платеж не найден',
        'payment_error': '❌ Ошибка при создании платежа',
        'order_not_found': '❌ Заказ не найден',
        'plan_not_found': '❌ Тарифный план не найден',
        'check_payment_status': '🔄 Проверить статус оплаты',
        'check_premium_payment': '🔄 Проверить статус подписки',
        'get_product': '📦 Получить товар',
        'back_to_shop': '🛒 Вернуться в магазин',
        'back_to_premium': '⭐ Вернуться к Premium',
        'open_payment_link': '🔗 Открыть ссылку для оплаты',

        'tonkeeper_payment': '💳 <b>Оплата через Tonkeeper</b>\n\nСумма: ${amount} TON\nКомментарий (обязательно укажите!): <code>{comment}</code>\nСсылка: {url}\n\nПерейдите по ссылке, вставьте комментарий и подтвердите.',
        'tonkeeper_payment_title': '💳 Оплата через Tonkeeper',
        'tonkeeper_amount': 'Сумма: <b>{ton_amount:.3f} TON</b> ≈ ${usd_amount:.3f}',
        'tonkeeper_comment_label': 'Комментарий (обязательно!):',
        'tonkeeper_instruction': 'Отсканируйте QR-код ниже\nили нажмите кнопку «Открыть в Tonkeeper»',
        'tonkeeper_warning': '<i>Не меняйте и не удаляйте комментарий — иначе платёж не засчитается!</i>',

        'buy_premium': '⭐ <b>Покупка Premium подписки</b>\n\n'
                      '📅 Срок: {days} дней\n'
                      '💰 Цена: ${price}\n'
                      '🎯 Скидка: {discount}%\n\n'
                      'Выберите способ оплаты:',
        'premium_payment': '💳 <b>Оплата Premium подписки</b>\n\n'
                          '💰 Сумма: ${amount}\n'
                          '🔗 Ссылка для оплаты: {url}\n\n'
                          '⚠️ Ссылка действительна 30 минут',
        'plan_not_found': '❌ Тарифный план не найден',
    },
    'en': {
        'buy_product': '📦 <b>{name}</b>\n\n📝 <b>Description:</b>\n{description}\n\n💰 <b>Price:</b> ${original_price}\n🎯 <b>Your discount:</b> {discount}%\n💵 <b>Total:</b> <b>${final_price}</b>',
        'premium_info': '⭐ <b>Premium Subscription</b>\n\n🚀 <b>Benefits:</b>\n✅ {discount}% discount on all products\n✅ Priority support\n✅ Exclusive offers\n\n🎯 <b>Choose plan:</b>',
        'premium_active': '⭐ <b>Your Premium Subscription is active!</b>\n\n✅ <b>Discount:</b> {discount}%\n📅 <b>Valid until:</b> {until}\n⏳ <b>Days left:</b> {days_left}\n\n🎯 <b>Want to renew?</b>',
        'premium_plan': '{days} day(s) - ${price}',
        'pay_cryptobot': '💳 Pay via CryptoBot',
        'pay_tonkeeper': '💳 Pay via Tonkeeper',
        'crypto_payment': '💳 <b>Payment via CryptoBot</b>\n\nPayment link: {url}\n\nAfter payment click "Check payment" button',
        'open_payment_link': '🔗 Open payment link',
        'check_payment': '✅ Check payment',
        'payment_success': '✅ <b>Payment successful!</b>\n\n🛒 <b>Your order:</b> {product_name}\n💰 <b>Amount:</b> ${amount}\n🎯 <b>Discount:</b> {discount}%\n\n📦 For receiving product follow the link:',
        'renew_premium': '🔄 Renew Premium',
        'product_unavailable': '❌ Product temporarily unavailable',
        'back': '⬅️ Back',
        'back_to_menu': '🏠 Back to main',
        'subscription_expired': '⚠️ <b>Your Premium subscription has expired!</b>\n\n'
                               '📅 End date: {end_date}\n'
                               '🎯 {discount}% discount is no longer active\n\n'
                               '🔄 To get discounts again, renew your subscription in the Premium section',
        
        'subscription_expiring_3days': '⏳ <b>Your Premium subscription is expiring soon!</b>\n\n'
                                      '📅 Valid until: {end_date}\n'
                                      '⏰ Days left: 3\n'
                                      '🔄 To continue receiving discounts, renew your subscription by clicking Premium in the menu',
        
        'subscription_expiring_1day': '⏳ <b>Your Premium subscription ends tomorrow!</b>\n\n'
                                     '📅 Valid until: {end_date}\n'
                                     '🔄 Renew your subscription urgently to not lose your discounts!',

        'crypto_payment_created': '💳 <b>CryptoBot payment created</b>\n\n💰 Amount: {amount} {currency}\n🔗 Payment link: {url}\n\n⚠️ Link is valid for 30 minutes',
        'premium_payment_created': '⭐ <b>Premium subscription payment</b>\n\n📅 Term: {days} day(s)\n💰 Amount: {price} USDT\n🔗 Payment link: {url}',
        'payment_success': '✅ Payment received successfully!\n\nThank you for your purchase! Your product is ready.',
        'payment_pending': '⏳ Payment is pending',
        'payment_expired': '❌ Payment expired',
        'payment_not_found': '❌ Payment not found',
        'payment_error': '❌ Error creating payment',
        'order_not_found': '❌ Order not found',
        'plan_not_found': '❌ Plan not found',
        'check_payment_status': '🔄 Check payment status',
        'check_premium_payment': '🔄 Check subscription status',
        'get_product': '📦 Get product',
        'back_to_shop': '🛒 Back to shop',
        'back_to_premium': '⭐ Back to Premium',
        'open_payment_link': '🔗 Open payment link',

        'tonkeeper_payment': '💳 <b>Payment via Tonkeeper</b>\n\nAmount: ${amount} TON\nComment (required!): <code>{comment}</code>\nLink: {url}\n\nFollow the link, paste comment and confirm.',
        'tonkeeper_payment_title': '💳 Payment via Tonkeeper',
        'tonkeeper_amount': 'Amount: <b>{ton_amount:.3f} TON</b> ≈ ${usd_amount:.3f}',
        'tonkeeper_comment_label': 'Comment (required!):',
        'tonkeeper_instruction': 'Scan the QR code below\nor tap the "Open in Tonkeeper" button',
        'tonkeeper_warning': '<i>Do not change or remove the comment — otherwise the payment won’t be credited!</i>',

        'buy_premium': '⭐ <b>Buy Premium subscription</b>\n\n'
                      '📅 Term: {days} days\n'
                      '💰 Price: ${price}\n'
                      '🎯 Discount: {discount}%\n\n'
                      'Choose payment method:',
        'premium_payment': '💳 <b>Premium subscription payment</b>\n\n'
                          '💰 Amount: ${amount}\n'
                          '🔗 Payment link: {url}\n\n'
                          '⚠️ Link is valid for 30 minutes',
        'plan_not_found': '❌ Plan not found',
    }
}

def get_payment_text(text_key: str, language: str = 'ru', **kwargs) -> str:
    try:
        from admin.methods import TextEditorMethodsDB
        text_editor_db = TextEditorMethodsDB()
        custom_text = text_editor_db.get_text('payment', text_key, language)
        if custom_text:
            if kwargs:
                return custom_text.format(**kwargs)
            return custom_text
    except:
        pass
    if language in TEXTS and text_key in TEXTS[language]:
        text = TEXTS[language][text_key]
        if kwargs:
            return text.format(**kwargs)
        return text
    
    return f"[{text_key}]"