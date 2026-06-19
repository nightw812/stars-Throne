import asyncio
from aiogram import Bot

BOT_TOKEN = "8904034562:AAGs3I8oprdPkdzRq7_Fqcbku0lAkG5k6pg"

async def main():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook удалён!")
    await bot.session.close()

asyncio.run(main())