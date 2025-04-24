from core.config import telegram_config
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, Application
import logging

tel_bots = []
commands = [
    BotCommand(command='help', description='Show help message'),
]

async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await help(update, context)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = f"Hello, {update.message.from_user.first_name}"
    await update.message.reply_text(help_text, disable_web_page_preview=True)

async def run(token):
    global tel_bots
    application = ApplicationBuilder() \
        .token(token) \
        .concurrent_updates(True) \
        .post_init(post_init) \
        .build()

    tel_bots.append(application.bot)

    # 基础命令
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))
    
    # 从services加载其他命令
    from services.rss.commands import register_commands
    register_commands(application)

    await application.initialize()
    await application.start()
    logging.info("Telegram bot startup successful")
    await application.updater.start_polling(drop_pending_updates=True)

async def init_task():
    logging.info("Initializing Telegram bot")

async def start_task(token):
    return await run(token)

def close_all():
    logging.info("Closing Telegram bot")