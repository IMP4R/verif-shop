from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from base.methods import get_user_language, update_user_language
from .methods import SettingsMethodsDB
from .texts import get_settings_text
from project.main_menu import show_main_menu
from config.languages import SUPPORTED_LANGUAGES

router = Router()
settings_db = SettingsMethodsDB()


class SettingsStates(StatesGroup):
    waiting_for_language = State()
    waiting_for_notification = State()


@router.callback_query(F.data == "settings")
async def handle_settings(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    user_settings = settings_db.get_user_settings(user_id)
    
    text = get_settings_text('settings_title', language)
    
    text += "\n\n" + get_settings_text('current_settings', language).format(
        language=SUPPORTED_LANGUAGES.get(language, {}).get('native', language),
        notifications=get_settings_text('notifications_on' if user_settings['notifications'] else 'notifications_off', language)
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=get_settings_text('change_language', language),
            callback_data="settings_language"
        )],
        #[InlineKeyboardButton(
        #    text=get_settings_text('toggle_notifications', language) + 
        #         f" ({get_settings_text('notifications_on' if user_settings['notifications'] else 'notifications_off', language)})",
        #    callback_data="settings_notifications"
        #)],
        #[InlineKeyboardButton(text=get_settings_text('about_bot', language),callback_data="settings_about")],
        [InlineKeyboardButton(
            text=get_settings_text('back_to_menu', language),
            callback_data="main_menu"
        )]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "settings_language")
async def handle_change_language(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    text = get_settings_text('choose_language', language)
    
    buttons = []
    for lang_code, lang_data in SUPPORTED_LANGUAGES.items():
        prefix = "✅ " if lang_code == language else ""
        button_text = f"{prefix}{lang_data['emoji']} {lang_data['native']}"
        
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"set_language_{lang_code}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text=get_settings_text('back', language),
        callback_data="settings"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("set_language_"))
async def handle_set_language(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    new_language = callback.data.split("_")[2]
    
    update_user_language(user_id, new_language)
    
    text = get_settings_text('language_changed', new_language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=get_settings_text('back_to_settings', new_language),
            callback_data="settings"
        ),
        InlineKeyboardButton(
            text=get_settings_text('back_to_menu', new_language),
            callback_data="main_menu"
        )
    ]])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data == "settings_notifications")
async def handle_toggle_notifications(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    new_status = settings_db.toggle_notifications(user_id)
    
    text = get_settings_text('notifications_toggled', language).format(
        status=get_settings_text('notifications_on' if new_status else 'notifications_off', language)
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=get_settings_text('back_to_settings', language),
            callback_data="settings"
        )
    ]])
    
    await callback.answer(text, show_alert=True)
    
    await handle_settings(callback, state)


@router.callback_query(F.data == "settings_about")
async def handle_about_bot(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    bot_stats = settings_db.get_bot_stats()
    
    text = get_settings_text('about_title', language)
    
    text += "\n\n" + get_settings_text('features', language).format(
        features="\n".join([
            "✅ " + get_settings_text('feature_shop', language),
            "✅ " + get_settings_text('feature_premium', language),
            "✅ " + get_settings_text('feature_referrals', language),
            "✅ " + get_settings_text('feature_multilanguage', language)
        ])
    )
    
    text += "\n\n" + get_settings_text('bot_stats', language).format(
        users=bot_stats['total_users'],
        products=bot_stats['active_products'],
        orders=bot_stats['total_orders']
    )
    
    text += "\n\n" + get_settings_text('version', language).format(version="1.0.0")
    
    text += "\n\n" + get_settings_text('contact_info', language)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=get_settings_text('contact_support', language),
            url="https://t.me/verifypostav"
        ),
        InlineKeyboardButton(
            text=get_settings_text('back_to_settings', language),
            callback_data="settings"
        )
    ]])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    await show_main_menu(callback, language, state)