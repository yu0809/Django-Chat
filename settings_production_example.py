"""
Django Chat 生产环境配置示例

使用方法:
1. 复制此文件为 settings_production.py
2. 修改相关配置
3. 使用 --settings=settings_production 参数运行Django命令
"""

from settings import *  # 导入基础配置

# 基本设置
DEBUG = False
SECRET_KEY = "your-secure-secret-key"  # 请更改为安全的密钥
ALLOWED_HOSTS = ["your-domain.com", "www.your-domain.com"]  # 允许的主机名

# 数据库配置 (PostgreSQL示例)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django_chat",
        "USER": "db_user",
        "PASSWORD": "db_password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# 静态文件设置
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# 安全设置
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000  # 1年
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Channel Layer配置 (使用Redis)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis-host", 6379)],
        },
    }
}

# 日志配置
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "django_chat.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": True,
        },
        "chat": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
} 