from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
from dirrrr import PROJECT_ROOT
from base.methods import get_user_language
from admin.methods import RulesAndInstructionsDB
from admin.texts import get_admin_text

router = Router()
rules_db = RulesAndInstructionsDB()

ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class RulesStates(StatesGroup):
    waiting_for_rule_name = State()
    waiting_for_telegraph_url = State()

class InstructionsStates(StatesGroup):
    waiting_for_instruction_name = State()
    waiting_for_instruction_text = State()
    waiting_for_delivery_bot = State()


@router.callback_query(F.data == "admin_rules_instructions")
async def handle_rules_instructions(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        await callback.answer("⛔ Доступ запрещен")
        return
    
    text = "📝 <b>Управление правилами и инструкциями</b>\n\n"
    text += "Выберите раздел для управления:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Правила перед оплатой", callback_data="manage_pre_payment_rules")],
        [InlineKeyboardButton(text="📋 Инструкции после оплаты", callback_data="manage_post_payment_instructions")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "manage_pre_payment_rules")
async def handle_manage_pre_payment_rules(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    rules = rules_db.get_pre_payment_rules()
    
    text = "📋 <b>Правила перед оплатой</b>\n\n"
    
    if not rules:
        text += "Нет правил"
    else:
        for rule in rules:
            status = "✅ Активен" if rule['is_active'] else "❌ Не активен"
            text += f"{rule['id']}. {rule['name']} - {status}\n"
            text += f"   🔗 {rule['telegraph_url'][:50]}...\n\n"
    
    buttons = []
    for rule in rules:
        status_text = "❌" if rule['is_active'] else "✅"
        action = "deactivate" if rule['is_active'] else "activate"
        buttons.append([
            InlineKeyboardButton(
                text=f"{rule['id']}. {rule['name']}",
                callback_data=f"view_rule_{rule['id']}"
            ),
            InlineKeyboardButton(
                text=status_text,
                callback_data=f"toggle_rule_{rule['id']}"
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"delete_rule_{rule['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить правило", callback_data="add_pre_payment_rule"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_rules_instructions")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "add_pre_payment_rule")
async def handle_add_pre_payment_rule(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.set_state(RulesStates.waiting_for_rule_name)
    
    text = "📝 <b>Добавление правил перед оплатой</b>\n\n"
    text += "Введите название набора правил (например: 'Основные правила'):"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_pre_payment_rules")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(RulesStates.waiting_for_rule_name)
async def handle_rule_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.update_data(rule_name=message.text.strip())
    await state.set_state(RulesStates.waiting_for_telegraph_url)
    
    text = "🔗 Введите ссылку на Telegraph с правилами:\n\n"
    text += "Пример: https://telegra.ph/Pravila-pokupki-01-01"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_pre_payment_rules")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.message(RulesStates.waiting_for_telegraph_url)
async def handle_telegraph_url(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    telegraph_url = message.text.strip()
    
    if not (telegraph_url.startswith('http://') or telegraph_url.startswith('https://')):
        await message.answer("❌ Некорректная ссылка. Используйте http:// или https://")
        return
    
    data = await state.get_data()
    rule_name = data['rule_name']
    
    rule_id = rules_db.add_pre_payment_rule(rule_name, telegraph_url)
    
    await state.clear()
    
    text = f"✅ Правила успешно добавлены!\n\n"
    text += f"Название: {rule_name}\n"
    text += f"Ссылка: {telegraph_url}\n"
    text += f"ID: {rule_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку правил", callback_data="manage_pre_payment_rules")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("toggle_rule_"))
async def handle_toggle_rule(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    rule_id = int(callback.data.replace("toggle_rule_", ""))
    
    if rules_db.toggle_rule_active(rule_id):
        await callback.answer("✅ Статус правила изменен")
        await handle_manage_pre_payment_rules(callback)
    else:
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("delete_rule_"))
async def handle_delete_rule(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    rule_id = int(callback.data.replace("delete_rule_", ""))
    
    if rules_db.delete_rule(rule_id):
        await callback.answer("✅ Правило удалено")
        await handle_manage_pre_payment_rules(callback)
    else:
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data == "manage_post_payment_instructions")
async def handle_manage_post_payment_instructions(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    instructions = rules_db.get_post_payment_instructions()
    
    text = "📋 <b>Инструкции после оплаты</b>\n\n"
    
    if not instructions:
        text += "Нет инструкций"
    else:
        for instr in instructions:
            status = "✅ Активна" if instr['is_active'] else "❌ Не активна"
            text += f"{instr['id']}. {instr['name']} - {status}\n\n"
    
    buttons = []
    for instr in instructions:
        status_text = "❌" if instr['is_active'] else "✅"
        action = "deactivate" if instr['is_active'] else "activate"
        buttons.append([
            InlineKeyboardButton(
                text=f"{instr['id']}. {instr['name']}",
                callback_data=f"view_instruction_{instr['id']}"
            ),
            InlineKeyboardButton(
                text=status_text,
                callback_data=f"toggle_instruction_{instr['id']}"
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"delete_instruction_{instr['id']}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить инструкцию", callback_data="add_post_payment_instruction"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_rules_instructions")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "add_post_payment_instruction")
async def handle_add_post_payment_instruction(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.set_state(InstructionsStates.waiting_for_instruction_name)
    
    text = "📝 <b>Добавление инструкции после оплаты</b>\n\n"
    text += "Введите название инструкции (например: 'Инструкция для товаров'):"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_post_payment_instructions")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(InstructionsStates.waiting_for_instruction_name)
async def handle_instruction_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.update_data(instruction_name=message.text.strip())
    await state.set_state(InstructionsStates.waiting_for_instruction_text)
    
    text = "📝 Введите текст инструкции:\n\n"
    text += "Можно использовать HTML разметку. Переменные:\n"
    text += "{order_number} - номер заказа\n"
    text += "{bot_username} - username бота для выдачи\n\n"
    text += "Пример:\n"
    text += "Оплата получена. Ваш номер заказа: №{order_number}\n"
    text += "Введите номер телефона с кодом страны...\n"
    text += "Укажите номер заказа {order_number}\n"
    text += "Отправьте данные в бот: @delivery_bot"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="manage_post_payment_instructions")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.message(InstructionsStates.waiting_for_instruction_text)
async def handle_instruction_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    await state.update_data(instruction_text=message.text.strip())
    await state.set_state(InstructionsStates.waiting_for_delivery_bot)
    
    text = "🤖 Введите username бота для выдачи товара (например: @delivery_bot):\n\n"
    text += "Оставьте пустым, если бот не указан"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_delivery_bot")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "skip_delivery_bot")
async def handle_skip_delivery_bot(callback: CallbackQuery, state: FSMContext):
    await save_instruction(callback, state, "")


@router.message(InstructionsStates.waiting_for_delivery_bot)
async def handle_delivery_bot_input(message: Message, state: FSMContext):
    delivery_bot = message.text.strip()
    await save_instruction(message, state, delivery_bot)


async def save_instruction(update, state: FSMContext, delivery_bot: str):
    user_id = update.from_user.id if isinstance(update, Message) else update.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    data = await state.get_data()
    instruction_name = data['instruction_name']
    instruction_text = data['instruction_text']
    
    if delivery_bot and not delivery_bot.startswith('@'):
        delivery_bot = f"@{delivery_bot}"
    
    instruction_id = rules_db.add_post_payment_instruction(
        instruction_name, 
        instruction_text, 
        delivery_bot
    )
    
    await state.clear()
    
    text = f"✅ Инструкция успешно добавлена!\n\n"
    text += f"Название: {instruction_name}\n"
    text += f"ID: {instruction_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку инструкций", callback_data="manage_post_payment_instructions")]
    ])
    
    if isinstance(update, Message):
        await update.answer(text, reply_markup=keyboard)
    else:
        await update.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("toggle_instruction_"))
async def handle_toggle_instruction(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    instruction_id = int(callback.data.replace("toggle_instruction_", ""))
    
    if rules_db.toggle_instruction_active(instruction_id):
        await callback.answer("✅ Статус инструкции изменен")
        await handle_manage_post_payment_instructions(callback)
    else:
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("delete_instruction_"))
async def handle_delete_instruction(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    instruction_id = int(callback.data.replace("delete_instruction_", ""))
    
    if rules_db.delete_instruction(instruction_id):
        await callback.answer("✅ Инструкция удалена")
        await handle_manage_post_payment_instructions(callback)
    else:
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("view_instruction_"))
async def handle_view_instruction(callback: CallbackQuery):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    if not is_admin(user_id):
        return
    
    instruction_id = int(callback.data.replace("view_instruction_", ""))
    
    instructions = rules_db.get_post_payment_instructions()
    instruction = next((i for i in instructions if i['id'] == instruction_id), None)
    
    if not instruction:
        await callback.answer("❌ Инструкция не найдена")
        return
    
    text = f"📋 <b>Инструкция: {instruction['name']}</b>\n\n"
    text += f"<b>Текст:</b>\n{instruction['instruction_text']}\n\n"
    
    if instruction['delivery_bot_username']:
        text += f"<b>Бот для выдачи:</b> {instruction['delivery_bot_username']}\n"
    
    text += f"<b>Статус:</b> {'✅ Активна' if instruction['is_active'] else '❌ Не активна'}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_post_payment_instructions")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")