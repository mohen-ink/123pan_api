import os
import json
from datetime import datetime as dt
from datetime import timedelta

# 常量定义
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "token.txt"  # 保存 clientID 和 clientSecret 的文件

def format_file_size(size):
    """格式化文件大小为可读形式"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size/1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/(1024*1024):.2f} MB"
    else:
        return f"{size/(1024*1024*1024):.2f} GB"

def save_token(access_token, expired_at):
    """保存token到本地文件"""
    token_data = {
        "accessToken": access_token,
        "expiredAt": expired_at
    }
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)

def save_credentials(client_id, client_secret):
    """保存凭证到本地文件"""
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            f.write(f"{client_id}\n{client_secret}")
        return True
    except Exception:
        return False

def load_credentials():
    """从本地文件加载凭证"""
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    return lines[0].strip(), lines[1].strip()
    except Exception:
        pass
    return None, None

def check_token_validity(expired_at):
    """检查token是否有效"""
    if not expired_at:
        return False
        
    # 解析过期时间
    expired_time = dt.strptime(expired_at.split('+')[0], "%Y-%m-%dT%H:%M:%S")                   
    # 获取当前时间
    current_time = dt.now()

    # 如果token还有效，返回True（提前10分钟更新token）
    if current_time < expired_time - timedelta(minutes=10):
        return True
    return False

def get_remaining_time(expired_at):
    """获取token剩余有效时间"""
    if not expired_at:
        return "未知"
        
    # 解析过期时间
    expired_time = dt.strptime(expired_at.split('+')[0], "%Y-%m-%dT%H:%M:%S")                   
    # 获取当前时间
    current_time = dt.now()

    # 计算剩余时间
    remaining_time = expired_time - current_time
    remaining_hours = remaining_time.total_seconds() // 3600
    remaining_minutes = (remaining_time.total_seconds() % 3600) // 60
    remaining_seconds = remaining_time.total_seconds() % 60
    
    return f"{int(remaining_hours)}小时{int(remaining_minutes)}分钟{int(remaining_seconds)}秒"