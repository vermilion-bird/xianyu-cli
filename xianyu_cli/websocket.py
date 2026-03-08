"""
闲鱼 WebSocket 消息客户端
基于 XianyuAutoAgent 项目的 WebSocket 实现
"""
import base64
import json
import asyncio
import time
import os
import websockets
from loguru import logger

from .xianyu_utils import generate_mid, generate_uuid, generate_device_id, decrypt


class XianyuWebSocket:
    """闲鱼 WebSocket 消息客户端"""
    
    def __init__(self, cookies_str: str, device_id: str = None):
        self.base_url = 'wss://wss-goofish.dingtalk.com/'
        self.cookies_str = cookies_str
        self.device_id = device_id or generate_device_id(cookies_str.split('unb=')[1].split(';')[0] if 'unb=' in cookies_str else '')
        
        # 心跳配置
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "15"))
        self.heartbeat_timeout = int(os.getenv("HEARTBEAT_TIMEOUT", "5"))
        self.last_heartbeat_time = 0
        self.last_heartbeat_response = 0
        self.heartbeat_task = None
        self.ws = None
        self.current_token = None
        self.token_refresh_interval = int(os.getenv("TOKEN_REFRESH_INTERVAL", "3600"))
        self.last_token_refresh_time = 0
        
        # 消息回调
        self.message_callback = None
    
    def set_message_callback(self, callback):
        """设置消息回调函数"""
        self.message_callback = callback
    
    async def refresh_token(self, api):
        """刷新 Token"""
        try:
            logger.info("刷新 Token...")
            token_result = api.get_token(self.device_id)
            if token_result and 'data' in token_result and 'accessToken' in token_result['data']:
                new_token = token_result['data']['accessToken']
                self.current_token = new_token
                self.last_token_refresh_time = time.time()
                logger.info("Token 刷新成功")
                return new_token
            else:
                logger.error(f"Token 刷新失败: {token_result}")
                return None
        except Exception as e:
            logger.error(f"Token 刷新异常: {str(e)}")
            return None
    
    async def init(self, ws):
        """初始化连接"""
        if not self.current_token or (time.time() - self.last_token_refresh_time) >= self.token_refresh_interval:
            logger.info("获取初始 Token...")
            # 这里需要传入 api 对象，暂时跳过
        
        if not self.current_token:
            logger.error("无法获取有效 Token，初始化失败")
            raise Exception("Token 获取失败")
            
        msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",
                "token": self.current_token,
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5",
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid()
            }
        }
        await ws.send(json.dumps(msg))
        await asyncio.sleep(1)
        msg = {
            "lwp": "/r/SyncStatus/ackDiff", 
            "headers": {"mid": "5701741704675979 0"}, 
            "body": [{
                "pipeline": "sync", 
                "tooLong2Tag": "PNM,1", 
                "channel": "sync", 
                "topic": "sync", 
                "highPts": 0,
                "pts": int(time.time() * 1000) * 1000, 
                "seq": 0, 
                "timestamp": int(time.time() * 1000)
            }]
        }
        await ws.send(json.dumps(msg))
        logger.info('连接注册完成')
    
    def is_chat_message(self, message):
        """判断是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict) 
                and "1" in message 
                and isinstance(message["1"], dict)
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False
    
    def is_sync_package(self, message_data):
        """判断是否为同步包消息"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False
    
    async def handle_message(self, message_data, websocket):
        """处理消息"""
        # 发送 ACK
        try:
            message = message_data
            ack = {
                "code": 200,
                "headers": {
                    "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                    "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                }
            }
            if 'app-key' in message["headers"]:
                ack["headers"]["app-key"] = message["headers"]["app-key"]
            if 'ua' in message["headers"]:
                ack["headers"]["ua"] = message["headers"]["ua"]
            if 'dt' in message["headers"]:
                ack["headers"]["dt"] = message["headers"]["dt"]
            await websocket.send(json.dumps(ack))
        except Exception:
            pass
        
        if not self.is_sync_package(message_data):
            return
        
        # 获取并解密数据
        sync_data = message_data["body"]["syncPushPackage"]["data"][0]
        
        if "data" not in sync_data:
            return
        
        try:
            data = sync_data["data"]
            try:
                data = base64.b64decode(data).decode("utf-8")
                data = json.loads(data)
                return
            except Exception:
                decrypted_data = decrypt(data)
                message = json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"消息解密失败: {e}")
            return
        
        # 检查订单消息
        try:
            if message['3'].get('redReminder') == '等待买家付款':
                logger.info('等待买家付款')
                return
            elif message['3'].get('redReminder') == '交易关闭':
                logger.info('交易关闭')
                return
            elif message['3'].get('redReminder') == '等待卖家发货':
                logger.info('等待卖家发货')
                return
        except:
            pass
        
        # 处理聊天消息
        if not self.is_chat_message(message):
            return
        
        create_time = int(message["1"]["5"])
        send_user_name = message["1"]["10"]["reminderTitle"]
        send_user_id = message["1"]["10"]["senderUserId"]
        send_message = message["1"]["10"]["reminderContent"]
        
        # 时效性验证（过滤5分钟前消息）
        if (time.time() * 1000 - create_time) > 300000:
            return
        
        # 获取商品 ID 和会话 ID
        url_info = message["1"]["10"]["reminderUrl"]
        item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None
        chat_id = message["1"]["2"].split('@')[0]
        
        if not item_id:
            return
        
        msg_info = {
            "user_name": send_user_name,
            "user_id": send_user_id,
            "item_id": item_id,
            "chat_id": chat_id,
            "message": send_message,
            "time": create_time
        }
        
        logger.info(f"收到消息 - 用户: {send_user_name}, 商品: {item_id}, 消息: {send_message}")
        
        # 调用回调函数
        if self.message_callback:
            await self.message_callback(msg_info)
    
    async def send_heartbeat(self, ws):
        """发送心跳"""
        try:
            heartbeat_msg = {
                "lwp": "/!",
                "headers": {"mid": generate_mid()}
            }
            await ws.send(json.dumps(heartbeat_msg))
            self.last_heartbeat_time = time.time()
            logger.debug("心跳包已发送")
        except Exception as e:
            logger.error(f"发送心跳包失败: {e}")
    
    async def heartbeat_loop(self, ws):
        """心跳维护循环"""
        while True:
            try:
                current_time = time.time()
                
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)
                
                if (current_time - self.last_heartbeat_response) > (self.heartbeat_interval + self.heartbeat_timeout):
                    logger.warning("心跳响应超时，可能连接已断开")
                    break
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                break
    
    async def handle_heartbeat_response(self, message_data):
        """处理心跳响应"""
        try:
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到心跳响应")
                return True
        except Exception as e:
            logger.error(f"处理心跳响应出错: {e}")
        return False
    
    async def listen(self, token: str = None, api=None):
        """开始监听消息"""
        self.current_token = token
        
        while True:
            try:
                headers = {
                    "Cookie": self.cookies_str,
                    "Host": "wss-goofish.dingtalk.com",
                    "Connection": "Upgrade",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "Origin": "https://www.goofish.com",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }
                
                # 如果没有 token，尝试获取
                if not self.current_token and api:
                    token_result = await self.refresh_token(api)
                    if token_result:
                        self.current_token = token_result
                
                async with websockets.connect(self.base_url, additional_headers=headers) as websocket:
                    self.ws = websocket
                    await self.init(websocket)
                    
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_response = time.time()
                    
                    # 启动心跳任务
                    self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))
                    
                    async for message in websocket:
                        try:
                            message_data = json.loads(message)
                            
                            if await self.handle_heartbeat_response(message_data):
                                continue
                            
                            # 发送通用 ACK 响应
                            if "headers" in message_data and "mid" in message_data["headers"]:
                                ack = {
                                    "code": 200,
                                    "headers": {
                                        "mid": message_data["headers"]["mid"],
                                        "sid": message_data["headers"].get("sid", "")
                                    }
                                }
                                for key in ["app-key", "ua", "dt"]:
                                    if key in message_data["headers"]:
                                        ack["headers"][key] = message_data["headers"][key]
                                await websocket.send(json.dumps(ack))
                            
                            # 处理消息
                            await self.handle_message(message_data, websocket)
                                
                        except json.JSONDecodeError:
                            logger.error("消息解析失败")
                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {str(e)}")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket 连接已关闭，5秒后重连...")
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"连接发生错误: {e}")
                await asyncio.sleep(5)
            
            finally:
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
    
    async def send_once(self, token: str, chat_id: str, to_user_id: str, text: str) -> bool:
        """建立连接，发送单条消息后断开"""
        headers = {
            "Cookie": self.cookies_str,
            "Host": "wss-goofish.dingtalk.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Origin": "https://www.goofish.com",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self.current_token = token
        async with websockets.connect(self.base_url, additional_headers=headers) as websocket:
            self.ws = websocket
            await self.init(websocket)
            await asyncio.sleep(1)
            return await self.send_message(chat_id, to_user_id, text)

    async def send_message(self, chat_id: str, to_user_id: str, text: str):
        """发送消息"""
        if not self.ws:
            logger.error("WebSocket 未连接")
            return False
        
        try:
            text_msg = {
                "contentType": 1,
                "text": {"text": text}
            }
            text_base64 = str(base64.b64encode(json.dumps(text_msg).encode('utf-8')), 'utf-8')
            
            my_id = self.cookies_str.split('unb=')[1].split(';')[0] if 'unb=' in self.cookies_str else ''
            
            msg = {
                "lwp": "/r/MessageSend/sendByReceiverScope",
                "headers": {"mid": generate_mid()},
                "body": [
                    {
                        "uuid": generate_uuid(),
                        "cid": f"{chat_id}@goofish",
                        "conversationType": 1,
                        "content": {
                            "contentType": 101,
                            "custom": {
                                "type": 1,
                                "data": text_base64
                            }
                        },
                        "redPointPolicy": 0,
                        "extension": {"extJson": "{}"},
                        "ctx": {
                            "appVersion": "1.0",
                            "platform": "web"
                        },
                        "mtags": {},
                        "msgReadStatusSetting": 1
                    },
                    {
                        "actualReceivers": [
                            f"{to_user_id}@goofish",
                            f"{my_id}@goofish"
                        ]
                    }
                ]
            }
            
            await self.ws.send(json.dumps(msg))
            logger.info(f"消息发送成功: {text}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            return False