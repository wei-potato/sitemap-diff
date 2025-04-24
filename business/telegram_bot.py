from kernel.config import telegram_config

from telegram import Message, MessageEntity, Update, constants, \
    BotCommand, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, \
    filters, InlineQueryHandler, Application, CallbackContext, CallbackQueryHandler

import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re


tel_bots = []
commands = [
    BotCommand(command='help', description='Show help message'),
    # BotCommand(command='token', description='please input your replicate token, you should sign up and get your API token: https://replicate.com/account/api-tokens'),
]


async def post_init(application: Application) -> None:
    """
    Post initialization hook for the bot.
    """
    await application.bot.set_my_commands(commands)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    logging.info(update.message)

    id = str(message.from_user.id)
    logging.info(id)

    await help(update, context)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Shows the help menu.
    """
    lang = str(update.message.from_user.language_code)
    logging.info(lang)
    help_text = f"Hello, {update.message.from_user.first_name}"
    await update.message.reply_text(help_text, disable_web_page_preview=True)


async def run(token):
    """
    Runs the bot indefinitely until the user presses Ctrl+C
    """
    global tel_bots
    application = ApplicationBuilder() \
        .token(token) \
        .concurrent_updates(True) \
        .connect_timeout(30) \
        .read_timeout(30) \
        .write_timeout(30) \
        .post_init(post_init) \
        .build()

    bot_num = len(tel_bots)
    tel_bots.append(application.bot)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))

    await application.initialize()
    await application.start()
    logging.info("start up successful ……")
    await application.updater.start_polling(drop_pending_updates=True)

async def init_task():
    """|coro|
    以异步方式启动
    """
    logging.info("init vars and sd_webui end")


async def start_task(token):
    return await run(token)


def close_all():
    logging.info("db close")

