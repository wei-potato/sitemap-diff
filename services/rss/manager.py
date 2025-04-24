import json
import logging
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests

class RSSManager:
    def __init__(self):
        self.config_dir = Path("storage/rss/config")
        self.sitemap_dir = Path("storage/rss/sitemaps")  # 存储sitemap的基础目录
        self.feeds_file = self.config_dir / "feeds.json"
        self._init_directories()

    def _init_directories(self):
        """初始化必要的目录"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.sitemap_dir.mkdir(parents=True, exist_ok=True)

        if not self.feeds_file.exists():
            self.feeds_file.write_text('[]')

    def download_sitemap(self, url: str) -> tuple[bool, str]:
        """下载并保存sitemap文件

        Args:
            url: sitemap的URL

        Returns:
            tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            # 获取域名作为目录名
            domain = urlparse(url).netloc
            domain_dir = self.sitemap_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # 生成带日期的文件名
            date_str = datetime.now().strftime("%Y%m%d")
            file_name = f"sitemap_{date_str}.xml"
            file_path = domain_dir / file_name

            # 下载sitemap
            logging.info(f"开始下载sitemap: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # 保存文件
            file_path.write_text(response.text)
            logging.info(f"sitemap已保存到: {file_path}")

            return True, ""

        except requests.exceptions.RequestException as e:
            return False, f"下载失败: {str(e)}"
        except Exception as e:
            return False, f"保存失败: {str(e)}"

    def add_feed(self, url: str) -> tuple[bool, str]:
        """添加sitemap监控

        Args:
            url: sitemap的URL

        Returns:
            tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            logging.info(f"尝试添加sitemap监控: {url}")

            # 验证是否已存在
            feeds = self.get_feeds()
            if url in feeds:
                logging.warning(f"sitemap已存在: {url}")
                return False, "该sitemap已在监控列表中"

            # 尝试下载sitemap
            success, error_msg = self.download_sitemap(url)
            if not success:
                return False, error_msg

            # 添加到监控列表
            feeds.append(url)
            self.feeds_file.write_text(json.dumps(feeds, indent=2))
            logging.info(f"成功添加sitemap监控: {url}")

            return True, ""

        except Exception as e:
            logging.error(f"添加sitemap监控失败: {url}", exc_info=True)
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

    def get_feeds(self) -> list:
        """获取所有监控的feeds"""
        try:
            content = self.feeds_file.read_text()
            return json.loads(content)
        except Exception as e:
            logging.error("读取feeds文件失败", exc_info=True)
            return []




