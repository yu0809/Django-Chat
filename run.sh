#!/bin/bash
# Django Chat 开发环境启动脚本

# 如果虚拟环境目录存在，则激活它
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 确保先停止所有现有服务器
echo "停止正在运行的服务器进程..."
pkill -f "runserver|daphne" || true

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput

# 使用daphne启动ASGI服务器
echo "正在启动 Daphne ASGI 服务器..."
echo "访问 http://127.0.0.1:8000 打开应用"
daphne -b 127.0.0.1 -p 8000 -v 2 asgi:application 