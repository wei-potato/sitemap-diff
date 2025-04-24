from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
import logging

async def rss_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /rss 命令"""
    await update.message.reply_text("RSS功能正在开发中...")

def register_commands(application: Application):
    """注册RSS相关的命令"""
    application.add_handler(CommandHandler('rss', rss_command))