from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    language_selection = State()
    subscription_check = State()
    main_menu = State()