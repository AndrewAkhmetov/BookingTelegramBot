import asyncio
import datetime

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto

from database.db_class import DataBase
from keyboards.inline_kayboards import create_delete_confirmation_keyboard, create_info_panel, create_excel_keyboard
from parsers.booking_parser import parse_booking
from utils.constants import SORT_OPTIONS_DESCRIPTIONS, MIN_REFRESH_TIME, MAX_PANELS
from utils.utils import run_in_executor, format_date
from states.state import Form

# Initialize a router
command_router = Router()


# Starting message handler
@command_router.message(CommandStart())
async def start(message: Message) -> None:
    """Greets the user and send him brief description of bot features"""
    await message.answer(
        "Hello! I'm here to assist you in creating info panels with all the "
        "available hotels from Booking.com, tailored to your preferences.\n"
        "To begin choosing hotels, please use the /start_form command.\n"
        "If you need to cancel the form at any time, just use the /cancel command.\n"
        "If you would like to ensure you have the latest data in all your info panels, "
        "use the /refresh_all command to refresh them.\n"
        "Should you wish to remove all existing info panels, the /delete_all command is available.\n"
        "If you're interested in information about all hotels, use the /get_excel command "
        "that will provide you this data in Excel format.\n"
        "Lastly, to review the details you've entered, use the /get_form command."
    )


# Handler to initiate a new form
@command_router.message(Command('start_form'))
async def start_from(message: Message, state: FSMContext, db: DataBase) -> None:
    """Starts a new form for the user to create an info panel."""
    # Check the number of existing info panels for the user
    existing_panels_count = await db.count_all_info_panels(message.from_user.id)

    if existing_panels_count >= MAX_PANELS:
        # Inform the user about the limit on info panels
        destination_prompt = await message.answer(
            'You cannot have more info panels. Delete some of them to get a new one'
        )
        await asyncio.sleep(1.5)
        await message.delete()
        await destination_prompt.delete()
        return

    # Continue form creation
    await state.update_data(user_id=message.from_user.id)
    await state.update_data(existing_panels_count=existing_panels_count)
    await state.set_state(Form.destination)
    destination_prompt = await message.answer(
        'Please write your destination.\n'
        'If you would like to add multiple destinations write destinations, separated by commas.\n'
        'Example: Paris, New York, Berlin'
    )
    # Keep track of the previous messages
    await state.update_data(prev_messages=[message, destination_prompt])


# Handler for the cancel command
@command_router.message(Command('cancel'))
async def clear_state(message: Message, state: FSMContext, bot: Bot) -> None:
    """Cancels the current form and clears previous messages and the state."""
    cancellation_message = await message.answer('You have canceled the form')
    await asyncio.sleep(1.5)

    # Get user info and clear state
    user_data = await state.get_data()
    await state.clear()
    prev_messages = user_data.get('prev_messages')

    await cancellation_message.delete()
    await message.delete()
    # Clear previous messages from the chat
    if prev_messages:
        for prev_message in prev_messages:
            try:
                await bot.delete_message(
                    chat_id=message.from_user.id,
                    message_id=prev_message.message_id
                )
            except TelegramBadRequest:
                pass


# Handler to confirm deletion of all info panels
@command_router.message(Command('delete_all'))
async def ask_to_delete_all_info_panels(message: Message) -> None:
    """Asks the user for confirmation before deleting all info panels."""
    await message.delete()
    await message.answer(
        'Are you sure you want to delete all info panels?',
        reply_markup=await create_delete_confirmation_keyboard(None)
    )


# Handler to get user's form (adults, rooms, children, sorting)
@command_router.message(Command('get_form'))
async def show_form_information(message: Message, db: DataBase) -> None:
    """Displays the user's form information with their selected preferences."""
    await message.delete()
    # Get user's form details from database
    user_details = await db.get_user_details(message.from_user.id)

    # If no user details are found, inform the user and exit the function
    if not user_details:
        await message.answer('You do not have any info panels. Use /start_form to create them.')
        return

    await message.answer("<b>Here's a summary of your selected preferences:</b>")
    await asyncio.sleep(0.5)

    for user_detail in user_details:
        # Format the summary text with the user's preferences
        text = (
            f"👨 Adults: {user_detail.get('adults')}\n"
            f"🛌 Rooms: {user_detail.get('rooms')}\n"
            f"🧑‍ Children: {user_detail.get('children')}\n"
            f"👶 Ages of Children: {', '.join(map(str, user_detail.get('children_age')))}\n"
            f"🔝 Sorting Preference: {SORT_OPTIONS_DESCRIPTIONS.get(user_detail.get('order_by'))}"
        )

        # Send the formatted summary text to the user
        await message.answer(
            text=text
        )
        await asyncio.sleep(0.5)


