from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
import logging
from .manager import RSSManager
from pathlib import Path
from urllib.parse import urlparse

rss_manager = RSSManager()
RSS_CHANNEL = "@h5gamerss"  # 固定频道ID

async def check_bot_channel_admin(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """检查机器人是否是频道管理员"""
    try:
        # 获取机器人在频道中的成员信息
        chat_member = await context.bot.get_chat_member(
            chat_id=RSS_CHANNEL,
            user_id=context.bot.id
        )
        return chat_member.status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f"检查机器人权限失败: {str(e)}")
        return False

async def send_sitemap_to_channel(context: ContextTypes.DEFAULT_TYPE, file_path: Path, url: str) -> bool:
    """发送sitemap文件到频道"""
    try:
        # 先检查机器人权限
        if not await check_bot_channel_admin(context):
            raise Exception("机器人不是频道管理员，请先将机器人添加为频道管理员")

        # 发送文件
        await context.bot.send_document(
            chat_id=RSS_CHANNEL,
            document=file_path,
            caption=f"新的Sitemap文件\nURL: {url}"
        )
        # 发送成功后删除临时文件
        file_path.unlink()
        logging.info(f"已发送sitemap文件到频道并删除: {file_path}")
        return True
    except Exception as e:
        logging.error(f"发送文件到频道失败: {str(e)}")
        return False, str(e)

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
        success, error_msg, dated_file = rss_manager.add_feed(url)

        if success:
            if "已存在的feed更新成功" in error_msg:
                await update.message.reply_text(f"该sitemap已在监控列表中")
            else:
                await update.message.reply_text(f"成功添加sitemap监控：{url}")

            # 如果有新文件，发送到频道
            if dated_file:
                send_result = await send_sitemap_to_channel(context, dated_file, url)
                if isinstance(send_result, tuple):  # 发送失败带错误信息
                    success, error_msg = send_result
                    await update.message.reply_text(f"文件添加成功，但发送到频道失败：{error_msg}\n请确保机器人已被添加为频道 {RSS_CHANNEL} 的管理员")
                    logging.error(f"发送sitemap到频道失败: {url}, 原因: {error_msg}")
                elif send_result:  # 发送成功
                    logging.info(f"已发送sitemap到频道: {url}")
                else:  # 发送失败无错误信息
                    await update.message.reply_text(f"文件添加成功，但发送到频道失败\n请确保机器人已被添加为频道 {RSS_CHANNEL} 的管理员")
                    logging.error(f"发送sitemap到频道失败: {url}")
        else:
            if "今天已经更新过此sitemap" in error_msg:
                # 获取当前文件并发送给用户
                try:
                    domain = urlparse(url).netloc
                    current_file = rss_manager.sitemap_dir / domain / "sitemap-current.xml"
                    if current_file.exists():
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=current_file,
                            caption=f"今天的Sitemap文件\nURL: {url}"
                        )
                        await update.message.reply_text(f"该sitemap今天已经更新过")
                    else:
                        await update.message.reply_text(f"该sitemap今天已经更新过")
                except Exception as e:
                    logging.error(f"发送文件给用户失败: {str(e)}")
                    await update.message.reply_text(f"该sitemap今天已经更新过")
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










