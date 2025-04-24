from core.config import telegram_config
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, Application
import logging
import asyncio

tel_bots = {}
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

    # 用token作为key存储bot实例
    tel_bots[token] = application.bot

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

async def scheduled_task(token):
    """定时任务"""
    await asyncio.sleep(5)

    # 直接通过token获取bot实例
    bot = tel_bots.get(token)
    if not bot:
        logging.error(f"未找到token对应的bot实例: {token}")
        return

    while True:
        try:
            from services.rss.commands import rss_manager, send_sitemap_to_channel, send_new_urls_to_channel
            feeds = rss_manager.get_feeds()
            logging.info(f"定时任务开始检查订阅源更新，共 {len(feeds)} 个订阅")

            for url in feeds:
                logging.info(f"正在检查订阅源: {url}")
                success, error_msg, dated_file, new_urls = rss_manager.add_feed(url)
                if success and dated_file:
                    context = ContextTypes.DEFAULT_TYPE(application=None, bot=bot)
                    send_result = await send_sitemap_to_channel(context, dated_file, url)
                    if send_result:
                        await send_new_urls_to_channel(context, url, new_urls)
                        logging.info(f"订阅源 {url} 更新成功，发现 {len(new_urls)} 个新URL")
                    else:
                        logging.warning(f"订阅源 {url} 更新成功，但发送到频道失败")
                else:
                    logging.warning(f"订阅源 {url} 更新失败: {error_msg}")

            logging.info("所有订阅源检查完成，等待下一次检查")
            await asyncio.sleep(3600)  # 每小时检查一次
        except Exception as e:
            logging.error(f"检查订阅源更新失败: {str(e)}")
            await asyncio.sleep(60)  # 出错后等待1分钟再试



