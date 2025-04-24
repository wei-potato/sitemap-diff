# Site Bot

一个支持 Telegram 和 Discord 的站点监控机器人。

## 环境要求

- Python 3.8+
- pip
- virtualenv

## 安装步骤

1. 克隆项目
```bash
git clone [项目地址]
cd site-bot
```

2. 创建并激活虚拟环境
```bash
# 创建虚拟环境
python -m venv venv

# Windows激活虚拟环境
venv\Scripts\activate

# Linux/Mac激活虚拟环境
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑.env文件，填入你的配置
# TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
# DISCORD_TOKEN="your_discord_token"
```

## 运行方式

1. 直接运行
```bash
python site-bot.py
```

2. 使用启动脚本（推荐）
```bash
# 添加执行权限
chmod +x restart.sh

# 运行脚本
./restart.sh
```

## 日志查看

程序运行日志位于：
```bash
tail -f /tmp/site-bot.log
```

## 目录结构

```
project/
├── apps/                 # 应用入口层
│   ├── telegram_bot.py
│   └── discord_bot.py
├── core/                 # 核心配置层
│   └── config.py
├── services/            # 具体服务层
│   └── rss/            
├── storage/             # 数据存储层
└── site-bot.py         # 主程序入口
```

## 注意事项

1. 确保.env文件中配置了正确的bot token
2. 运行restart.sh前确保在项目根目录
3. 首次运行时需要创建虚拟环境并安装依赖