# Django Chat 项目文档

本文档提供了 Django Chat 项目的技术细节、功能列表和文件结构。

## 功能详细介绍

### 用户认证系统
- 用户注册：新用户可以创建账号
- 用户登录：已有用户可以登录系统
- 用户验证：确保只有登录用户可以访问聊天功能

### 聊天室管理
- 创建聊天室：用户可以创建新的聊天室
- 聊天室列表：显示所有可用的聊天室
- 加入聊天室：用户可以进入任何聊天室

### 实时通信
- WebSocket 连接：使用 Django Channels 建立 WebSocket 连接
- 实时消息传递：消息实时发送到所有连接的用户
- 连接状态显示：显示 WebSocket 连接状态

### 历史消息功能
- 消息存储：将消息保存到数据库
- 历史记录加载：用户可以加载聊天记录
- 分页加载：支持分页加载历史消息

### 用户界面
- 响应式设计：适配桌面和移动设备
- 消息气泡：区分自己和他人的消息
- 系统消息：显示系统状态和提示

## 项目结构

```
django-chat/
│
├── chat/                       # 主应用目录
│   ├── migrations/             # 数据库迁移文件
│   ├── static/                 # 静态资源文件
│   │   └── chat/
│   │       ├── css/           # CSS 样式文件
│   │       │   └── style.css   # 主样式文件
│   │       └── js/            # JavaScript 文件
│   │           └── chat.js    # 聊天功能脚本
│   │
│   ├── templates/             # HTML 模板
│   │   └── chat/
│   │       ├── base.html      # 基础模板
│   │       ├── index.html     # 聊天室列表页
│   │       ├── login.html     # 登录页
│   │       ├── room.html      # 聊天室页面
│   │       ├── room_create.html # 创建聊天室页面
│   │       └── signup.html    # 注册页
│   │
│   ├── __init__.py
│   ├── admin.py               # Django 管理界面配置
│   ├── apps.py                # 应用配置
│   ├── consumers.py           # WebSocket 消费者
│   ├── forms.py               # 表单定义
│   ├── models.py              # 数据模型
│   ├── routing.py             # WebSocket 路由
│   ├── urls.py                # URL 路由配置
│   └── views.py               # 视图函数
│
├── screenshots/               # 项目截图目录
│
├── .gitignore                 # Git 忽略文件
├── LICENSE                    # MIT 许可证
├── README.md                  # 项目说明
├── CONTRIBUTING.md            # 贡献指南
├── DOCUMENTATION.md           # 项目文档
├── asgi.py                    # ASGI 配置
├── manage.py                  # Django 管理命令
├── requirements.txt           # 项目依赖
├── run.sh                     # 开发环境启动脚本
├── run_production.sh          # 生产环境启动脚本
├── settings.py                # 项目设置
├── settings_production_example.py # 生产环境设置示例
├── urls.py                    # 项目 URL 配置
└── wsgi.py                    # WSGI 配置
```

## 技术实现细节

### 数据模型

**Room 模型**：表示聊天室
```python
class Room(models.Model):
    name = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Message 模型**：表示聊天消息
```python
class Message(models.Model):
    room = models.ForeignKey(Room, related_name='messages', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
```

### WebSocket 使用

项目通过以下步骤实现实时通信：

1. 建立 WebSocket 连接：
   - 前端使用原生 WebSocket API
   - 后端使用 Django Channels 的 AsyncWebsocketConsumer

2. 消息处理流程：
   - 客户端发送消息到服务器
   - 服务器广播消息到聊天室的所有成员
   - 服务器将消息保存到数据库

3. 历史记录加载：
   - 客户端请求历史消息
   - 服务器查询数据库并返回分页结果
   - 客户端将消息整合到聊天界面

## API 端点

### HTTP 端点

- `/` - 聊天室列表页
- `/login/` - 用户登录
- `/signup/` - 用户注册
- `/logout/` - 用户退出
- `/create/` - 创建聊天室
- `/room/<room_name>/` - 特定聊天室

### WebSocket 端点

- `/ws/chat/<room_name>/` - 聊天室 WebSocket 连接

## 部署注意事项

1. 确保使用 ASGI 服务器（Daphne 或 Uvicorn）
2. 对于生产环境，建议使用 Redis 作为 Channel Layer
3. 对于大规模部署，考虑使用负载均衡和多个 ASGI 工作进程 