from typing import Any, Optional

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Create an inline keyboard for selecting quantity with increment and decrement buttons
async def create_quantity_keyboard(number=1) -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()
    # Add decrement button
    kb_builder.button(text='-', callback_data='-')
    # Add button displaying the current number
    kb_builder.button(text=str(number), callback_data='number')
    # Add increment button
    kb_builder.button(text='+', callback_data='+')
    # Add confirmation button
    kb_builder.button(text='ok', callback_data='ok')

    # Arrange buttons into rows and columns
    kb_builder.adjust(3, 1)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


# Create an inline keyboard for selecting age from 1 to 17
async def create_age_keyboard() -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()
    # Add buttons for each age
    for i in range(0, 18):
        kb_builder.button(text=str(i), callback_data=str(i))
    # Arrange buttons into rows
    kb_builder.adjust(3)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


# Create an inline keyboard for sorting options
async def create_order_by_keyboard() -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()
    # Add buttons for each sorting option
    kb_builder.button(text='Top picks for long stays', callback_data='popularity')
    kb_builder.button(text='Homes & apartments first', callback_data='upsort_bh')
    kb_builder.button(text='Price (lowest first)', callback_data='price')
    kb_builder.button(text='Best reviewed & lowest price', callback_data='review_score_and_price')
    kb_builder.button(text='Property rating (high to low)', callback_data='class')
    kb_builder.button(text='Property rating (low to high)', callback_data='class_asc')
    kb_builder.button(text='Property rating and price', callback_data='class_and_price')
    kb_builder.button(text='Distance From Downtown', callback_data='distance_from_search')
    kb_builder.button(text='Top Reviewed', callback_data='bayesian_review_score')

    # Arrange buttons into a single column
    kb_builder.adjust(1)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


# Create an inline keyboard for delete confirmation
async def create_delete_confirmation_keyboard(callback_query_id: Optional[int]) -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()
    # Add 'Yes', 'No' buttons for confirmation, with dynamic callback data based on the query ID
    kb_builder.button(text='Yes', callback_data=f'delete_{callback_query_id}' if callback_query_id else 'all_delete')
    kb_builder.button(text='No', callback_data='save')

    # Arrange buttons into two columns
    kb_builder.adjust(2)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


# Create an inline keyboard, prompting the user to add more dates
async def create_dates_prompting_keyboard() -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()

    # Add 'Yes', 'No' buttons to confirm adding more dates
    kb_builder.button(text='Yes', callback_data='add_dates')
    kb_builder.button(text='No', callback_data='dont_add_dates')

    # Arrange buttons into two columns
    kb_builder.adjust(2)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


# Create an info panel with navigation and action buttons
async def create_info_panel(link: str, cur_position: int, info_length: int) -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()

    # Add a button linking to an external URL
    kb_builder.button(
        text='Link',
        url=link
    )
    # Add navigation buttons and display the current page/total pages
    kb_builder.button(
        text='⬅️',
        callback_data='info_previous'
    )
    kb_builder.button(
        text=f'{cur_position}/{info_length}',
        callback_data='info_page'
    )
    kb_builder.button(
        text='➡️',
        callback_data='info_next'
    ),
    # Add action buttons for additional functionality
    kb_builder.button(
        text='Show as list',
        callback_data='show_list'
    )
    kb_builder.button(
        text='Refresh',
        callback_data='refresh'
    )
    kb_builder.button(
        text='Delete',
        callback_data='panel_delete'
    )

    # Arrange buttons into rows with specified numbers of buttons per row
    kb_builder.adjust(1, 3, 1)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


# Create an inline keyboard to display a list of hotel information
async def show_info_panel_list(
        hotels_info: list[dict[str, Any]], cur_list_position: int, list_length: int
) -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()

    # Add buttons for each hotel with name, price, and rating
    for position, hotel_info in enumerate(hotels_info, start=cur_list_position):
        name, price, rating = hotel_info.get('name'), hotel_info.get('price'), hotel_info.get('rating')
        # Truncate the hotel name to fit within the button
        parts = name[:22].split(' ')
        name = ' '.join(parts[:-1]) if len(parts) > 1 else name[:22]
        kb_builder.button(
            text=(
                f'🏨 {name} '
                f'💸 ${price} '
                f"⭐️ {rating if rating else 'No rating'}"
            ),
            callback_data=f'info_position_{position}'
        )
    # Add navigation buttons and display the current page/total pages
    kb_builder.button(
        text='⬅️',
        callback_data='list_previous'
    )
    kb_builder.button(
        text=f'{(cur_list_position - 1) // 5 + 1}/{list_length}',
        callback_data='list_page'
    )
    kb_builder.button(
        text='➡️',
        callback_data='list_next'
    )
    # Add a button to go back to the previous menu
    kb_builder.button(
        text='Back',
        callback_data='info_back'
    )

    # Calculate the keyboard size based on the number of hotel entries and navigation buttons
    kb_size = (1,) * (position - cur_list_position + 1) + (3, 1)
    # Arrange buttons into rows with specified numbers of buttons per row
    kb_builder.adjust(*kb_size)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()


async def create_excel_keyboard() -> InlineKeyboardMarkup:
    # Initialize the keyboard builder
    kb_builder = InlineKeyboardBuilder()

    # Add buttons for sorting by price and rating
    kb_builder.button(
        text='Sort by price',
        callback_data='excel_price'
    )
    kb_builder.button(
        text='Sort by rating',
        callback_data='excel_rating'
    )

    # Arrange buttons into a single column
    kb_builder.adjust(1)
    # Return the constructed inline keyboard markup
    return kb_builder.as_markup()
