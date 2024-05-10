import asyncio
import datetime

import inflect
from aiogram.exceptions import TelegramBadRequest
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db_class import DataBase
from keyboards.inline_kayboards import (
    create_dates_prompting_keyboard, create_quantity_keyboard,
    create_age_keyboard, create_order_by_keyboard,
    create_info_panel
)
from parsers.booking_parser import parse_booking
from states.state import Form
from utils.utils import run_in_executor, format_date

# Initialize a router
form_router = Router()
# Initialize an inflect engine instance
p = inflect.engine()


# Handler to ask for a destination
@form_router.message(
    Form.destination,  F.text.regexp(r"^([a-zA-Z\u0080-\u024F]+(?:,\s*|-|\s|'))*[a-zA-Z\u0080-\u024F]*$")
)
async def process_destination(message: Message, state: FSMContext) -> None:
    """Requests the user to input their destination and validates the format."""
    user_data = await state.get_data()
    # Store the destination in the state
    destinations = [dest.strip() for dest in message.text.split(',') if dest.strip()]

    if len(destinations) + user_data.get('existing_panels_count') > 6:
        error_message = await message.answer('You cannot pick so many destinations')
        await asyncio.sleep(1.5)
        await error_message.delete()
        await message.delete()
    else:
        await state.update_data(destination=destinations)
        # Confirm the destination choice to the user
        confirmation_message = await message.answer(
            f"You have chosen {', '.join(destinations)} as your destination(s)"
        )
        await asyncio.sleep(0.5)
        # Move to the next state to ask for check-in date
        await state.set_state(Form.check_in)
        # Prompt the user to enter the check-in date
        check_in_prompt = await message.answer(
            'When would you like to check in?',
            reply_markup=await SimpleCalendar(locale='en_EN').start_calendar()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([message, confirmation_message, check_in_prompt])
        await state.update_data(prev_messages=prev_messages)


# Handler for incorrect destination format
@form_router.message(Form.destination)
async def process_unknown_destination(message: Message) -> None:
    """Informs the user that the entered destination format is incorrect and prompts for a valid destination."""
    error_message = await message.answer('The destination format is incorrect. Please enter a valid destination.')
    await asyncio.sleep(1.5)
    await message.delete()
    await error_message.delete()


# Handler to get a check-in date
@form_router.callback_query(Form.check_in, SimpleCalendarCallback.filter())
async def process_check_in_selection(
    callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext
) -> None:
    """Processes the check-in date selection from the calendar."""
    # Get the user's selected date from the calendar
    selected, date = await SimpleCalendar(locale='en_EN').process_selection(callback_query, callback_data)
    # Check if a date has been selected
    if selected:
        # Prevent selection of past dates by comparing with today's date
        if datetime.date.today() > date.date():
            # Notify the user and present the calendar again to select a valid date
            await callback_query.answer('You cannot pick this date')
            await callback_query.message.edit_reply_markup(
                reply_markup=await SimpleCalendar(locale='en_EN').start_calendar()
            )
            return

        await callback_query.message.delete()
        user_data = await state.get_data()
        # Update the state with the selected check-in date
        prev_check_ins = user_data.get('check_in')
        if prev_check_ins:
            prev_check_ins.append(date.strftime('%Y-%m-%d'))
            await state.update_data(check_in=prev_check_ins)
            await state.update_data(check_in_index=user_data.get('check_in_index') + 1)
        else:
            await state.update_data(check_in=[date.strftime('%Y-%m-%d')])
            await state.update_data(check_in_index=0)
        # Confirm the selected date to the user
        confirmation_message = await callback_query.message.answer(
            f'You have selected {date.strftime("%#d %B %Y")} as your check-in date.'
        )
        await asyncio.sleep(0.5)
        # Set the next state to collect the check-out date
        await state.set_state(Form.check_out)
        # Prompt the user to select the check-out date
        check_out_prompt = await callback_query.message.answer(
            'When would you like to check-out?',
            reply_markup=await SimpleCalendar(locale='en_EN').start_calendar()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([confirmation_message, check_out_prompt])
        await state.update_data(prev_messages=prev_messages)


# Handler to get a check-out date
@form_router.callback_query(Form.check_out, SimpleCalendarCallback.filter())
async def process_check_out_selection(
    callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext
) -> None:
    """Processes the check-out date selection from the calendar and asks user if he wants to add more dates."""
    # Get the user's selected date from the calendar
    selected, date = await SimpleCalendar(locale='en_EN').process_selection(callback_query, callback_data)
    # Check if a date has been selected
    if selected:
        user_data = await state.get_data()

        check_in = datetime.datetime.strptime(
                user_data.get('check_in')[user_data.get('check_in_index')], '%Y-%m-%d'
        ).date()

        # Ensure the check-out date is after the check-in date
        if date.date() <= check_in:
            await callback_query.answer('You cannot pick this date')
            await callback_query.message.edit_reply_markup(
                reply_markup=await SimpleCalendar(locale='en_EN').start_calendar()
            )
            return

        # Check if the date is within 90 days from the check-in date
        if date.date() > check_in + datetime.timedelta(days=90):
            await callback_query.answer("Reservations for more than 90 nights aren't possible.")
            await callback_query.message.edit_reply_markup(
                reply_markup=await SimpleCalendar(locale='en_EN').start_calendar()
            )
            return

        await callback_query.message.delete()
        # Update the state with the selected check-out date
        prev_check_outs = user_data.get('check_out')
        if prev_check_outs:
            prev_check_outs.append(date.strftime('%Y-%m-%d'))
            await state.update_data(check_out=prev_check_outs)
        else:
            await state.update_data(check_out=[date.strftime('%Y-%m-%d')])
        # Confirm the selected date to the user
        confirmation_message = await callback_query.message.answer(
            f'You have selected {date.strftime("%#d %B %Y")} as your check-out date.'
        )
        await asyncio.sleep(0.5)
        # Ask user if he wants to add more dates
        dates_prompt = await callback_query.message.answer(
            'Do you want to add more dates?',
            reply_markup=await create_dates_prompting_keyboard()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([confirmation_message, dates_prompt])
        await state.update_data(prev_messages=prev_messages)


# Handler to add more dates
@form_router.callback_query(F.data == 'add_dates')
async def add_more_dates(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Handles the user's decision to add dates to their form."""
    await callback_query.message.delete()
    # Get user data and previous messages
    user_data = await state.get_data()
    prev_messages = user_data.get('prev_messages')
    # Calculate if adding more dates would exceed the maximum allowed info panels
    if user_data.get('existing_panels_count') + (len(user_data.get('destination')) * (user_data.get(
            "check_in_index") + 2)) > 6:
        # Inform the user that they cannot pick more dates due to the limit
        dates_limit_message = await callback_query.message.answer(
            'You cannot pick more dates'
        )
        await asyncio.sleep(0.5)

        # Set the next state to collect the number of adults
        await state.set_state(Form.adults)
        adults_prompt = await callback_query.message.answer(
            'How many adults will be staying?',
            reply_markup=await create_quantity_keyboard()
        )
        # Keep track of the previous messages
        prev_messages.extend([dates_limit_message, adults_prompt])
        await state.update_data(prev_messages=prev_messages)
    else:
        # Set the check-in state to add another date
        await state.set_state(Form.check_in)
        # Prompt the user to enter the check-in date
        check_in_prompt = await callback_query.message.answer(
            'When would you like to check in?',
            reply_markup=await SimpleCalendar(locale='en_EN').start_calendar()
        )
        # Keep track of the previous messages
        prev_messages.append(check_in_prompt)
        await state.update_data(prev_messages=prev_messages)


# Handler if user does not want to add dates
@form_router.callback_query(F.data == 'dont_add_dates')
async def do_not_add_dates(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Handles the user's decision not to add dates to their form."""
    await callback_query.message.delete()

    user_data = await state.get_data()
    # Set the next state to collect the number of adults
    await state.set_state(Form.adults)
    adults_prompt = await callback_query.message.answer(
        'How many adults will be staying?',
        reply_markup=await create_quantity_keyboard()
    )
    # Keep track of the previous messages
    prev_messages = user_data.get('prev_messages')
    prev_messages.append(adults_prompt)
    await state.update_data(prev_messages=prev_messages)


# Handler for prompting the user to select a date, using calendar markup
@form_router.message(Form.check_in)
@form_router.message(Form.check_out)
async def process_check_in(message: Message) -> None:
    """Sends a reminder to the user to select a date from the calendar."""
    reminder_message = await message.answer('Select a date from the calendar')
    await asyncio.sleep(1.5)
    await message.delete()
    await reminder_message.delete()


# Handler for selecting the number of adults
@form_router.callback_query(Form.adults)
async def process_adults_selection(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Allows the user to select the number of adults for the booking."""
    # Get user's data
    user_data = await state.get_data()
    number_of_adults = user_data.get('adults', 1)

    # If the user presses on number button answer callback
    if callback_query.data == 'number':
        await callback_query.answer()
        return

    # Increase or decrease number, depending on callback data
    if callback_query.data == '+':
        number_of_adults += 1
    elif callback_query.data == '-':
        number_of_adults -= 1

    # Ensure the number of adults is within the allowed range
    if number_of_adults > 30 or number_of_adults < 1:
        await callback_query.answer('You can choose only between 1 and 30')
        return

    if callback_query.data == 'ok':
        await callback_query.message.delete()
        # Confirm the selected number of adults to the user
        confirmation_message = await callback_query.message.answer(
            f'You have selected {number_of_adults} adult(s).'
        )
        await asyncio.sleep(0.5)
        # Update the state with the selected number of adults
        await state.update_data(adults=number_of_adults)
        # Move to the next state to ask for the number of children
        await state.set_state(Form.children)
        children_prompt = await callback_query.message.answer(
            'How many children will be accompanying you?',
            reply_markup=await create_quantity_keyboard()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([confirmation_message, children_prompt])
        await state.update_data(prev_messages=prev_messages)
    else:
        # Update the reply markup to reflect the current number of adults
        await state.update_data(adults=number_of_adults)
        await callback_query.message.edit_reply_markup(
            reply_markup=await create_quantity_keyboard(number_of_adults)
        )


# Handler to get the number of children
@form_router.callback_query(Form.children)
async def process_children_selection(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Allows the user to select the number of children for the booking."""
    # Get user's data
    user_data = await state.get_data()
    number = user_data.get('children', 1)

    # If the user presses on number button answer callback
    if callback_query.data == 'number':
        await callback_query.answer()
        return

    # Increase or decrease the number of children
    if callback_query.data == '+':
        number += 1
    elif callback_query.data == '-':
        number -= 1

    # Ensure the number of children is within the allowed range
    if number > 30 or number < 0:
        await callback_query.answer('You can choose only between 0 and 30')
        return

    if callback_query.data == 'ok':
        await callback_query.message.delete()
        # Confirm the selected number of children to the user
        confirmation_message = await callback_query.message.answer(f'You have selected {number} child(ren).')
        await asyncio.sleep(0.5)
        # Update the state with the selected number of children
        await state.update_data(children=number)
        await state.update_data(children_age=[])
        # Get previous messages
        prev_messages = user_data.get('prev_messages')
        if number > 0:
            # Move to the next state to ask for the children's age
            await state.update_data(children_age_index=0)
            await state.set_state(Form.children_age)
            children_age_prompt = await callback_query.message.answer(
                f"What's the age of the 1st child?",
                reply_markup=await create_age_keyboard()
            )
            prev_messages.extend([confirmation_message, children_age_prompt])
        else:
            # Move straight the rooms state if no children have been selected
            await state.set_state(Form.rooms)
            rooms_prompt = await callback_query.message.answer(
                'How many rooms do you need?',
                reply_markup=await create_quantity_keyboard()
            )
            prev_messages.extend([confirmation_message, rooms_prompt])
        # Keep track of the previous messages
        await state.update_data(prev_messages=prev_messages)
    else:
        # Update the reply markup to reflect the current number of children
        await state.update_data(children=number)
        await callback_query.message.edit_reply_markup(
            reply_markup=await create_quantity_keyboard(number)
        )


# Handler to get the children's ages
@form_router.callback_query(Form.children_age)
async def process_children_age_selection(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Processes the age selection for each child and prompts for the next child's age or moves to room selection."""
    # Delete the previous prompting message
    await callback_query.message.delete()

    # Get user's data
    user_data = await state.get_data()
    children_age_index = user_data.get('children_age_index')
    children_age = user_data.get('children_age')
    children = user_data.get('children')

    # If the current child is the last one, finalize the age input process
    if children_age_index == children - 1:
        # Add the age of the last child to the list
        children_age.append(int(callback_query.data))
        # Update the state with the new list of children's ages
        await state.update_data(children_age=children_age)
        # Increment the child index
        children_age_index += 1
        # Confirm the selected age for a child
        confirmation_message = await callback_query.message.answer(
            f'Your {p.ordinal(children_age_index)} child is {callback_query.data} years old.'
        )
        await asyncio.sleep(0.5)
        # Move to the next state to ask for the number of rooms
        await state.set_state(Form.rooms)
        rooms_prompt = await callback_query.message.answer(
            'How many rooms do you need?',
            reply_markup=await create_quantity_keyboard()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([confirmation_message, rooms_prompt])
        await state.update_data(prev_messages=prev_messages)
    else:
        # If there are more children, continue the age input process
        # Add the age of the last child to the list
        children_age.append(int(callback_query.data))
        # Update the state with the new list of children's ages
        await state.update_data(children_age=children_age)
        # Increment the child index
        children_age_index += 1
        # Update the state with the new child index
        await state.update_data(children_age_index=children_age_index)
        # Confirm the selected age for a child
        confirmation_message = await callback_query.message.answer(
            f'Your {p.ordinal(children_age_index)} child is {callback_query.data} years old.'
        )
        await asyncio.sleep(0.5)
        # Prompt user for the age of the next child
        next_child_prompt = await callback_query.message.answer(
            f"What's the age of the {p.ordinal(children_age_index + 1)} child?",
            reply_markup=await create_age_keyboard()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([confirmation_message, next_child_prompt])
        await state.update_data(prev_messages=prev_messages)


# Handler to get the number of rooms
@form_router.callback_query(Form.rooms)
async def process_rooms_selection(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Allows the user to select the number of rooms for the booking."""
    # Get user's data
    user_data = await state.get_data()
    number = user_data.get('rooms', 1)

    # If the user presses on number button answer callback
    if callback_query.data == 'number':
        await callback_query.answer()
        return

    # Increase or decrease number, depending on callback data
    if callback_query.data == '+':
        number += 1
    elif callback_query.data == '-':
        number -= 1

    # Ensure the number of rooms is within the allowed range
    if number > 30 or number < 1:
        await callback_query.answer('You can choose only between 1 and 30')
        return

    if callback_query.data == 'ok':
        await callback_query.message.delete()
        # Confirm the selected number of rooms to the user
        confirmation_message = await callback_query.message.answer(f'You have selected {number} room(s).')
        await asyncio.sleep(0.5)
        # Update the state with the selected number of rooms
        await state.update_data(rooms=number)
        # Move to the next state to ask for sorting preference
        await state.set_state(Form.order_by)
        sorting_prompt = await callback_query.message.answer(
            'How would you like to sort the results?',
            reply_markup=await create_order_by_keyboard()
        )
        # Keep track of the previous messages
        prev_messages = user_data.get('prev_messages')
        prev_messages.extend([confirmation_message, sorting_prompt])
        await state.update_data(prev_messages=prev_messages)
    else:
        # Update the reply markup to reflect the current number of rooms
        await state.update_data(rooms=number)
        await callback_query.message.edit_reply_markup(
            reply_markup=await create_quantity_keyboard(number)
        )


# Handler to process the sorting preference selection
@form_router.callback_query(Form.order_by)
async def process_order_by_selection(callback_query: CallbackQuery, state: FSMContext, db: DataBase, bot: Bot) -> None:
    """Processes the user's sorting preference, finalizes the form submission and creates info panels."""
    await callback_query.message.delete()
    await state.update_data(order_by=callback_query.data)

    # Get user info and clear state
    user_data = await state.get_data()
    await state.clear()

    prev_messages = user_data.get('prev_messages')

    # Clear previous messages from the chat
    for message in prev_messages:
        try:
            await bot.delete_message(
                chat_id=callback_query.from_user.id,
                message_id=message.message_id
            )
        except TelegramBadRequest:
            pass

    # Notify the user that data is being collected
    collecting_data_message = await callback_query.message.answer('<b>Collecting data...</b>')
    # Create info panels
    await create_info_panels(user_data, bot, db)
    # Delete notifying message
    await collecting_data_message.delete()


# Function to create and send information panels to user
async def create_info_panels(user_data: dict, bot: Bot, db: DataBase) -> None:
    """Creates and sends information panels to user."""
    tasks = []
    # Create tasks for parsing hotel data
    for destination in user_data.get('destination'):
        for check_in, check_out in zip(user_data.get('check_in'), user_data.get('check_out')):
            task = asyncio.create_task(
                run_in_executor(
                    parse_booking,
                    destination,
                    check_in,
                    check_out,
                    user_data.get('adults'),
                    user_data.get('rooms'),
                    user_data.get('children'),
                    user_data.get('children_age'),
                    user_data.get('order_by')
                )
            )
            tasks.append(task)

    # Wait for all tasks to complete and gather results
    hotels = await asyncio.gather(*tasks)

    # Create current form counter
    cur_form = 0
    # Display new info panels for each hotel
    for destination in user_data.get('destination'):
        for check_in, check_out in zip(user_data.get('check_in'), user_data.get('check_out')):
            hotels_info = hotels[cur_form]

            # Inform user that hotel information is missing and continue loop
            if not hotels_info:
                await bot.send_message(
                    chat_id=user_data.get('user_id'),
                    text=f'No information about {destination} from {check_in} to {check_out} is available right now.'
                )
                # Increment the 'cur_form' counter by 1 to move to the next form
                cur_form += 1
                continue

            hotel_info_length = len(hotels_info)
            # Send a message with hotel information
            message = await bot.send_photo(
                chat_id=user_data.get('user_id'),
                photo=hotels_info[0].get('Photo'),
                caption=(
                    f'🏨 <b>{hotels_info[0].get("Name")}</b>\n'
                    f'💸 {hotels_info[0].get("Price")}$\n'
                    f'⭐️ {hotels_info[0].get("Rating") if hotels_info[0].get("Rating") else 'No rating'}\n\n'
                    f'🏙 <b>{destination}</b>\n'
                    f'🛬 {await format_date(check_in)}\n'
                    f'🛫 {await format_date(check_out)}'
                ),
                reply_markup=await create_info_panel(hotels_info[0].get('Link'), 1, hotel_info_length)
            )
            # Insert user data into database
            await db.insert_user_data(
                user_data.get('user_id'), message.message_id, hotel_info_length,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"), hotels_info,
                destination, check_in, check_out, user_data.get('adults'),
                user_data.get('children'), user_data.get('rooms'), user_data.get('order_by'),
                user_data.get('children_age')
            )
            # Increment the 'cur_form' counter by 1 to move to the next form
            cur_form += 1
            await asyncio.sleep(1)
