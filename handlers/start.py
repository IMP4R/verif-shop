from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from base.methods import (
    get_user_language,
    check_channel_subscription,
    show_language_selection,
    show_subscription_request,
    show_main_menu,
    methods_db
)

router = Router()

@router.message(Command("start"))
async def handle_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if len(message.text.split()) > 1:
        start_param = message.text.split()[1]
        from profiles.methods import ReferralMethodsDB
        referral_db = ReferralMethodsDB()
        referral_db.process_referral_registration(user_id, start_param)
    
    current_language = get_user_language(user_id)
    
    if methods_db.user_exists(user_id):
        is_subscribed = await check_channel_subscription(user_id)
        
        if not is_subscribed:
            await show_subscription_request(message, current_language, state)
        else:
            await show_main_menu(message, current_language, state)
    else:
        await show_language_selection(message, state)