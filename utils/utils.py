import asyncio
from datetime import datetime
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor

from utils.constants import MAX_WORKERS


# Create a ThreadPoolExecutor with a maximum number of workers from constants
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)


# Function to run a given function in the executor
async def run_in_executor(func: Callable[..., Any], *args: Any) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, func, *args)


# Function to shut down the executor
async def executor_shutdown() -> None:
    executor.shutdown(wait=True)


# Function to format a date string
async def format_date(date: str) -> str:
    return datetime.strptime(date, '%Y-%m-%d').strftime('%#d %B %Y')
