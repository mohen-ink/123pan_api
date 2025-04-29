import os
import json
from PySide6.QtWidgets import QDialog, QLineEdit, QFormLayout, QHBoxLayout, QPushButton
from utils import TOKEN_FILE, CREDENTIALS_FILE, load_credentials, save_token, check_token_validity, get_remaining_time

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录123云盘")
        self.setMinimumWidth(300)
        
        layout = QFormLayout(self)
        
        self.client_id_input = QLineEdit()
        self.client_secret_input = QLineEdit()
        
        layout.addRow("Client ID:", self.client_id_input)
        layout.addRow("Client Secret:", self.client_secret_input)
        
        # 尝试从token.txt读取
        client_id, client_secret = load_credentials()
        if client_id and client_secret:
            self.client_id_input.setText(client_id)
            self.client_secret_input.setText(client_secret)
        
        button_layout = QHBoxLayout()
        login_button = QPushButton("登录")
        cancel_button = QPushButton("取消")
        
        login_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(login_button)
        button_layout.addWidget(cancel_button)
        
        layout.addRow("", button_layout)
    
    def get_credentials(self):
        return self.client_id_input.text(), self.client_secret_input.text()

class AuthManager:
    """认证管理类"""
    
    def __init__(self, api):
        self.api = api
        self.token = None
        self.expired_at = None
    
    def load_token(self):
        """从本地加载token"""
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    access_token = token_data.get("accessToken")
                    expired_at = token_data.get("expiredAt")
                    
                    # 检查token是否有效
                    if access_token and check_token_validity(expired_at):
                        self.token = access_token
                        self.expired_at = expired_at
                        self.api.set_token(access_token)
                        return True, get_remaining_time(expired_at)
            except Exception as e:
                return False, f"读取本地token出错: {e}"
        
        return False, "无有效token"
    
    def login_with_credentials(self, client_id, client_secret):
        """使用凭证登录"""
        try:
            access_token, expired_at = self.api.get_access_token(client_id, client_secret)
            
            # 保存token
            save_token(access_token, expired_at)
            
            # 更新当前token
            self.token = access_token
            self.expired_at = expired_at
            self.api.set_token(access_token)
            
            return True, f"登录成功，token有效期: {get_remaining_time(expired_at)}"
        except Exception as e:
            return False, f"登录失败: {e}"
    
    def logout(self):
        """退出登录"""
        self.token = None
        self.expired_at = None
        self.api.set_token(None)
        
        # 清除保存的凭证
        if os.path.exists(CREDENTIALS_FILE):
            try:
                os.remove(CREDENTIALS_FILE)
            except Exception:
                pass
        
        # 清除token文件
        if os.path.exists(TOKEN_FILE):
            try:
                os.remove(TOKEN_FILE)
            except Exception:
                pass
        
        return True