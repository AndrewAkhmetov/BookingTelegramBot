import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.methods import DeleteWebhook

from config_data.config import load_config
from keyboards.set_commands import set_commands
from handlers import commands, handlers, state_handlers
from database.db_class import DataBase
from utils.utils import executor_shutdown

# Load configuration from the '.env' file
config = load_config('.env')

# Initialize the Dispatcher
dp = Dispatcher()
# Initialize the Bot
bot = Bot(config.tg_bot.token, parse_mode='HTML')
# Initialize the connection to the database
db = DataBase(config.db_config.database)


async def main() -> None:
    # Create the database tables if they don't exist
    await db.create_db()
    # Include handlers into the dispatcher
    dp.include_routers(commands.command_router, handlers.router, state_handlers.form_router)
    # Register the executor shutdown to be called on dispatcher shutdown
    dp.shutdown.register(executor_shutdown)
    # Set the bot commands
    await set_commands(bot)
    # Remove any existing webhook to switch to polling
    await bot(DeleteWebhook(drop_pending_updates=True))
    # Start polling for updates from Telegram
    await dp.start_polling(bot, db=db)


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