@command_router.message(Command('get_excel'))
async def ask_excel_preferences(message: Message) -> None:
    """Asks the user for his preferences on how to sort data in the Excel table."""
    await message.delete()
    await message.answer(
        'How would you like to sort data in your excel table?',
        reply_markup=await create_excel_keyboard()
    )


# Handler to refresh all info panels
@command_router.message(Command('refresh_all'))
async def refresh_all_info_panels(message: Message, bot: Bot, db: DataBase) -> None:
    """Refreshes user's info panels, deletes expired ones, and updates the database."""
    await message.delete()
    # Get all information panels and forms based on the user id
    forms_info_panels = await db.get_all_forms_info_panels(message.from_user.id)

    # If no info panels exist, inform the user and exit the function
    if not forms_info_panels:
        await message.answer('You do not have any info panels. Use /start_form to create them.')
        return

    # List to store info panels and forms that are still valid
    existing_forms_info_panels = []
    # List to store tasks for asynchronous execution
    tasks = []

    # Loop over each info panel and form
    for form_info_panel in forms_info_panels:
        # Check if the check-in date has passed
        if datetime.date.today() > datetime.datetime.strptime(
                form_info_panel.get('check_in'), '%Y-%m-%d'
        ).date():
            # Attempt to delete the expired info panel message
            try:
                await bot.delete_message(
                    chat_id=message.from_user.id,
                    message_id=form_info_panel.get('message_id')
                )
            # If deletion fails, ignore and continue
            except TelegramBadRequest:
                pass
            # Delete the expired info panel from the database and continue loop
            await db.delete_info_panel(form_info_panel.get('info_panel_id'))
            await bot.send_message(
                chat_id=message.from_user.id,
                text=(
                    f"Data about {form_info_panel.get('destination')} from "
                    f"{await format_date(form_info_panel.get('check_in'))} "
                    f"to {await format_date(form_info_panel.get('check_out'))} has been expired. "
                    f"Info panel will be deleted."
                )
            )
            continue

        # Calculate the time since the last refresh
        last_refresh = datetime.datetime.strptime(form_info_panel.get('last_refresh'), "%Y-%m-%d %H:%M:%S.%f")
        time_since_last_refresh = datetime.datetime.now() - last_refresh

        # If the last refresh was less than 30 seconds ago, inform the user and continue loop
        if time_since_last_refresh < datetime.timedelta(seconds=MIN_REFRESH_TIME):
            await bot.send_message(
                chat_id=message.from_user.id,
                text=(
                    f'You cannot refresh info panel with {form_info_panel.get('destination')} from '
                    f'{form_info_panel.get('check_in')} to {form_info_panel.get('check_out')} for next '
                    f'{MIN_REFRESH_TIME - time_since_last_refresh.seconds} seconds.'
                )
            )
            continue

        # Create a task to parse hotels
        task = asyncio.create_task(
            run_in_executor(
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
        )
        tasks.append(task)
        # Add valid info panel and form
        existing_forms_info_panels.append(form_info_panel)

    # Set the caption to 'Refreshing...' for all existing info panels
    for form_info_panel in existing_forms_info_panels:
        await bot.edit_message_caption(
            message_id=form_info_panel.get('message_id'),
            caption='<b>Refreshing...</b>',
            chat_id=message.from_user.id
        )

    # Gather results from all the tasks
    hotels = await asyncio.gather(*tasks)

    # Update each info panel with the new data
    for hotels_info, form_info_panel in zip(hotels, existing_forms_info_panels):
        # Inform user that hotel information is missing and continue loop
        if not hotels_info:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=(
                    f'No information about {form_info_panel.get('destination')} from '
                    f'{form_info_panel.get('check_in')} to {form_info_panel.get('check_out')} is available right now.'
                )
            )
            continue

        # Get the number of hotels found
        hotels_info_length = len(hotels_info)

        # Edit the message media with the new hotel information
        await bot.edit_message_media(
            chat_id=message.from_user.id,
            message_id=form_info_panel.get('message_id'),
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
            form_info_panel.get('info_panel_id'), hotels_info,
            hotels_info_length, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        )
        await asyncio.sleep(1)
