import os
import asyncio
import datetime

import pandas as pd
from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, FSInputFile

from database.db_class import DataBase
from keyboards.inline_kayboards import create_info_panel, show_info_panel_list, create_delete_confirmation_keyboard
from parsers.booking_parser import parse_booking
from utils.constants import MIN_REFRESH_TIME
from utils.utils import run_in_executor, format_date

# Initialize a router
router = Router()


# Info panel navigation handler
@router.callback_query(F.data.startswith('info_'))
async def change_info_panel(callback_query: CallbackQuery, bot: Bot, db: DataBase) -> None:
    """Handles user navigation through the info panels."""
    # Get the info panel data from database, using user_id and message_id
    info_panel = await db.get_info_panel(callback_query.from_user.id, callback_query.message.message_id)

    # If info panel is not active, notify the user and remove the inactive panel
    if not info_panel:
        await callback_query.answer(
            'You are clicking on no more working information panel'
        )
        await asyncio.sleep(1.5)
        await callback_query.message.delete()
        return

    # Get relevant details from the info panel for navigation
    info_panel_id = info_panel.get('info_panel_id')
    cur_position = info_panel.get('cur_position')
    info_length = info_panel.get('length')

    # If user presses on page indicator answer callback and exit function
    if callback_query.data == 'info_page':
        await callback_query.answer()
        return

    # Adjust the current position based on the navigation command
    if callback_query.data == 'info_previous':
        cur_position -= 1
    elif callback_query.data == 'info_next':
        cur_position += 1
    elif callback_query.data.startswith('info_position_'):
        cur_position = int(callback_query.data.split('_')[-1])

    # Check if the new position is within the valid range
    if cur_position <= 0 or cur_position > info_length:
        await callback_query.answer()
        return

    # Update current info panel position in the db and get hotel based on the new position
    hotel_info = await db.update_position_get_hotel(info_panel_id, cur_position)

    # Edit the message media with the new hotel information
    await bot.edit_message_media(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        media=InputMediaPhoto(
            media=hotel_info.get('photo'),
            caption=(
                f'🏨 <b>{hotel_info.get('name')}</b>\n'
                f'💸 {hotel_info.get('price')}$\n'
                f'⭐️ {hotel_info.get('rating') if hotel_info.get('rating') else 'No rating'}\n\n'
                f'🏙 <b>{hotel_info.get('destination')}</b>\n'
                f'🛬 {await format_date(hotel_info.get('check_in'))}\n'
                f'🛫 {await format_date(hotel_info.get('check_out'))}'
            )
        ),
        reply_markup=await create_info_panel(hotel_info.get('link'), cur_position, info_length)
    )


# List navigation handler
@router.callback_query(F.data.startswith('list_'))
async def change_list(callback_query: CallbackQuery, db: DataBase) -> None:
    """Handles user navigation through the list of hotels."""
    # Get the info panel data from database, using user_id and message_id
    info_panel = await db.get_info_panel(callback_query.from_user.id, callback_query.message.message_id)

    # If info panel is not active, notify the user and remove the inactive panel
    if not info_panel:
        await callback_query.answer(
            'You are clicking on no more working information panel'
        )
        await asyncio.sleep(1.5)
        await callback_query.message.delete()
        return

    # Get relevant details from the info panel for navigation
    info_panel_id = info_panel.get('info_panel_id')
    cur_list_position = info_panel.get('cur_list_position')
    info_length = info_panel.get('length')

    # If user presses on page indicator answer callback and exit function
    if callback_query.data == 'list_page':
        await callback_query.answer()
        return

    # Calculate the length of the list
    list_length = (info_length - 1) // 5 + 1

    # Process list navigation commands
    if callback_query.data == 'list_previous':
        cur_list_position -= 5
    elif callback_query.data == 'list_next':
        cur_list_position += 5

    # Check if the new position is within the valid range
    if cur_list_position < 0 or cur_list_position > info_length:
        await callback_query.answer()
        return

    # Update current list position in the db and get hotel based on the new position
    hotels_info = await db.update_list_position_get_hotels(info_panel_id, cur_list_position)
    # Update list
    await callback_query.message.edit_reply_markup(
        reply_markup=await show_info_panel_list(hotels_info, cur_list_position, list_length)
    )


