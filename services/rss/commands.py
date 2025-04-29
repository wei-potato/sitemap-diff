from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
import logging
from .manager import RSSManager
from pathlib import Path
from urllib.parse import urlparse
from core.config import telegram_config

rss_manager = RSSManager()


async def send_sitemap(bot, file_path: Path, url: str, target_chat: str = None) -> bool:
    """发送sitemap文件到指定目标

    Args:
        bot: Telegram bot实例
        file_path: sitemap文件路径
        url: sitemap来源URL
        target_chat: 发送目标ID,默认使用配置中的target_chat
    """
    chat_id = target_chat or telegram_config["target_chat"]
    if not chat_id:
        logging.error("未配置发送目标，请检查TELEGRAM_TARGET_CHAT环境变量")
        return False

    try:
        await bot.send_document(
            chat_id=chat_id, document=file_path, caption=f"新的Sitemap文件\nURL: {url}"
        )
        file_path.unlink()
        logging.info(f"已发送sitemap文件并删除: {file_path}")
        return True
    except Exception as e:
        logging.error(f"发送文件失败: {str(e)}")
        return False


async def send_new_urls(
    bot, url: str, new_urls: list[str], target_chat: str = None
) -> None:
    """发送新增的URL到指定目标，优化视觉分隔

    Args:
        bot: Telegram bot实例
        url: sitemap来源URL
        new_urls: 新增的URL列表
        target_chat: 发送目标ID,默认使用配置中的target_chat
    """
    chat_id = target_chat or telegram_config["target_chat"]
    if not chat_id:
        logging.error("未配置发送目标，请检查TELEGRAM_TARGET_CHAT环境变量")
        return

    try:
        # 从URL中提取域名
        domain = urlparse(url).netloc

        if not new_urls:
            # 如果没有新URL，发送简洁通知
            message = f"✅ {domain} 今日没有更新"
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                disable_web_page_preview=True
            )
        else:
            # 如果有新URL，发送一个美观的标题作为分隔
            header_message = (
                f"✨ {domain} ✨\n"
                f"------------------------------------\n"
                f"发现新增内容！\n"
                f"来源: {url}\n"
                f"------------------------------------"
            )
            await bot.send_message(
                chat_id=chat_id,
                text=header_message,
                disable_web_page_preview=True  # 标题禁用预览
            )

            # 单独发送每个URL以利用预览
            for u in new_urls:
                await bot.send_message(
                    chat_id=chat_id,
                    text=u,
                    disable_web_page_preview=False  # URL启用预览
                )
            # (可选) 可以在所有URL发送完毕后加一个结束分隔符，但可能会过于冗长
            await bot.send_message(chat_id=chat_id, text="--- 更新结束 ---", disable_web_page_preview=True)

    except Exception as e:
        logging.error(f"发送新增URL失败: {str(e)}")


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
    if cmd == "list":
        logging.info("执行list命令")
        feeds = rss_manager.get_feeds()
        if not feeds:
            logging.info("RSS订阅列表为空")
            await update.message.reply_text("当前没有RSS订阅")
            return

        feed_list = "\n".join([f"- {feed}" for feed in feeds])
        logging.info(f"显示RSS订阅列表，共 {len(feeds)} 个")
        await update.message.reply_text(f"当前RSS订阅列表：\n{feed_list}")

    elif cmd == "add":
        if len(context.args) < 2:
            logging.warning("add命令缺少URL参数")
            await update.message.reply_text(
                "请提供sitemap.xml的URL\n例如：/rss add https://example.com/sitemap.xml"
            )
            return

        url = context.args[1]
        if not url.endswith("sitemap.xml"):
            logging.warning(f"无效的sitemap URL: {url}")
            await update.message.reply_text("URL必须以sitemap.xml结尾")
            return

        logging.info(f"执行add命令，URL: {url}")
        success, error_msg, dated_file, new_urls = rss_manager.add_feed(
            url
        )  # 只改这一行，接收new_urls

        if success:
            if "已存在的feed更新成功" in error_msg:
                await update.message.reply_text(f"该sitemap已在监控列表中")
            else:
                await update.message.reply_text(f"成功添加sitemap监控：{url}")

            # 如果有新文件，发送到目标
            if dated_file:
                send_result = await send_sitemap(context.bot, dated_file, url)
                if send_result:
                    await send_new_urls(context.bot, url, new_urls)
                    logging.info(f"已发送sitemap: {url}")
                else:
                    await update.message.reply_text(f"文件添加成功，但发送失败")
                    logging.error(f"发送sitemap失败: {url}")
        else:
            if "今天已经更新过此sitemap" in error_msg:
                # 获取当前文件并发送给用户
                try:
                    domain = urlparse(url).netloc
                    current_file = (
                        rss_manager.sitemap_dir / domain / "sitemap-current.xml"
                    )
                    if current_file.exists():
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=current_file,
                            caption=f"今天的Sitemap文件\nURL: {url}",
                        )
                        await update.message.reply_text(f"该sitemap今天已经更新过")
                    else:
                        await update.message.reply_text(f"该sitemap今天已经更新过")
                except Exception as e:
                    logging.error(f"发送文件给用户失败: {str(e)}")
                    await update.message.reply_text(f"该sitemap今天已经更新过")
            else:
                logging.error(f"添加sitemap监控失败: {url} 原因: {error_msg}")
                await update.message.reply_text(
                    f"添加sitemap监控失败：{url}\n原因：{error_msg}"
                )

    elif cmd == "del":
        if len(context.args) < 2:
            logging.warning("del命令缺少URL参数")
            await update.message.reply_text(
                "请提供要删除的RSS订阅链接\n例如：/rss del https://example.com/feed.xml"
            )
            return

        url = context.args[1]
        logging.info(f"执行del命令，URL: {url}")
        success, error_msg = rss_manager.remove_feed(url)
        if success:
            logging.info(f"成功删除RSS订阅: {url}")
            await update.message.reply_text(f"成功删除RSS订阅：{url}")
        else:
            logging.error(f"删除RSS订阅失败: {url} 原因: {error_msg}")
            await update.message.reply_text(
                f"删除RSS订阅失败：{url}\n原因：{error_msg}"
            )


def register_commands(application: Application):
    """注册RSS相关的命令"""
    application.add_handler(CommandHandler("rss", rss_command))
