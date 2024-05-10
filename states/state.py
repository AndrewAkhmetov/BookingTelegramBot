from aiogram.fsm.state import StatesGroup, State


# Create State
class Form(StatesGroup):
    user_id = State()
    existing_panels_count = State()
    destination = State()
    check_in = State()
    check_in_index = State()
    check_out = State()
    adults = State()
    children = State()
    children_age = State()
    children_age_index = State()
    rooms = State()
    order_by = State()
    prev_messages = State()
