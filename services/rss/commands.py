import logging
from .manager import RSSManager
from pathlib import Path
from urllib.parse import urlparse
from core.config import telegram_config
from telegram import Update, Bot
from telegram.ext import ContextTypes, CommandHandler, Application

rss_manager = RSSManager()


async def send_update_notification(
    bot: Bot,
    url: str,
    new_urls: list[str],
    dated_file: Path | None,
    target_chat: str = None,
) -> None:
    """
    发送Sitemap更新通知，包括文件（如果可用）和新增URL列表。
    """
    chat_id = target_chat or telegram_config["target_chat"]
    if not chat_id:
        logging.error("未配置发送目标，请检查TELEGRAM_TARGET_CHAT环境变量")
        return

    domain = urlparse(url).netloc

    try:
        if dated_file and dated_file.exists():
            # 根据是否有新增URL，分别构造美化后的标题
            if new_urls:
                header_message = (
                    f"✨ {domain} ✨\n"
                    f"------------------------------------\n"
                    f"发现新增内容！ (共 {len(new_urls)} 条)\n"
                    f"来源: {url}\n"
                    f"------------------------------------"
                )
            else:
                header_message = (
                    f"✅ {domain}\n"
                    f"------------------------------------\n"
                    f"{domain} 今日sitemap\n"
                    f"来源: {url}\n"
                    f"------------------------------------"
                )
            await bot.send_document(
                chat_id=chat_id,
                document=dated_file,
                caption=header_message,
            )
            logging.info(f"已发送sitemap文件: {dated_file} for {url}")
            try:
                dated_file.unlink()  # 发送成功后删除
                logging.info(f"已删除临时sitemap文件: {dated_file}")
            except OSError as e:
                logging.error(f"删除文件失败: {dated_file}, Error: {str(e)}")
        else:
            # 没有文件时，发送美化标题文本
            if not new_urls:
                message = f"✅ {domain} 今日没有更新"
                await bot.send_message(
                    chat_id=chat_id, text=message, disable_web_page_preview=True
                )
            else:
                header_message = (
                    f"✨ {domain} ✨\n"
                    f"------------------------------------\n"
                    f"发现新增内容！ (共 {len(new_urls)} 条)\n"
                    f"来源: {url}\n"
                    f"------------------------------------"
                )
                await bot.send_message(
                    chat_id=chat_id, text=header_message, disable_web_page_preview=True
                )

        # 单独发送每个URL
        if new_urls:
            for u in new_urls:
                await bot.send_message(
                    chat_id=chat_id, text=u, disable_web_page_preview=False
                )
            logging.info(f"已发送 {len(new_urls)} 个新URL for {domain}")

            # 发送更新结束的消息
            end_message = (
                f"------------------------------------\n"
                f"✨ {domain} 更新推送完成 ✨\n"
                f"------------------------------------"
            )
            await bot.send_message(
                chat_id=chat_id, text=end_message, disable_web_page_preview=True
            )

    except Exception as e:
        logging.error(f"发送URL更新消息失败 for {url}: {str(e)}")


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
        # 检查URL是否包含sitemap关键词，不再强制要求.xml后缀
        if "sitemap" not in url.lower():
            logging.warning(f"无效的sitemap URL: {url} (URL需包含sitemap关键词)")
            await update.message.reply_text("URL必须以sitemap.xml结尾")
            return

        logging.info(f"执行add命令，URL: {url}")
        success, error_msg, dated_file, new_urls = rss_manager.add_feed(url)

        if success:
            if "已存在的feed更新成功" in error_msg:
                await update.message.reply_text(f"该sitemap已在监控列表中")
            else:
                await update.message.reply_text(f"成功添加sitemap监控：{url}")

            # 调用新的合并函数
            await send_update_notification(context.bot, url, new_urls, dated_file)
            logging.info(f"已尝试发送更新通知 for {url} after add command")

        else:
            if "今天已经更新过此sitemap" in error_msg:
                # 获取当前文件并发送给用户 (这部分是发送给命令发起者的，逻辑保持)
                try:
                    domain = urlparse(url).netloc
                    current_file = (
                        rss_manager.sitemap_dir / domain / "sitemap-current.xml"
                    )
                    if current_file.exists():
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,  # 发送给命令发起者
                            document=current_file,
                            caption=f"今天的Sitemap文件\nURL: {url}",
                        )
                        await update.message.reply_text(f"该sitemap今天已经更新过")
                        # 即使今天更新过，也尝试给频道发送一次通知（可能包含上次比较的结果）
                        # 注意：这里 dated_file 可能不存在，需要处理
                        _, _, dated_file_maybe, existing_new_urls = (
                            rss_manager.download_sitemap(url)
                        )  # 再次调用以获取文件和URL
                        if dated_file_maybe:
                            await send_update_notification(
                                context.bot, url, existing_new_urls, dated_file_maybe
                            )

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


# 确保移除了旧的 send_sitemap 和 send_new_urls 函数定义
