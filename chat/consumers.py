import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room, Message

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """处理WebSocket连接"""
        try:
            self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
            self.group_name = f"chat_{self.room_name}"
            self.user = self.scope["user"]
            
            # 打印调试信息
            print(f"WebSocket连接: 用户尝试连接到房间 {self.room_name}")
            logger.info(f"连接参数: url_route={self.scope.get('url_route')}, path={self.scope.get('path')}")
            
            # 添加到组
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            
            print(f"用户已连接到房间: {self.room_name}")
            
            # 发送欢迎消息
            await self.send(text_data=json.dumps({
                "message": f"欢迎来到聊天室 #{self.room_name}!",
                "username": "系统",
            }))
        except Exception as e:
            logger.error(f"连接时出错: {e}")
            print(f"连接错误: {e}")

    async def disconnect(self, code):
        """处理WebSocket断开连接"""
        print(f"WebSocket断开: code={code}")
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception as e:
            logger.error(f"断开连接时出错: {e}")

    async def receive(self, text_data):
        """接收WebSocket消息"""
        print(f"收到消息: {text_data}")
        try:
            data = json.loads(text_data)
            
            # 检查是否是加载历史记录的请求
            if 'load_history' in data:
                # 加载并发送历史消息
                page = data.get('page', 1)
                await self.send_message_history(page)
                return
                
            # 正常的消息处理
            message = data["message"]
            username = self.user.username if self.user.is_authenticated else "匿名用户"
            
            # 保存消息到数据库
            if self.user.is_authenticated:
                await self.save_message(message)
            
            print(f"将消息广播到群组 {self.group_name}: {message}")
            
            # 发送消息到组
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "username": username,
                },
            )
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            print(f"处理消息出错: {e}")
            await self.send(text_data=json.dumps({
                "error": f"处理消息失败: {str(e)}",
                "username": "系统",
            }))

    async def chat_message(self, event):
        """将消息发送到WebSocket"""
        print(f"发送消息到客户端: {event}")
        try:
            await self.send(text_data=json.dumps({
                "message": event["message"],
                "username": event["username"],
            }))
        except Exception as e:
            logger.error(f"发送消息到客户端时出错: {e}")
            print(f"发送消息出错: {e}")
    
    @database_sync_to_async
    def save_message(self, content):
        """将消息保存到数据库"""
        try:
            # 获取或创建房间
            room, _ = Room.objects.get_or_create(name=self.room_name, defaults={'owner': self.user})
            
            # 创建消息
            Message.objects.create(
                room=room,
                user=self.user,
                content=content
            )
        except Exception as e:
            logger.error(f"保存消息时出错: {e}")
    
    @database_sync_to_async
    def get_message_history(self, page=1, per_page=20):
        """获取消息历史记录"""
        try:
            # 获取房间
            room = Room.objects.get(name=self.room_name)
            
            # 计算分页
            start = (page - 1) * per_page
            end = page * per_page
            
            # 获取消息记录
            messages = Message.objects.filter(room=room).order_by('-timestamp')[start:end]
            
            # 返回按时间正序排列的消息（从旧到新）
            return [msg.to_json() for msg in reversed(messages)], messages.count() < per_page
        except Room.DoesNotExist:
            return [], True
        except Exception as e:
            logger.error(f"获取消息历史记录时出错: {e}")
            return [], True
    
    async def send_message_history(self, page=1):
        """发送消息历史记录到客户端"""
        try:
            messages, is_end = await self.get_message_history(page)
            
            await self.send(text_data=json.dumps({
                "history": True,
                "messages": messages,
                "page": page,
                "is_end": is_end
            }))
        except Exception as e:
            logger.error(f"发送历史记录时出错: {e}")
            await self.send(text_data=json.dumps({
                "error": f"获取历史记录失败: {str(e)}",
                "username": "系统",
            })) 