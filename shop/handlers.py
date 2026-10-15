from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from base.states import UserStates
from base.methods import get_user_language
from shop.methods import ProductMethodsDB
from shop.texts import get_shop_text
from project.main_menu import show_main_menu
from payments.methods import SubscriptionMethodsDB

subscription_db = SubscriptionMethodsDB()

router = Router()
product_db = ProductMethodsDB()


@router.callback_query(F.data == "shop_m")
async def handle_shop(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    
    categories = product_db.get_all_categories()
    
    if not categories:
        try:
            await callback.message.edit_text(
                get_shop_text('shop_empty', language),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=get_shop_text('back', language), callback_data="back_to_main")]
                ])
            )
        except:
            await callback.message.reply(
                    get_shop_text('shop_empty', language),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=get_shop_text('back', language), callback_data="back_to_main")]
                    ])
                )
            await callback.message.delete()
        return
    
    buttons = []
    for category in categories:
        if product_db.has_active_products_in_category(category):
            buttons.append([InlineKeyboardButton(
                text=f"📁 {category}",
                callback_data=f"category_{category}"
            )])
    
    buttons.append([InlineKeyboardButton(
        text=get_shop_text('back', language),
        callback_data="back_to_main"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        get_shop_text('shop_title', language),
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("category_"))
async def handle_category(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    category = callback.data.replace("category_", "")
    
    products = product_db.get_products_by_category(category)
    
    if not products:
        await callback.message.edit_text(
            get_shop_text('category_no_products', language),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_shop_text('back', language), callback_data="shop_m")]
            ])
        )
        return
    
    buttons = []
    for product in products:
        # Рассчитываем цену со скидкой
        user_discount = subscription_db.get_user_discount(user_id)
        final_price = product.price * (1 - user_discount / 100) if user_discount > 0 else product.price
        price_str = f"{final_price:.2f}"
        
        # Кнопка только с итоговой ценой
        button_text = f"{product.name} - ${price_str}"
        
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"product_{product.id}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text=get_shop_text('back', language),
        callback_data="shop_m"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        get_shop_text('category_title', language, category=category),
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("product_"))
async def handle_product(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    product_id = int(callback.data.replace("product_", ""))
    
    product = product_db.get_product(product_id)
    
    if not product:
        await callback.message.edit_text(
            get_shop_text('product_not_found', language),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_shop_text('back', language), callback_data="shop_m")]
            ])
        )
        return
    
    user_discount = subscription_db.get_user_discount(user_id)
    final_price = product.price * (1 - user_discount / 100) if user_discount > 0 else product.price
    final_price_str = f"{final_price:.2f}"

    text = get_shop_text('product_info', language).format(
        name=product.name,
        description=product.description,
        price=final_price_str,  # ← здесь уже итоговая цена
        category=product.category
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🛒 Купить за ${final_price_str}",  # ← только итоговая цена
                callback_data=f"buy_{product.id}"
            ),
            InlineKeyboardButton(text=get_shop_text('back', language), callback_data=f"category_{product.category}")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    language = get_user_language(user_id)
    await show_main_menu(callback, language, state)