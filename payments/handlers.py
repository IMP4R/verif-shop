from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from dirrrr import PROJECT_ROOT
from base.methods import get_user_language
from payments.methods import PaymentMethodsDB, SubscriptionMethodsDB
from payments.texts import get_payment_text
from shop.methods import ProductMethodsDB
from payments.cryptobot import cryptobot
import sqlite3

router = Router()
payment_db = PaymentMethodsDB()
subscription_db = SubscriptionMethodsDB()
product_db = ProductMethodsDB()

from admin.methods import RulesAndInstructionsDB  # Добавить импорт

rules_db = RulesAndInstructionsDB()  # Добавить после других db


@router.callback_query(F.data.startswith("buy_"))
async def handle_buy_product(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    product_id = int(callback.data.split("_")[1])
    
    product = product_db.get_product(product_id)
    if not product or not product.is_active:
        await callback.answer(get_payment_text('product_unavailable', language))
        return
    
    user_discount = subscription_db.get_user_discount(user_id)
    final_price = product.price * (1 - user_discount / 100) if user_discount else product.price
    
    order_id = payment_db.create_order(user_id, product_id, product.price, final_price, user_discount)
    
    # Получаем активные правила
    active_rule = rules_db.get_active_pre_payment_rule()
    
    text = get_payment_text('buy_product', language).format(
        name=product.name,
        description=product.description,
        original_price=product.price,
        discount=user_discount if user_discount else 0,
        final_price=final_price
    )
    
    # Добавляем предупреждение о правилах
    text += "\n\n⚠️ <b>Перед оплатой ознакомьтесь с правилами!</b>"
    text += "\nПокупка означает ваше согласие с ними."
    
    buttons = []
    
    # Добавляем кнопку с правилами, если они есть
    if active_rule:
        buttons.append([
            InlineKeyboardButton(
                text="📋 Ознакомиться с правилами", 
                url=active_rule['telegraph_url']
            )
        ])
    
    # Кнопки оплаты
    buttons.append([
        InlineKeyboardButton(text=get_payment_text('pay_cryptobot', language), callback_data=f"pay_crypto_{order_id}"),
        InlineKeyboardButton(text=get_payment_text('pay_tonkeeper', language), callback_data=f"pay_tonkeeper_{order_id}")
    ])
    
    buttons.append([
        InlineKeyboardButton(text=get_payment_text('back', language), callback_data=f"product_{product_id}")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "premium_info")
async def handle_premium_info(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    subscription = subscription_db.get_user_subscription(user_id)
    
    if subscription and subscription.check_active():
        text = get_payment_text('premium_active', language).format(
            discount=subscription.discount,
            until=subscription.end_date,
            days_left=subscription.days_until_expiry()
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_payment_text('renew_premium', language), callback_data="renew_premium")],
            [InlineKeyboardButton(text=get_payment_text('back_to_menu', language), callback_data="main_menu")]
        ])
    else:
        text = get_payment_text('premium_info', language).format(
            discount=subscription_db.BASE_DISCOUNT
        )
        
        plans = subscription_db.get_subscription_plans()
        buttons = []
        
        for plan in plans:
            button_text = get_payment_text('premium_plan', language).format(
                days=plan['days'],
                price=plan['price'],
                discount=plan['discount']
            )
            buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"premium_buy_{plan['days']}")])
        
        buttons.append([InlineKeyboardButton(text=get_payment_text('back_to_menu', language), callback_data="main_menu")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.reply(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.message.delete()


@router.callback_query(F.data.startswith("pay_crypto_"))
async def handle_crypto_payment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    order_id = int(callback.data.split("_")[2])
    
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT final_price FROM orders WHERE id = ?', (order_id,))
        result = cursor.fetchone()
        
        if not result:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        amount = result[0]
    
    invoice_data = await cryptobot.create_invoice(
        order_id=order_id,
        user_id=user_id,
        amount=float(amount),
        description=f"Order #{order_id}"
    )
    
    if not invoice_data:
        await callback.answer("Ошибка при создании платежа", show_alert=True)
        return
    
    payment_url = invoice_data['pay_url']
    
    text = get_payment_text('crypto_payment', language).format(url=payment_url)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_payment_text('open_payment_link', language), url=payment_url)],
        [InlineKeyboardButton(text=get_payment_text('check_payment', language), callback_data=f"check_crypto_{order_id}")],
        [InlineKeyboardButton(text=get_payment_text('back', language), callback_data=f"order_{order_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("check_crypto_"))
async def handle_check_crypto(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    order_id = int(callback.data.split("_")[2])
    
    status = await cryptobot.check_order_payment(order_id)
    
    if status == 'paid':
        await callback.answer("✅ Оплата получена!", show_alert=True)
        
        text = "✅ <b>Оплата успешно получена!</b>\n\n"
        text += "Спасибо за покупку!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Вернуться в магазин", callback_data="shop_m")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    elif status == 'active':
        await callback.answer("⏳ Ожидание оплаты...", show_alert=True)
    elif status == 'expired':
        await callback.answer("❌ Срок оплаты истек", show_alert=True)
    else:
        await callback.answer("❌ Платеж не найден", show_alert=True)


@router.callback_query(F.data.startswith("premium_buy_"))
async def handle_premium_buy(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    try:
        if callback.data == "premium_buy":
            await handle_premium_info(callback, state)
            return
        
        days = int(callback.data.split("_")[2])
        
        plans = subscription_db.get_subscription_plans()
        plan_data = next((p for p in plans if p['days'] == days), None)
        
        if not plan_data:
            await callback.answer(get_payment_text('plan_not_found', language), show_alert=True)
            return
        
        price = plan_data['price']
        discount = plan_data['discount']
        days = plan_data['days'] 
        
        order_id = payment_db.create_order(
            user_id=user_id,
            product_id=-days,
            original_price=price,
            final_price=price,
            discount_percent=0
        )
        
        text = get_payment_text('buy_premium', language).format(
            days=days,
            price=price,
            discount=discount
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_payment_text('pay_cryptobot', language), callback_data=f"pay_premium_crypto_{order_id}")],
            [InlineKeyboardButton(text=get_payment_text('pay_tonkeeper', language), callback_data=f"pay_tonkeeper_{order_id}")],
            [InlineKeyboardButton(text=get_payment_text('back', language), callback_data="premium_info")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except:
            await callback.message.reply(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.message.delete()
        
    except Exception as e:
        print(f"Error in premium_buy: {e}")
        await callback.answer("Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("pay_premium_crypto_"))
async def handle_premium_crypto_payment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    order_id = int(callback.data.split("_")[3])
    
    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT final_price FROM orders WHERE id = ?', (order_id,))
        result = cursor.fetchone()
        
        if not result:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        amount = result[0]
    
    invoice_data = await cryptobot.create_invoice(
        order_id=order_id,
        user_id=user_id,
        amount=float(amount),
        description=f"Premium subscription - Order #{order_id}"
    )
    
    if not invoice_data:
        await callback.answer("Ошибка при создании платежа", show_alert=True)
        return
    
    payment_url = invoice_data['pay_url']
    
    text = get_payment_text('premium_payment', language).format(
        url=payment_url,
        amount=amount
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_payment_text('open_payment_link', language), url=payment_url)],
        [InlineKeyboardButton(text=get_payment_text('check_payment', language), callback_data=f"check_premium_crypto_{order_id}")],
        [InlineKeyboardButton(text=get_payment_text('back', language), callback_data=f"premium_info")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("check_premium_crypto_"))
async def handle_check_premium_crypto(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[3])
    language = get_user_language(callback.from_user.id)
    
    status = await cryptobot.check_order_payment(order_id)
    
    if status == 'paid':
        await callback.answer("✅ Premium подписка активирована!", show_alert=True)
        
        text = "⭐ <b>Ваша Premium подписка успешно активирована!</b>\n\n"
        text += "🎯 Теперь вы получаете скидку на все товары в магазине."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Перейти в магазин", callback_data="shop_m")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
    elif status == 'active':
        await callback.answer("⏳ Ожидание оплаты Premium подписки...", show_alert=True)
    else:
        await callback.answer("❌ Платеж не найден или отменен", show_alert=True)

from payments.ton_direct import ton_direct
import os

from base.methods import get_user_language
from payments.texts import get_payment_text
from payments.ton_direct import ton_direct, get_ton_price_usd
from io import BytesIO

from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile
)

import qrcode

@router.callback_query(F.data.startswith("pay_tonkeeper_"))
async def handle_tonkeeper_payment(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    order_id = int(callback.data.split("_")[2])

    MERCHANT_ADDRESS = os.getenv("MERCHANT_TON_ADDRESS")
    if not MERCHANT_ADDRESS:
        await callback.answer("❌ Ошибка: адрес магазина не настроен", show_alert=True)
        return

    with sqlite3.connect(os.path.join(os.path.dirname(PROJECT_ROOT), "payments", "payments_data.db")) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT final_price, product_id FROM orders WHERE id = ?',
            (order_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        
        usd_amount, product_id = result

    ton_price_usd = await get_ton_price_usd()
    ton_amount = (usd_amount / ton_price_usd)
    ton_amount_n = ton_amount * 1_000_000_000
    ton_amount_nano = int(ton_amount_n)

    comment = await ton_direct.register_order(order_id, user_id, usd_amount)

    ton_link = (
        f"ton://transfer/{MERCHANT_ADDRESS}"
        f"?amount={ton_amount_nano}"
        f"&text={comment.replace('#', '%23')}"
    )

    text = (
        f"<b>{get_payment_text('tonkeeper_payment_title', language)}</b>\n\n"
        f"{get_payment_text('tonkeeper_amount', language).format(ton_amount=ton_amount, usd_amount=usd_amount)}\n\n"
        f"<b>{get_payment_text('tonkeeper_comment_label', language)}</b>\n"
        f"<code>{comment}</code>\n\n"
        f"{get_payment_text('tonkeeper_instruction', language)}\n\n"
        f"{get_payment_text('tonkeeper_warning', language)}"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(ton_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)

    await callback.message.delete()
    
    await callback.message.answer_photo(
        photo=BufferedInputFile(bio.read(), filename="ton_payment_qr.png"),
        caption=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=get_payment_text('open_payment_link', language),
                url=ton_link
            )],
            [InlineKeyboardButton(
                text=get_payment_text('check_payment', language),
                callback_data=f"check_tonkeeper_{order_id}"
            )],
            [InlineKeyboardButton(
                text=get_payment_text('back', language),
                callback_data=f"product_{product_id}" if product_id > 0 else "premium_info"
            )]
        ]),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("check_tonkeeper_"))
async def handle_check_tonkeeper(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    language = get_user_language(callback.from_user.id)

    status = await ton_direct.check_order_payment(order_id)

    if status == 'paid':
        await callback.answer(get_payment_text('payment_success', language), show_alert=True)
        text = get_payment_text('payment_success', language)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_payment_text('back_to_shop', language), callback_data="shop_m")]
        ])
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except:
            await callback.message.reply(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.message.delete()
    elif status == 'pending':
        await callback.answer(get_payment_text('payment_pending', language), show_alert=True)
    else:
        await callback.answer("❌ Ошибка или платёж не найден", show_alert=True)

@router.callback_query(F.data == "renew_premium")
async def handle_renew_premium(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)

    current_sub = subscription_db.get_user_subscription(user_id)

    if not current_sub or not current_sub.check_active():
        await handle_premium_info(callback, state)
        await callback.answer(get_payment_text('subscription_expired', language), show_alert=True)
        return

    plans = subscription_db.get_subscription_plans()

    matching_plan = next((p for p in plans if p['days'] == current_sub.plan_days), None)

    if not matching_plan:
        matching_plan = max(plans, key=lambda p: p['days'])

    days = matching_plan['days']
    price = matching_plan['price']
    discount = matching_plan['discount']

    order_id = payment_db.create_order(
        user_id=user_id,
        product_id=-days,
        original_price=price,
        final_price=price,
        discount_percent=0
    )

    text = get_payment_text('buy_premium', language).format(
        days=days,
        price=price,
        discount=discount
    )
    text += "\n\n<i>Продление текущей подписки (ещё {days_left} дней)</i>".format(
        days_left=current_sub.days_until_expiry()
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_payment_text('pay_cryptobot', language),
            callback_data=f"pay_premium_crypto_{order_id}"
        )],
        [InlineKeyboardButton(
            text=get_payment_text('pay_tonkeeper', language),
            callback_data=f"pay_tonkeeper_{order_id}"
        )],
        [InlineKeyboardButton(
            text=get_payment_text('back', language),
            callback_data="premium_info"
        )]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.reply(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.message.delete()