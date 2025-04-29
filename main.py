import sys
from PySide6.QtWidgets import QApplication
from api import API_123pan
from auth import AuthManager
from ui import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 创建API实例
    api = API_123pan()
    
    # 创建认证管理器
    auth_manager = AuthManager(api)
    
    # 创建并显示主窗口
    window = MainWindow(api, auth_manager)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()