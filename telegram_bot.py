# telegram_bot.py
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
import asyncio
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

# Token do bot e ID do grupo obtidos do arquivo .env
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_ID = os.getenv('GROUP_CHAT_ID')
mensagem = "Olá time CHIP! Um novo chamado do TRT foi reconhecido."

async def enviar_mensagem():
    bot = Bot(token=TOKEN)  # Inicializa o bot
    await bot.send_message(chat_id=GROUP_ID, text=mensagem, parse_mode=ParseMode.HTML)  # Enviar msg pro grupo

def notificar_telegram():
    asyncio.run(enviar_mensagem())