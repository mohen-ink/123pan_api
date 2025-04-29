from PySide6.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QStyle,
                              QWidget, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
                              QHBoxLayout, QHeaderView, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt
from auth import LoginDialog
from threads import DownloadThread, UploadThread
from utils import save_credentials, format_file_size

class MainWindow(QMainWindow):
    def __init__(self, api, auth_manager):
        super().__init__()
        
        # 初始化API和认证管理器
        self.api = api
        self.auth_manager = auth_manager
        
        # 初始化状态变量
        self.is_logged_in = False
        self.current_folder_id = "0"  # 默认根目录
        self.current_path = "/"
        self.last_file_id = None  # 用于分页
        self.folder_history = []  # 文件夹导航历史
        
        self.setup_ui()
        self.auto_login()
    
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("123云盘客户端")
        self.setGeometry(100, 100, 1000, 600)
        
        # 设置应用样式表
        self.apply_style()
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 添加标题
        title_label = QLabel("123云盘文件管理")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px; color: #0078d7;")
        main_layout.addWidget(title_label)
        
        # 添加用户信息区域
        self.user_info_label = QLabel("未登录")
        self.user_info_label.setStyleSheet("padding: 8px; background-color: #ffffff; border-radius: 6px;")
        main_layout.addWidget(self.user_info_label)
        
        # 添加导航区域
        main_layout.addLayout(self.create_navigation_layout())
        
        # 添加按钮区域
        main_layout.addLayout(self.create_button_layout())
        
        # 添加文件表格
        self.file_table = self.create_file_table()
        main_layout.addWidget(self.file_table)
        
        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("padding: 8px; background-color: #ffffff; border-radius: 6px;")
        main_layout.addWidget(self.status_label)
        
        # 添加分页按钮
        main_layout.addLayout(self.create_pagination_layout())
        
        # 更新路径导航
        self.update_path_navigation()
    
    def apply_style(self):

        self.setStyleSheet("""
            QMainWindow, QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #202020;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px 12px;
                color: #202020;
            }
            QPushButton:hover {
                background-color: #e5e5e5;
                border: 1px solid #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e5f3ff;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #e0e0e0;
                color: #505050;
            }
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 6px;
                background-color: #ffffff;
            }
        """)
    
    def create_navigation_layout(self):
        """创建导航区域布局"""
        nav_layout = QHBoxLayout()
        
        # 返回上级按钮
        back_button = QPushButton("返回上级")
        back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        back_button.clicked.connect(self.go_to_parent_folder)
        nav_layout.addWidget(back_button)
        
        # 路径导航区域
        self.path_nav_layout = QHBoxLayout()
        self.path_nav_layout.setSpacing(0)
        self.path_nav_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建一个容器来放置路径导航
        path_nav_container = QWidget()
        path_nav_container.setLayout(self.path_nav_layout)
        path_nav_container.setStyleSheet("background-color: #ffffff; border-radius: 6px; padding: 5px;")
        
        nav_layout.addWidget(path_nav_container)
        nav_layout.setStretch(1, 1)  # 让路径导航区域占据更多空间
        
        return nav_layout
    
    def create_button_layout(self):
        """创建按钮区域布局"""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 登录按钮
        self.login_button = QPushButton("登录账号")
        self.login_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.login_button.clicked.connect(self.login)
        button_layout.addWidget(self.login_button)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新列表")
        refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_button.clicked.connect(lambda: self.list_files())
        button_layout.addWidget(refresh_button)
        
        # 上传按钮
        upload_button = QPushButton("上传文件")
        upload_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        upload_button.clicked.connect(self.upload_file)
        button_layout.addWidget(upload_button)
        
        # 下载按钮
        download_button = QPushButton("下载文件")
        download_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowDown))
        download_button.clicked.connect(self.download_file)
        button_layout.addWidget(download_button)
        
        return button_layout
    
    def create_file_table(self):
        """创建文件表格"""
        file_table = QTableWidget(0, 7)
        file_table.setHorizontalHeaderLabels(["文件ID", "文件名", "类型", "大小", "分类", "状态", "MD5"])
        file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        file_table.setSelectionBehavior(QTableWidget.SelectRows)
        file_table.setEditTriggers(QTableWidget.NoEditTriggers)
        file_table.cellDoubleClicked.connect(self.on_file_double_clicked)
        file_table.setAlternatingRowColors(True)
        file_table.verticalHeader().setVisible(False)
        return file_table
    
    def create_pagination_layout(self):
        """创建分页按钮布局"""
        pagination_layout = QHBoxLayout()
        self.next_page_button = QPushButton("下一页")
        self.next_page_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.next_page_button.clicked.connect(lambda: self.list_files(use_last_id=True))
        self.next_page_button.setVisible(False)  # 默认隐藏
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.next_page_button)
        return pagination_layout
    
    # ===== 认证和用户信息相关方法 =====
    
    def auto_login(self):
        """尝试使用保存的token自动登录"""
        success, message = self.auth_manager.load_token()
        if success:
            self.is_logged_in = True
            self.update_login_button()
            self.update_user_info()
            self.list_files()
            self.status_label.setText(f"自动登录成功，token有效期剩余{message}")
    
    def login(self):
        """登录或退出登录"""
        if self.is_logged_in:
            # 如果已登录，则退出登录
            self.logout()
        else:
            # 如果未登录，则显示登录对话框
            dialog = LoginDialog(self)
            if dialog.exec():
                client_id, client_secret = dialog.get_credentials()
                
                if client_id and client_secret:
                    # 保存凭证
                    save_credentials(client_id, client_secret)
                    
                    # 登录
                    self.status_label.setText("正在登录...")
                    success, message = self.auth_manager.login_with_credentials(client_id, client_secret)
                    
                    if success:
                        self.is_logged_in = True
                        self.update_login_button()
                        self.update_user_info()
                        self.list_files()
                        self.status_label.setText(message)
                    else:
                        self.status_label.setText(message)
                        QMessageBox.warning(self, "登录失败", message)
                else:
                    QMessageBox.warning(self, "登录失败", "Client ID 和 Client Secret 不能为空")
    
    def logout(self):
        """退出登录"""
        # 清除token
        self.auth_manager.logout()
        self.is_logged_in = False
        
        # 更新UI
        self.update_login_button()
        self.user_info_label.setText("未登录")
        self.file_table.setRowCount(0)
        self.status_label.setText("已退出登录")
        
        # 重置文件夹状态
        self.current_folder_id = "0"
        self.current_path = "/"
        self.folder_history = []
        self.update_path_navigation()
    
    def update_login_button(self):
        """根据登录状态更新登录按钮文本"""
        self.login_button.setText("退出登录" if self.is_logged_in else "登录账号")
    
    def update_user_info(self):
        """更新用户信息显示"""
        if not self.is_logged_in:
            self.user_info_label.setText("未登录")
            return
        
        self.status_label.setText("正在获取用户信息...")
        try:
            spaceUsed, spacePermanent, directTraffic = self.api.get_user_info()
            self.user_info_label.setText(
                f'已用空间：{spaceUsed:.2f} GB | 总空间：{spacePermanent:.2f} TB | 剩余直链流量：{directTraffic:.2f} GB'
            )
            self.status_label.setText("获取用户信息成功")
        except Exception as e:
            self.status_label.setText(f"获取用户信息失败: {e}")
    
    # ===== 文件操作相关方法 =====
    
    def list_files(self, use_last_id=False):
        """获取并显示文件列表"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "错误", "请先登录")
            return

        # 每次刷新时更新用户信息
        self.update_user_info()
        # 确定使用哪个last_file_id
        last_id = None
        if use_last_id and self.last_file_id:
            last_id = self.last_file_id
        
        self.status_label.setText(f"正在获取文件列表，文件夹ID: {self.current_folder_id}...")
        try:
            files, last_file_id = self.api.get_file_list(self.current_folder_id, last_id)
            
            if files:
                # 如果是加载下一页，则追加到现有列表
                if use_last_id:
                    self.append_files(files)
                else:
                    self.display_files(files)
                
                # 保存最后一个文件ID用于下一页
                self.last_file_id = last_file_id
                
                # 根据是否有更多文件显示或隐藏"下一页"按钮
                if last_file_id and last_file_id != -1:
                    self.next_page_button.setVisible(True)
                    self.status_label.setText(f"显示部分文件，还有更多文件")
                else:
                    self.next_page_button.setVisible(False)
                    self.status_label.setText("已显示全部文件")
            else:
                self.status_label.setText("文件夹为空或获取失败")
                self.next_page_button.setVisible(False)
        except Exception as e:
            self.status_label.setText(f"获取文件列表失败: {e}")
            self.next_page_button.setVisible(False)
    
    def display_files(self, files):
        """在表格中显示文件列表"""
        self.file_table.setRowCount(0)  # 清空表格
        self.append_files(files)
    
    def append_files(self, files):
        """将文件追加到表格末尾"""
        current_row_count = self.file_table.rowCount()
        
        for row, file in enumerate(files):
            row_index = current_row_count + row
            self.file_table.insertRow(row_index)
            self.file_table.setItem(row_index, 0, QTableWidgetItem(str(file["fileId"])))
            self.file_table.setItem(row_index, 1, QTableWidgetItem(file["filename"]))
            self.file_table.setItem(row_index, 2, QTableWidgetItem(file["type"]))
            self.file_table.setItem(row_index, 3, QTableWidgetItem(file["size"]))
            self.file_table.setItem(row_index, 4, QTableWidgetItem(file["category"]))
            self.file_table.setItem(row_index, 5, QTableWidgetItem(file["status"]))
            self.file_table.setItem(row_index, 6, QTableWidgetItem(file["etag"] or ""))
    
    def on_file_double_clicked(self, row, column):
        """处理文件表格的双击事件"""
        if not self.is_logged_in:
            return
            
        file_id = self.file_table.item(row, 0).text()
        file_type = self.file_table.item(row, 2).text()
        file_name = self.file_table.item(row, 1).text()
        
        if file_type == "文件夹":
            # 如果是文件夹，则进入该文件夹
            self.enter_folder(file_id, file_name)
        else:
            # 如果是文件，可以实现预览或下载功能
            self.status_label.setText(f"选择了文件: {file_name}")
    
    # ===== 文件夹导航相关方法 =====
    
    def enter_folder(self, folder_id, folder_name):
        """进入指定文件夹"""
        # 保存当前文件夹信息到导航历史
        self.folder_history.append((self.current_folder_id, self.current_path))
        
        # 更新当前文件夹信息
        self.current_folder_id = folder_id
        self.current_path = f"{self.current_path}{folder_name}/" if self.current_path.endswith('/') else f"{self.current_path}/{folder_name}/"
        
        # 更新路径导航
        self.update_path_navigation()
        
        # 重置分页状态
        self.last_file_id = None
        
        # 获取并显示新文件夹的内容
        self.list_files()
    
    def go_to_parent_folder(self):
        """返回上级文件夹"""
        if not self.folder_history:
            self.status_label.setText("已经在根目录")
            return
            
        # 从历史记录中获取上级文件夹信息
        parent_folder_id, parent_path = self.folder_history.pop()
        
        # 更新当前文件夹信息
        self.current_folder_id = parent_folder_id
        self.current_path = parent_path
        
        # 更新路径导航
        self.update_path_navigation()
        
        # 重置分页状态
        self.last_file_id = None
        
        # 获取并显示上级文件夹的内容
        self.list_files()
    
    def update_path_navigation(self):
        """更新路径导航区域"""
        # 清除现有的路径导航按钮
        while self.path_nav_layout.count():
            item = self.path_nav_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 解析当前路径
        path_parts = self.current_path.strip('/').split('/')
        
        # 构建路径和文件夹ID的映射
        path_id_map = {"/": "0"}  # 根目录
        
        # 从历史记录构建路径映射
        # 创建完整的路径到ID的映射
        current_full_path = "/"
        for i, (folder_id, folder_path) in enumerate(self.folder_history):
            path_id_map[folder_path] = folder_id
            
            # 如果是当前路径的一部分，则添加到映射中
            if self.current_path.startswith(folder_path) and folder_path != self.current_path:
                # 提取该路径后的下一级文件夹
                next_part = self.current_path[len(folder_path):].split('/')[0]
                if next_part:
                    next_path = folder_path + next_part + "/"
                    # 查找下一级文件夹的ID
                    for j in range(i+1, len(self.folder_history)):
                        if self.folder_history[j][1] == next_path:
                            path_id_map[next_path] = self.folder_history[j][0]
                            break
        
        # 当前文件夹
        path_id_map[self.current_path] = self.current_folder_id
        
        # 添加根目录按钮
        root_button = QPushButton("/")
        root_button.setStyleSheet("border: none; text-align: left; padding: 5px; border-radius: 4px;")
        root_button.setCursor(Qt.PointingHandCursor)
        root_button.clicked.connect(lambda: self.jump_to_folder("0", "/"))
        self.path_nav_layout.addWidget(root_button)
        
        # 构建路径导航
        current_path = "/"
        for i, part in enumerate(path_parts):
            if not part:  # 跳过空部分
                continue
                
            # 添加分隔符
            separator = QLabel(">")
            separator.setStyleSheet("margin: 0 5px;")
            self.path_nav_layout.addWidget(separator)
            
            # 更新当前路径
            if current_path.endswith('/'):
                current_path += part
            else:
                current_path += '/' + part
                
            # 确保路径以/结尾
            if not current_path.endswith('/'):
                current_path += '/'
            
            # 创建按钮
            folder_button = QPushButton(part)
            folder_button.setStyleSheet("border: none; text-align: left; padding: 5px; border-radius: 4px;")
            folder_button.setCursor(Qt.PointingHandCursor)
            
            # 获取该路径对应的文件夹ID
            folder_id = path_id_map.get(current_path)
            
            # 如果找不到ID，则使用当前文件夹ID（这是一个后备方案）
            if folder_id is None:
                # 调试信息
                print(f"警告: 找不到路径 '{current_path}' 的文件夹ID，使用当前文件夹ID")
                folder_id = self.current_folder_id if current_path == self.current_path else None
                
                # 如果仍然找不到ID，跳过这个按钮
                if folder_id is None:
                    continue
            
            # 使用lambda函数的默认参数来避免闭包问题
            folder_button.clicked.connect(lambda checked=False, fid=folder_id, path=current_path: self.jump_to_folder(fid, path))
            
            self.path_nav_layout.addWidget(folder_button)
        
        # 添加弹性空间
        self.path_nav_layout.addStretch()
    
    def jump_to_folder(self, folder_id, folder_path):
        """跳转到指定文件夹"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "错误", "请先登录")
            return
        
        # 如果是当前文件夹，不做任何操作
        if folder_id == self.current_folder_id:
            return
        
        # 更新当前文件夹信息
        self.current_folder_id = folder_id
        self.current_path = folder_path
        
        # 重置文件夹历史
        if folder_id == "0":  # 如果是根目录，清空历史
            self.folder_history = []
        else:
            # 重建文件夹历史 - 只保留当前路径的父路径
            new_history = []
            if hasattr(self, 'folder_history'):
                for old_id, old_path in self.folder_history:
                    if folder_path.startswith(old_path) and old_path != folder_path:
                        new_history.append((old_id, old_path))
            
            self.folder_history = new_history
        
        # 重置分页状态
        self.last_file_id = None
        
        # 更新路径导航
        self.update_path_navigation()
        
        # 获取并显示文件夹内容
        self.list_files()
    
    def upload_file(self):
        """上传文件"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "错误", "请先登录")
            return
            
        # 选择要上传的文件
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要上传的文件")
        if not file_path:
            return
        
        file_name = os.path.basename(file_path)
        self.status_label.setText(f"准备上传文件: {file_name}")
        
        # 创建进度条
        self.upload_progress_bar = QProgressBar()
        self.upload_progress_bar.setRange(0, 100)
        self.upload_progress_bar.setValue(0)
        self.upload_progress_bar.setTextVisible(True)
        self.upload_progress_bar.setFormat("%p% - " + file_name)
        
        # 添加进度条到主布局
        central_widget = self.centralWidget()
        main_layout = central_widget.layout()
        main_layout.insertWidget(main_layout.count()-1, self.upload_progress_bar)  # 在状态标签之前插入
        
        # 创建并启动上传线程
        self.upload_thread = UploadThread(file_path, self.auth_manager.token, self.current_folder_id)
        self.upload_thread.progress_signal.connect(self.update_upload_progress)
        self.upload_thread.finished_signal.connect(self.upload_finished)
        self.upload_thread.start()
    
    def update_upload_progress(self, current, total, status_text):
        """更新上传进度"""
        if total > 0:
            progress = int((current / total) * 100)
            self.upload_progress_bar.setValue(progress)
            self.status_label.setText(status_text)
    
    def upload_finished(self, success, result, file_name):
        """上传完成处理"""
        # 移除进度条
        if hasattr(self, 'upload_progress_bar'):
            central_widget = self.centralWidget()
            main_layout = central_widget.layout()
            main_layout.removeWidget(self.upload_progress_bar)
            self.upload_progress_bar.deleteLater()
            self.upload_progress_bar = None
        
        if success:
            self.status_label.setText(f"文件 {file_name} 上传成功，文件ID: {result}")
            # 刷新文件列表
            self.list_files()
        else:
            self.status_label.setText(f"文件上传失败: {result}")
    
    def download_file(self):
        """下载文件"""
        if not self.is_logged_in:
            QMessageBox.warning(self, "错误", "请先登录")
            return
            
        selected_rows = self.file_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "错误", "请先选择要下载的文件")
            return
        
        # 获取选中的行
        row = selected_rows[0].row()
        file_id = self.file_table.item(row, 0).text()
        file_name = self.file_table.item(row, 1).text()
        file_type = self.file_table.item(row, 2).text()
        
        if file_type == "文件夹":
            QMessageBox.warning(self, "错误", "不能直接下载文件夹")
            return
        
        # 选择保存位置
        save_path, _ = QFileDialog.getSaveFileName(self, "保存文件", file_name)
        if not save_path:
            return
        
        self.status_label.setText(f"准备下载文件: {file_name}")
        
        try:
            # 1. 获取下载链接
            download_url = self.api.get_download_url(file_id)
            if not download_url:
                self.status_label.setText("获取下载链接失败")
                return
            
            # 2. 创建进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(True)
            self.progress_bar.setFormat("%p% - " + file_name)
            
            # 添加进度条到主布局
            central_widget = self.centralWidget()
            main_layout = central_widget.layout()
            main_layout.insertWidget(main_layout.count()-1, self.progress_bar)  # 在状态标签之前插入
            
            # 3. 创建并启动下载线程
            self.download_thread = DownloadThread(download_url, save_path)
            self.download_thread.progress_signal.connect(self.update_download_progress)
            self.download_thread.finished_signal.connect(lambda success, error: self.download_finished(success, error, file_name, save_path))
            self.download_thread.start()
            
            self.status_label.setText(f"正在下载: {file_name}")
        
        except Exception as e:
            self.status_label.setText(f"下载过程中发生错误: {e}")

    def update_download_progress(self, downloaded, total):
        """更新下载进度"""
        if total > 0:
            progress = int((downloaded / total) * 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(f"下载进度: {progress}% ({format_file_size(downloaded)}/{format_file_size(total)})")

    def download_finished(self, success, error, file_name, save_path):
        """下载完成处理"""
        # 移除进度条
        if hasattr(self, 'progress_bar'):
            central_widget = self.centralWidget()
            main_layout = central_widget.layout()
            main_layout.removeWidget(self.progress_bar)
            self.progress_bar.deleteLater()
            self.progress_bar = None
        
        if success:
            self.status_label.setText(f"文件 {file_name} 下载成功，保存至: {save_path}")
        else:
            self.status_label.setText(f"文件下载失败: {error}")