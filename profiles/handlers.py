from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from base.methods import get_user_language
from .methods import ProfileMethodsDB, ReferralMethodsDB
from .texts import get_profile_text
from project.main_menu import show_main_menu

router = Router()
profile_db = ProfileMethodsDB()
referral_db = ReferralMethodsDB()


@router.callback_query(F.data == "profile")
async def handle_profile(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    profile_data = profile_db.get_user_profile(user_id)
    referral_stats = referral_db.get_user_referral_stats(user_id)

    text = get_profile_text('profile_title', language).format(
        user_id=user_id,
        total_orders=profile_data['total_orders'],
        total_spent=profile_data['total_spent']
    )

    if profile_data['premium_active']:
        text += "\n\n" + get_profile_text('premium_status_active', language).format(
            discount=profile_data['premium_discount'],
            end_date=profile_data['premium_end_date']
        )
    else:
        text += "\n\n" + get_profile_text('premium_status_inactive', language)

    text += "\n\n" + get_profile_text('referral_stats', language).format(
        referrals_count=referral_stats['referrals_count'],
        earned=referral_stats['earned'],
        available=referral_stats['available']
    )

    ref_link = await referral_db.generate_referral_link(user_id)
    text += f"\n\n<code>{ref_link}</code>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_profile_text('my_orders', language), callback_data="my_orders")],
        [InlineKeyboardButton(text=get_profile_text('withdraw_funds', language), callback_data="withdraw_funds")],
        [InlineKeyboardButton(text=get_profile_text('back_to_menu', language), callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "my_orders")
async def handle_my_orders(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    orders = profile_db.get_user_orders(user_id, limit=10)
    
    if not orders:
        text = get_profile_text('no_orders', language)
    else:
        text = get_profile_text('orders_title', language)
        for order in orders:
            text += f"\n\n📦 {order['product_name']}"
            text += f"\n💰 ${order['final_price']}"
            text += f"\n📅 {order['created_at']}"
            if order['discount'] > 0:
                text += f"\n🎯 Скидка: {order['discount']}%"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_profile_text('back_to_profile', language), callback_data="profile")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "withdraw_funds")
async def handle_withdraw_funds(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    available_balance = referral_db.get_available_balance(user_id)
    
    text = get_profile_text('withdraw_title', language).format(
        available=available_balance
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_profile_text('withdraw_10', language), callback_data="withdraw_10")],
        [InlineKeyboardButton(text=get_profile_text('withdraw_20', language), callback_data="withdraw_20")],
        [InlineKeyboardButton(text=get_profile_text('withdraw_custom', language), callback_data="withdraw_custom")],
        [InlineKeyboardButton(text=get_profile_text('back_to_profile', language), callback_data="profile")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

from .withdrawal_handlers import router as withdrawal_router
router.include_router(withdrawal_router)