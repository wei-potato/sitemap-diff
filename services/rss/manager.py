import json
import logging
from pathlib import Path

class RSSManager:
    def __init__(self):
        self.config_dir = Path("storage/rss/config")
        self.sitemap_dir = Path("storage/rss/sitemaps")
        self.feeds_file = self.config_dir / "feeds.json"
        self._init_directories()

    def _init_directories(self):
        """初始化必要的目录"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.sitemap_dir.mkdir(parents=True, exist_ok=True)

        if not self.feeds_file.exists():
            self.feeds_file.write_text('[]')

    def get_feeds(self):
        """获取所有RSS订阅"""
        try:
            logging.info(f"正在读取RSS订阅列表: {self.feeds_file}")
            feeds = json.loads(self.feeds_file.read_text())
            logging.info(f"成功读取RSS订阅列表，共 {len(feeds)} 个订阅")
            return feeds
        except Exception as e:
            logging.error(f"读取RSS订阅列表失败: {e}", exc_info=True)
            return []

    def add_feed(self, url: str) -> tuple[bool, str]:
        """添加RSS订阅

        Args:
            url: RSS订阅链接

        Returns:
            tuple[bool, str]: (是否添加成功, 错误信息)
        """
        try:
            logging.info(f"尝试添加RSS订阅: {url}")
            feeds = self.get_feeds()

            if url in feeds:
                logging.warning(f"RSS订阅已存在: {url}")
                return False, "该RSS订阅已存在"

            feeds.append(url)
            logging.info(f"正在写入RSS订阅到文件: {self.feeds_file}")
            self.feeds_file.write_text(json.dumps(feeds, indent=2))
            logging.info(f"成功添加RSS订阅: {url}")
            return True, ""
        except Exception as e:
            logging.error(f"添加RSS订阅失败: {url}", exc_info=True)
            return False, f"添加失败: {str(e)}"

    def remove_feed(self, url: str) -> tuple[bool, str]:
        """删除RSS订阅

        Args:
            url: RSS订阅链接

        Returns:
            tuple[bool, str]: (是否删除成功, 错误信息)
        """
        try:
            logging.info(f"尝试删除RSS订阅: {url}")
            feeds = self.get_feeds()

            if url not in feeds:
                logging.warning(f"RSS订阅不存在: {url}")
                return False, "该RSS订阅不存在"

            feeds.remove(url)
            logging.info(f"正在写入RSS订阅到文件: {self.feeds_file}")
            self.feeds_file.write_text(json.dumps(feeds, indent=2))
            logging.info(f"成功删除RSS订阅: {url}")
            return True, ""
        except Exception as e:
            logging.error(f"删除RSS订阅失败: {url}", exc_info=True)
            return False, f"删除失败: {str(e)}"


