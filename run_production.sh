#!/bin/bash
# Django Chat 生产环境启动脚本

# 激活虚拟环境 (如果有)
# source /path/to/venv/bin/activate

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput --settings=settings_production

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate --settings=settings_production

# 启动 Daphne ASGI 服务器
echo "启动 Daphne ASGI 服务器..."
daphne -b 0.0.0.0 -p 8000 asgi:application

# 如果使用 Uvicorn
# echo "启动 Uvicorn ASGI 服务器..."
# uvicorn asgi:application --host 0.0.0.0 --port 8000

# 注意：生产环境应使用 supervisor、systemd 等工具管理进程
# 本脚本仅作为参考示例 