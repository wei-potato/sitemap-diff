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
            return json.loads(self.feeds_file.read_text())
        except Exception as e:
            logging.error(f"读取RSS订阅列表失败: {e}")
            return []
