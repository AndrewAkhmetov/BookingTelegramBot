from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault


# Set commands for the bot
async def set_commands(bot: Bot) -> None:
    commands = [
        BotCommand(
            command='start',
            description='Start bot'
        ),
        BotCommand(
            command='start_form',
            description='Start form'
        ),
        BotCommand(
            command='cancel',
            description='Cancel form'
        ),
        BotCommand(
            command='refresh_all',
            description='Refresh all info panels'
        ),
        BotCommand(
            command='delete_all',
            description='Delete all info panels'
        ),
        BotCommand(
            command='get_excel',
            description='Get information about all hotels in excel'
        ),
        BotCommand(
            command='get_form',
            description='Get form information'
        )
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