# Display list handler
@router.callback_query(F.data == 'show_list')
async def show_list(callback_query: CallbackQuery, db: DataBase) -> None:
    """Displays the list of hotels based on the current position."""
    # Get the info panel data from database, using user_id and message_id
    info_panel = await db.get_info_panel(callback_query.from_user.id, callback_query.message.message_id)
    # If info panel is not active, notify the user and remove the inactive panel
    if not info_panel:
        await callback_query.answer(
            'You are clicking on no more working information panel'
        )
        await asyncio.sleep(1.5)
        await callback_query.message.delete()
        return

    # Get relevant details from the info panel for navigation
    info_panel_id = info_panel.get('info_panel_id')
    cur_position = info_panel.get('cur_position')
    info_length = info_panel.get('length')

    # Calculate cur list position and list length
    cur_list_position = 1 + 5 * ((cur_position - 1) // 5)
    list_length = (info_length - 1) // 5 + 1

    # Update current list position in the db and get hotel based on the new position
    hotels_info = await db.update_list_position_get_hotels(info_panel_id, cur_list_position)
    # Update message with the list
    await callback_query.message.edit_reply_markup(
        reply_markup=await show_info_panel_list(hotels_info, cur_list_position, list_length)
    )


# Handler to confirm deletion of an info panel
@router.callback_query(F.data == 'panel_delete')
async def ask_to_delete_info_panel(callback_query: CallbackQuery) -> None:
    """Asks the user for confirmation before deleting an info panel."""
    await callback_query.answer()
    await callback_query.message.answer(
        'Are you sure you want to delete this info panel?',
        reply_markup=await create_delete_confirmation_keyboard(callback_query.message.message_id)
    )


# Handler to exit the info panel without deleting
@router.callback_query(F.data == 'save')
async def leave_info_panel(callback_query: CallbackQuery) -> None:
    """Exits the info panel without making changes."""
    await callback_query.message.delete()


# Handler to delete an info panel
@router.callback_query(F.data.startswith('delete_'))
async def delete_info_panel(callback_query: CallbackQuery, bot: Bot, db: DataBase) -> None:
    """Deletes the selected info panel after confirmation."""
    # Delete the previous confirmation message
    await callback_query.message.delete()
    # Extract message ID from callback data
    callback_query_message_id = int(callback_query.data.split('_')[1])
    # Get message details from the database
    info_panel = await db.get_info_panel(callback_query.from_user.id, callback_query_message_id)
    # Delete the form from database associated with the info panel
    if info_panel:
        await db.delete_info_panel(info_panel.get('info_panel_id'))
    # Delete the info panel from the chat
    await bot.delete_message(
        chat_id=callback_query.from_user.id,
        message_id=callback_query_message_id
    )
    await callback_query.answer('Info panel is deleted')


# Handler to delete all info panels
@router.callback_query(F.data == 'all_delete')
async def delete_all_info_panels(callback_query: CallbackQuery, bot: Bot, db: DataBase) -> None:
    """Deletes all information panels associated with the user."""
    await callback_query.message.delete()

    # Get all info panels for the user from the database
    info_panels = await db.get_all_info_panels(callback_query.from_user.id)

    # If no info panels exist, inform the user and exit the function
    if not info_panels:
        await callback_query.message.answer('You do not have any info panels. Use /start_form to create them.')
        return

    # Loop over each info panel, delete them from database and delete messages with them
    for info_panel in info_panels:
        await db.delete_info_panel(info_panel.get('info_panel_id'))
        await bot.delete_message(
            chat_id=callback_query.from_user.id,
            message_id=info_panel.get('message_id')
        )


# Handler to refresh the information panel
@router.callback_query(F.data == 'refresh')
async def refresh_info_panel(callback_query: CallbackQuery, bot: Bot, db: DataBase) -> None:
    """Refreshes the information panel if the cooldown period has passed."""
    form_info_panel = await db.get_form_info_panel(callback_query.from_user.id, callback_query.message.message_id)

    # If info panel does work, inform the user and delete it
    if not form_info_panel:
        await callback_query.answer(
            'You are clicking on no more working information panel'
        )
        await asyncio.sleep(1.5)
        await callback_query.message.delete()
        return

    # Check if the check-in date has passed
    if datetime.date.today() > datetime.datetime.strptime(
            form_info_panel.get('check_in'), '%Y-%m-%d'
    ).date():
        # Inform user that the data of info panel has been expired
        await callback_query.answer(
            text='Data has been expired. Info panel will be deleted.'
        )
        await asyncio.sleep(1.5)
        # Delete the expired info panel message
        await bot.delete_message(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
        )
        # Delete the expired info panel from the database
        await db.delete_info_panel(form_info_panel.get('info_panel_id'))
        return

    # Get relevant details from the info panel
    info_panel_id = form_info_panel.get('info_panel_id')
    last_refresh = datetime.datetime.strptime(form_info_panel.get('last_refresh'), "%Y-%m-%d %H:%M:%S.%f")
    time_since_last_refresh = datetime.datetime.now() - last_refresh

    # Check if the refresh cooldown has passed
    if time_since_last_refresh < datetime.timedelta(seconds=MIN_REFRESH_TIME):
        await callback_query.answer(
            f'You cannot refresh this info panel for next {MIN_REFRESH_TIME - time_since_last_refresh.seconds} seconds'
        )
        return

    # Set the caption to 'Refreshing...' for the info panel
    await bot.edit_message_caption(
        message_id=callback_query.message.message_id,
        caption='<b>Refreshing...</b>',
        chat_id=callback_query.from_user.id
    )

    # Parse hotels
    hotels_info = await run_in_executor(
        parse_booking,
        form_info_panel.get('destination'),
        form_info_panel.get('check_in'),
        form_info_panel.get('check_out'),
        form_info_panel.get('adults'),
        form_info_panel.get('rooms'),
        form_info_panel.get('children'),
        form_info_panel.get('children_age'),
        form_info_panel.get('order_by')
    )

    # If hotel information is missing inform user and exit function
    if not hotels_info:
        await callback_query.answer(
            'No information available right now.'
        )
        return

    # Get the number of hotels found
    hotels_info_length = len(hotels_info)

    # Edit the message media with the new hotel information
    await bot.edit_message_media(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        media=InputMediaPhoto(
            media=hotels_info[0].get('Photo'),
            caption=(
                f'🏨 <b>{hotels_info[0].get("Name")}</b>\n'
                f'💸 {hotels_info[0].get("Price")}$\n'
                f'⭐️ {hotels_info[0].get("Rating") if hotels_info[0].get("Rating") else 'No rating'}\n\n'
                f'🏙 <b>{form_info_panel.get('destination')}</b>\n'
                f'🛬 {await format_date(form_info_panel.get('check_in'))}\n'
                f'🛫 {await format_date(form_info_panel.get('check_out'))}'
            )
        ),
        reply_markup=await create_info_panel(hotels_info[0].get('Link'), 1, hotels_info_length)
    )

    # Update the database with the new hotel information
    await db.update_hotels_info_panel(
        info_panel_id, hotels_info,
        hotels_info_length, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    )


# Handler to send an Excel table with information about hotels
@router.callback_query(F.data.startswith('excel_'))
async def get_excel(callback_query: CallbackQuery, bot: Bot, db: DataBase) -> None:
    """Generates an Excel file with hotel information based on user's choice and sends it to the user."""
    # Initialize hotels_info variable
    hotels_info = None

    # Check the specific callback data and get corresponding hotel info
    if callback_query.data == 'excel_price':
        hotels_info = await db.get_hotels_info_price(callback_query.from_user.id)
    elif callback_query.data == 'excel_rating':
        hotels_info = await db.get_hotels_info_rating(callback_query.from_user.id)

    # If no hotel info is available, inform the user and exit function
    if not hotels_info:
        await callback_query.answer('You do not have any info panels. Use /start_form to create them.')
        await callback_query.message.delete()
        return

    await callback_query.message.delete()

    # Create a DataFrame from the hotel info
    df = pd.DataFrame(hotels_info)
    # Save the DataFrame to an Excel file
    df.to_excel(rf'data\{callback_query.from_user.id}.xlsx', index=False)

    # Prepare the Excel file for sending
    hotels_info = FSInputFile(
        rf'data\{callback_query.from_user.id}.xlsx', filename=f'hotels_info.xlsx'
    )

    # Send the Excel file to the user
    await bot.send_document(
        chat_id=callback_query.from_user.id,
        document=hotels_info
    )

    # Remove the Excel file after sending
    os.remove(rf'data\{callback_query.from_user.id}.xlsx')
