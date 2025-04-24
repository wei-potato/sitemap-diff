from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
import logging
from .manager import RSSManager

rss_manager = RSSManager()

async def rss_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /rss 命令"""
    user = update.message.from_user
    chat_id = update.message.chat_id
    logging.info(f"收到RSS命令 - 用户: {user.username}(ID:{user.id}) 聊天ID: {chat_id}")

    if not context.args:
        logging.info("显示RSS命令帮助信息")
        await update.message.reply_text(
            "请使用以下命令：\n"
            "/rss list - 显示所有监控的sitemap\n"
            "/rss add URL - 添加sitemap监控（URL必须以sitemap.xml结尾）\n"
            "/rss del URL - 删除sitemap监控"
        )
        return

    cmd = context.args[0].lower()
    if cmd == 'list':
        logging.info("执行list命令")
        feeds = rss_manager.get_feeds()
        if not feeds:
            logging.info("RSS订阅列表为空")
            await update.message.reply_text("当前没有RSS订阅")
            return

        feed_list = "\n".join([f"- {feed}" for feed in feeds])
        logging.info(f"显示RSS订阅列表，共 {len(feeds)} 个")
        await update.message.reply_text(f"当前RSS订阅列表：\n{feed_list}")

    elif cmd == 'add':
        if len(context.args) < 2:
            logging.warning("add命令缺少URL参数")
            await update.message.reply_text("请提供sitemap.xml的URL\n例如：/rss add https://example.com/sitemap.xml")
            return

        url = context.args[1]
        if not url.endswith('sitemap.xml'):
            logging.warning(f"无效的sitemap URL: {url}")
            await update.message.reply_text("URL必须以sitemap.xml结尾")
            return

        logging.info(f"执行add命令，URL: {url}")
        success, error_msg = rss_manager.add_feed(url)
        if success:
            logging.info(f"成功添加sitemap监控: {url}")
            await update.message.reply_text(f"成功添加sitemap监控：{url}")
        else:
            logging.error(f"添加sitemap监控失败: {url} 原因: {error_msg}")
            await update.message.reply_text(f"添加sitemap监控失败：{url}\n原因：{error_msg}")

    elif cmd == 'del':
        if len(context.args) < 2:
            logging.warning("del命令缺少URL参数")
            await update.message.reply_text("请提供要删除的RSS订阅链接\n例如：/rss del https://example.com/feed.xml")
            return

        url = context.args[1]
        logging.info(f"执行del命令，URL: {url}")
        success, error_msg = rss_manager.remove_feed(url)
        if success:
            logging.info(f"成功删除RSS订阅: {url}")
            await update.message.reply_text(f"成功删除RSS订阅：{url}")
        else:
            logging.error(f"删除RSS订阅失败: {url} 原因: {error_msg}")
            await update.message.reply_text(f"删除RSS订阅失败：{url}\n原因：{error_msg}")

def register_commands(application: Application):
    """注册RSS相关的命令"""
    application.add_handler(CommandHandler('rss', rss_command))






