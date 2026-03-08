"""
闲鱼消息 CLI 工具
基于 Click 框架的命令行工具
"""
import os
import sys


import asyncio
import json
from pathlib import Path

import click
from loguru import logger
from dotenv import load_dotenv

from .api import XianyuAPI
from .websocket import XianyuWebSocket


# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


def load_api() -> XianyuAPI:
    """加载 API 实例"""
    load_dotenv()
    cookies_str = os.getenv("COOKIES_STR")
    
    if not cookies_str:
        click.echo("错误: 未配置 COOKIES_STR，请先运行 'xianyu config set-cookies'", err=True)
        sys.exit(1)
    
    return XianyuAPI(cookies_str)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """闲鱼消息管理 CLI 工具 🐟"""
    pass


@cli.group()
def config():
    """配置管理"""
    pass


@config.command(name="set-cookies")
@click.argument("cookies")
def set_cookies(cookies: str):
    """设置 Cookie 字符串"""
    env_path = Path(".env")
    
    # 如果 .env 不存在，创建它
    if not env_path.exists():
        env_path.touch()
    
    # 读取现有内容
    existing = ""
    if env_path.exists():
        existing = env_path.read_text()
    
    # 更新或添加 COOKIES_STR
    lines = existing.split('\n')
    found = False
    new_lines = []
    
    for line in lines:
        if line.startswith('COOKIES_STR='):
            new_lines.append(f'COOKIES_STR={cookies}')
            found = True
        elif line.strip():
            new_lines.append(line)
    
    if not found:
        new_lines.append(f'COOKIES_STR={cookies}')
    
    env_path.write_text('\n'.join(new_lines))
    click.echo("✓ Cookie 已保存到 .env 文件")


@config.command(name="show")
def show_config():
    """显示当前配置"""
    load_dotenv()
    cookies = os.getenv("COOKIES_STR", "")
    
    if cookies:
        # 显示部分 Cookie（隐藏敏感信息）
        show_cookies = cookies[:50] + "..." if len(cookies) > 50 else cookies
        click.echo(f"COOKIES_STR: {show_cookies}")
    else:
        click.echo("COOKIES_STR: 未配置")


@cli.command()
def login():
    """检查登录状态"""
    api = load_api()
    
    click.echo("检查登录状态...")
    
    if api.is_logged_in():
        user_id = api.get_user_id()
        click.echo(f"✓ 已登录，用户 ID: {user_id}")
    else:
        click.echo("✗ 登录已失效，请更新 Cookie")


@cli.command()
@click.argument("item_id")
def item(item_id: str):
    """获取商品详情"""
    api = load_api()
    
    click.echo(f"获取商品信息: {item_id}...")
    
    result = api.get_item_info(item_id)
    
    if 'error' in result:
        click.echo(f"✗ 获取失败: {result['error']}", err=True)
        sys.exit(1)
    
    if 'data' in result and 'itemDO' in result['data']:
        item_data = result['data']['itemDO']
        
        click.echo("\n📦 商品信息:")
        click.echo(f"  标题: {item_data.get('title', 'N/A')}")
        click.echo(f"  描述: {item_data.get('desc', 'N/A')}")
        click.echo(f"  价格: ¥{item_data.get('soldPrice', 0) / 100}")
        click.echo(f"  库存: {item_data.get('quantity', 0)}")
        
        # SKU 信息
        sku_list = item_data.get('skuList', [])
        if sku_list:
            click.echo("\n📋 SKU 规格:")
            for sku in sku_list[:5]:  # 最多显示 5 个
                specs = [p.get('valueText', '') for p in sku.get('propertyList', [])]
                spec_text = " / ".join(specs) if specs else "默认"
                price = sku.get('price', 0) / 100
                click.echo(f"  - {spec_text}: ¥{price}")
    else:
        click.echo(f"✗ 获取失败: {result}", err=True)


@cli.command()
@click.argument("chat_id")
@click.argument("to_user_id")
@click.argument("message")
def send(chat_id: str, to_user_id: str, message: str):
    """发送消息"""
    api = load_api()

    cookies_str = os.getenv("COOKIES_STR")
    device_id = cookies_str.split('unb=')[1].split(';')[0] if 'unb=' in cookies_str else api.get_user_id()

    token_result = api.get_token(device_id)
    if not token_result or 'data' not in token_result:
        click.echo("✗ 获取 Token 失败", err=True)
        sys.exit(1)

    token = token_result['data'].get('accessToken')
    ws_client = XianyuWebSocket(cookies_str, device_id)

    try:
        result = asyncio.run(ws_client.send_once(token, chat_id, to_user_id, message))
        if result:
            click.echo("✓ 消息已发送")
        else:
            click.echo("✗ 消息发送失败", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"✗ 发送失败: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def listen(verbose: bool):
    """监听实时消息"""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    api = load_api()
    
    if not api.is_logged_in():
        click.echo("✗ 登录已失效，请更新 Cookie", err=True)
        sys.exit(1)
    
    click.echo("开始监听消息... (按 Ctrl+C 退出)")
    
    # 获取 token
    cookies_str = os.getenv("COOKIES_STR")
    user_id = api.get_user_id()
    device_id = cookies_str.split('unb=')[1].split(';')[0] if 'unb=' in cookies_str else user_id
    
    token_result = api.get_token(device_id)
    if not token_result or 'data' not in token_result:
        click.echo("✗ 获取 Token 失败", err=True)
        sys.exit(1)
    
    token = token_result['data'].get('accessToken')
    
    # 创建 WebSocket 客户端
    ws_client = XianyuWebSocket(cookies_str, device_id)
    
    # 设置消息回调
    async def on_message(msg_info):
        click.echo("\n" + "-"*40)
        click.echo(f"📩 新消息!")
        click.echo(f"  👤 用户: {msg_info['user_name']}")
        click.echo(f"  🆔 ID: {msg_info['user_id']}")
        click.echo(f"  🔗 Chat ID: {msg_info['chat_id']}")
        click.echo(f"  📦 商品: {msg_info['item_id']}")
        click.echo(f"  💬 内容: {msg_info['message']}")
        click.echo("-"*40)
    
    ws_client.set_message_callback(on_message)
    
    # 开始监听
    try:
        asyncio.run(ws_client.listen(token=token, api=api))
    except KeyboardInterrupt:
        click.echo("\n监听已停止")


@cli.command()
@click.argument("item_id")
def publish(item_id: str):
    """发布商品 (占位符)"""
    click.echo("发布商品功能开发中...")
    click.echo("需要实现: mtop.taobao.idle.publish 接口")


if __name__ == "__main__":
    cli()