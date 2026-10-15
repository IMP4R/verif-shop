TEXTS = {
    'ru': {
        'shop_menu': '🛒 Магазин',
        'shop_title': 'Выберите категорию:',
        'shop_empty': 'Магазин пуст',
        'category_no_products': 'В этой категории пока нет товаров',
        'category_title': '📁 {category}\n\nВыберите товар:',
        'product_info': '📦 <b>{name}</b>\n\n📝 <b>Описание:</b>\n{description}\n\n💰 <b>Цена:</b> ${price}\n📁 <b>Категория:</b> {category}',
        'product_not_found': 'Товар не найден',
        'buy': '🛒 Купить',
        'back': '⬅️ Назад'
    },
    'en': {
        'shop_menu': '🛒 Shop',
        'shop_title': 'Choose category:',
        'shop_empty': 'Shop is empty',
        'category_no_products': 'No products in this category yet',
        'category_title': '📁 {category}\n\nChoose product:',
        'product_info': '📦 <b>{name}</b>\n\n📝 <b>Description:</b>\n{description}\n\n💰 <b>Price:</b> ${price}\n📁 <b>Category:</b> {category}',
        'product_not_found': 'Product not found',
        'buy': '🛒 Buy',
        'back': '⬅️ Back'
    }
}

import sqlite3
def get_shop_text(text_key: str, language: str = 'ru', **kwargs) -> str:
    try:
        from admin.methods import TextEditorMethodsDB
        text_editor_db = TextEditorMethodsDB()
        custom_text = text_editor_db.get_text('shop', text_key, language)
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