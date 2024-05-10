from dataclasses import dataclass
from environs import Env


# Define a dataclass to store database configuration
@dataclass
class DatabaseConfig:
    database: str


# Define a dataclass to store Telegram bot configuration
@dataclass
class TgBot:
    token: str


# Define a dataclass to store the overall application configuration
@dataclass
class Config:
    tg_bot: TgBot
    db_config: DatabaseConfig


# Function to load the application configuration from environment variables
def load_config(path: str) -> Config:
    env = Env()
    # Read environment variables from the specified path
    env.read_env(path)

    # Create and return a Config instance with the loaded settings
    return Config(
        tg_bot=TgBot(
            token=env('BOT_TOKEN')
        ),
        db_config=DatabaseConfig(
            database=env('DATABASE')
        )
    )
