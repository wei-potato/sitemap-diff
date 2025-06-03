import sys
import logging
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

# 导入配置和RSS管理器
from config.config import domainlist
from services.rss.manager import RSSManager
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))
# 导入模型
from spider.webapp.model.session import Session
from spider.webapp.model.rs import RS
from spider.jobs.main import *
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("sitemap_monitor.log")
    ]
)


def extract_keyword_from_url(url: str) -> str:
    """
    从URL中提取关键词
    
    Args:
        url: 完整URL
        
    Returns:
        str: 提取的关键词
    """
    parsed_url = urlparse(url)
    path = parsed_url.path.strip('/')
    
    # 获取路径的最后一部分
    if path:
        last_part = path.split('/')[-1]
        # 将连字符替换为空格
        keyword = last_part.replace('-', ' ')
        return keyword
    return ""

def process_domain(domain: str, session) -> tuple[bool, list[str], list[str]]:
    """
    处理单个域名的sitemap，获取所有链接并返回所有URL和关键词
    
    Args:
        domain: 域名或直接的sitemap URL
        session: 当前会话对象
        
    Returns:
        tuple[bool, list[str], list[str]]: (是否成功, 所有URL列表, 提取的关键词列表)
    """
    rss_manager = RSSManager()
    
    # 如果domain不是直接的sitemap URL，则拼接sitemap.xml
    sitemap_url = domain if domain.endswith('.xml') else urljoin(domain, 'sitemap.xml')
    logging.info(f"处理域名: {domain}, sitemap URL: {sitemap_url}")
    
    # 下载sitemap（不需要比较，只需要获取所有URL）
    success, error_msg, file_path, _ = rss_manager.add_feed(sitemap_url)
    
    if not success:
        logging.error(f"处理域名 {domain} 失败: {error_msg}")
        return False, [], []
    
    # 获取sitemap中的所有URL
    all_urls = rss_manager.get_all_urls(sitemap_url)
    
    if not all_urls:
        logging.warning(f"域名 {domain} 的sitemap中没有找到任何URL")
        return True, [], []
    
    # 从所有URL中提取关键词
    word_list = []
    for url in all_urls:
        keyword = extract_keyword_from_url(url)
        if keyword:
            word_list.append(keyword)
    
    # 保存关键词到RS表
    for word in word_list:
        if word and RS.validate(word) and not RS.exists(word, session.uuid):
            rs = RS.create(
                rs=word,
                rk=f"game-{word}",
                session_uuid=session.uuid
            )
            RS.conn.session.add(rs)
    
    # 提交事务
    RS.conn.session.commit()
    
    logging.info(f"域名 {domain} 处理成功")
    logging.info(f"总共找到 {len(all_urls)} 个链接")
    logging.info(f"提取到 {len(word_list)} 个关键词")
    
    return True, all_urls, word_list

def main():
    """
    主函数，处理配置中的所有域名
    """
    # 创建会话
    sess = Session.create(
        geo="",
        timeframe="today 1-m"
    )
    
    results = {}
    
    for domain in domainlist:
        if not domain:
            continue
            
        success, new_urls, word_list = process_domain(domain, sess)
        results[domain] = {
            "success": success,
            "new_urls": new_urls,
            "word_list": word_list
        }
    
    # 打印结果摘要
    print("\n处理结果摘要:")
    for domain, result in results.items():
        status = "成功" if result["success"] else "失败"
        total_count = len(result["new_urls"])  # 现在是所有URL的数量
        word_count = len(result["word_list"])
        print(f"{domain}: {status}, 总链接数: {total_count}, 关键词数: {word_count}")
        
        if total_count > 0:
            print("所有链接:")
            for url in result["new_urls"]:  # 现在包含所有URL
                keyword = extract_keyword_from_url(url)
                print(f"  - {url}")
                if keyword:
                    print(f"    关键词: {keyword}")
            print("")
            
            print("提取的关键词列表:")
            for word in result["word_list"]:
                print(f"  - {word}")
            print("")
    rss = RS.conn.session.query(RS).filter(RS.session_uuid==sess.uuid).all()

    for rs in tqdm(rss, total=len(rss), desc='Collecting Multiline'):
        collect_multiline(rs, sess=sess)
    
    return results

if __name__ == "__main__":
    main()