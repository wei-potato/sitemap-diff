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
            self.feeds_file.write_text("[]")

    def download_sitemap(self, url: str) -> tuple[bool, str, Path | None, list[str]]:
        """下载并保存sitemap文件

        Args:
            url: sitemap的URL

        Returns:
            tuple[bool, str, Path | None, list[str]]: (是否成功, 错误信息, 带日期的文件路径, 新增的URL列表)
        """
        try:
            # 获取域名作为目录名
            logging.info(f"尝试下载sitemap: {url}")
            domain = urlparse(url).netloc
            domain_dir = self.sitemap_dir / domain
            domain_dir.mkdir(parents=True, exist_ok=True)

            # 检查今天是否已经更新过
            last_update_file = domain_dir / "last_update.txt"
            today = datetime.now().strftime("%Y%m%d")
            logging.info(f"今天的日期: {today}")

            # 保存文件
            current_file = domain_dir / "sitemap-current.xml"
            latest_file = domain_dir / "sitemap-latest.xml"
            dated_file = domain_dir / f"{domain}_sitemap_{today}.xml"

            if last_update_file.exists():
                last_date = last_update_file.read_text().strip()
                logging.info(f"上次更新日期: {last_date}")
                if last_date == today:
                    if (
                        dated_file.exists()
                        and current_file.exists()
                        and latest_file.exists()
                    ):
                        current_content = current_file.read_text()
                        latest_content = latest_file.read_text()
                        new_urls = self.compare_sitemaps(
                            current_content, latest_content
                        )
                        return True, "今天已经更新过此sitemap, 但没发送", dated_file, new_urls
                    return (
                        dated_file.exists(),
                        "今天已经更新过此sitemap",
                        dated_file,
                        [],
                    )

            # 下载新文件
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            new_urls = []
            # 如果存在current文件，比较差异
            if current_file.exists():
                old_content = current_file.read_text()
                new_urls = self.compare_sitemaps(response.text, old_content)
                current_file.replace(latest_file)

            # 保存新文件
            current_file.write_text(response.text)
            dated_file.write_text(response.text)  # 临时文件，用于发送到频道后删除

            # 更新最后更新日期
            last_update_file.write_text(today)

            logging.info(f"sitemap已保存到: {current_file}")
            return True, "", dated_file, new_urls  # 只添加新URLs返回

        except requests.exceptions.RequestException as e:
            return False, f"下载失败: {str(e)}", None, []  # 只添加空列表返回
        except Exception as e:
            return False, f"保存失败: {str(e)}", None, []  # 只添加空列表返回

    def add_feed(self, url: str) -> tuple[bool, str, Path | None, list[str]]:
        """添加sitemap监控

        Args:
            url: sitemap的URL

        Returns:
            tuple[bool, str, Path | None, list[str]]: (是否成功, 错误信息, 带日期的文件路径, 新增的URL列表)
        """
        try:
            logging.info(f"尝试添加sitemap监控: {url}")

            # 验证是否已存在
            feeds = self.get_feeds()
            if url not in feeds:
                # 如果是新的feed，先尝试下载
                success, error_msg, dated_file, new_urls = self.download_sitemap(url)
                if not success:
                    return False, error_msg, None, []

                # 添加到监控列表
                feeds.append(url)
                self.feeds_file.write_text(json.dumps(feeds, indent=2))
                logging.info(f"成功添加sitemap监控: {url}")
                return True, "", dated_file, new_urls
            else:
                # 如果feed已存在，仍然尝试下载（可能是新的一天）
                success, error_msg, dated_file, new_urls = self.download_sitemap(url)
                if not success:
                    return False, error_msg, None, []
                return True, "已存在的feed更新成功", dated_file, new_urls

        except Exception as e:
            logging.error(f"添加sitemap监控失败: {url}", exc_info=True)
            return False, f"添加失败: {str(e)}", None, []

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

    def compare_sitemaps(self, current_content: str, old_content: str) -> list[str]:
        """比较新旧sitemap，返回新增的URL列表"""
        try:
            from xml.etree import ElementTree as ET

            current_root = ET.fromstring(current_content)
            old_root = ET.fromstring(old_content)

            current_urls = set()
            old_urls = set()

            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            for url in current_root.findall(".//ns:url/ns:loc", ns):
                current_urls.add(url.text)

            for url in old_root.findall(".//ns:url/ns:loc", ns):
                old_urls.add(url.text)

            return list(current_urls - old_urls)
        except Exception as e:
            logging.error(f"比较sitemap失败: {str(e)}")
            return []
    def get_all_urls(self, sitemap_url: str) -> list[str]:
        """
        从sitemap URL中获取所有URL
        
        Args:
            sitemap_url: sitemap的URL
            
        Returns:
            list[str]: 所有URL的列表
        """
        try:
            # 设置请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
            
            # 发送请求获取sitemap内容
            response = requests.get(sitemap_url, timeout=30, headers=headers)
            response.raise_for_status()
            
            return self._parse_sitemap_content(response.text, sitemap_url)
            
        except requests.RequestException as e:
            logging.error(f"请求sitemap失败: {sitemap_url}, 错误: {e}")
            return []
        except Exception as e:
            logging.error(f"处理sitemap时发生未知错误: {sitemap_url}, 错误: {e}")
            return []
    
    def _parse_sitemap_content(self, content: str, base_url: str = "") -> list[str]:
        """
        解析sitemap内容，提取所有URL
        
        Args:
            content: sitemap的XML内容
            base_url: 基础URL，用于日志记录
            
        Returns:
            list[str]: 所有URL的列表
        """
        from xml.etree import ElementTree as ET
        
        urls = []
        
        try:
            # 解析XML
            root = ET.fromstring(content)
            
            # 定义命名空间
            ns = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            
            # 检查是否是sitemap索引文件（包含其他sitemap链接）
            sitemap_elements = root.findall('.//sitemap:sitemap', ns)
            if sitemap_elements:
                logging.info(f"发现sitemap索引文件: {base_url}，包含 {len(sitemap_elements)} 个子sitemap")
                # 这是一个sitemap索引文件，需要递归获取所有子sitemap的URL
                for sitemap_elem in sitemap_elements:
                    loc_elem = sitemap_elem.find('sitemap:loc', ns)
                    if loc_elem is not None and loc_elem.text:
                        child_sitemap_url = loc_elem.text.strip()
                        logging.info(f"正在处理子sitemap: {child_sitemap_url}")
                        # 递归获取子sitemap的URL
                        child_urls = self.get_all_urls(child_sitemap_url)
                        urls.extend(child_urls)
                        logging.info(f"从子sitemap获取到 {len(child_urls)} 个URL")
            else:
                # 这是一个普通的sitemap文件，直接提取URL
                url_elements = root.findall('.//sitemap:url', ns)
                logging.info(f"发现普通sitemap文件: {base_url}，包含 {len(url_elements)} 个URL")
                
                for url_elem in url_elements:
                    loc_elem = url_elem.find('sitemap:loc', ns)
                    if loc_elem is not None and loc_elem.text:
                        urls.append(loc_elem.text.strip())
            
            # 去重并返回
            unique_urls = list(set(urls))
            logging.info(f"总共获取到 {len(unique_urls)} 个唯一URL")
            return unique_urls
            
        except ET.ParseError as e:
            logging.error(f"解析sitemap XML失败: {base_url}, 错误: {e}")
            return []
        except Exception as e:
            logging.error(f"解析sitemap内容时发生错误: {base_url}, 错误: {e}")
            return []