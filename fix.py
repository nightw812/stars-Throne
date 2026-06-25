import asyncio
from aiogram import Bot

BOT_TOKEN = "8955023620:AAFoQ4MXOEZry7wycq5RH2rV2zVVKj1nTLk"

async def main():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook удалён!")
    await bot.session.close()

asyncio.run(main())
