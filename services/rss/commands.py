from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
import logging
from .manager import RSSManager

rss_manager = RSSManager()

async def rss_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /rss 命令"""
    if not context.args:
        await update.message.reply_text("请使用以下命令：\n/rss list - 显示所有订阅\n/rss add URL - 添加订阅\n/rss del URL - 删除订阅")
        return

    cmd = context.args[0].lower()
    if cmd == 'list':
        feeds = rss_manager.get_feeds()
        if not feeds:
            await update.message.reply_text("当前没有RSS订阅")
            return

        feed_list = "\n".join([f"- {feed}" for feed in feeds])
        await update.message.reply_text(f"当前RSS订阅列表：\n{feed_list}")

def register_commands(application: Application):
    """注册RSS相关的命令"""
    application.add_handler(CommandHandler('rss', rss_command))
