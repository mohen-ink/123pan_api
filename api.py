import http.client
import json
from utils import format_file_size

class API_123pan:
    BASE_URL = "open-api.123pan.com"
    
    def __init__(self, token=None):
        self.token = token
    
    def set_token(self, token):
        """设置访问令牌"""
        self.token = token
    
    def get_headers(self):
        """获取请求头"""
        headers = {
            'Content-Type': 'application/json',
            'Platform': 'open_platform'
        }
        if self.token:
            headers['Authorization'] = self.token
        return headers
    
    def get_user_info(self):
        """获取用户信息"""
        if not self.token:
            raise Exception("未登录")
            
        conn = http.client.HTTPSConnection(self.BASE_URL)
        headers = self.get_headers()
        
        conn.request("GET", "/api/v1/user/info", "", headers)
        res = conn.getresponse()
        data = res.read()
        data_dict = json.loads(data)
        
        if data_dict.get("code") != 0:
            raise Exception(data_dict.get("message", "未知错误"))
        
        spaceUsed = (data_dict["data"]["spaceUsed"])/1073741824
        spacePermanent = (data_dict["data"]["spacePermanent"])/1099511627776
        directTraffic = (data_dict["data"]["directTraffic"])/1073741824
        return spaceUsed, spacePermanent, directTraffic
    
    def get_file_list(self, folder_id, last_file_id=None):
        """获取指定文件夹的文件列表"""
        if not self.token:
            raise Exception("未登录")
            
        conn = http.client.HTTPSConnection(self.BASE_URL)
        headers = self.get_headers()
        
        url = f"/api/v2/file/list?parentFileId={folder_id}&limit=100"
        if last_file_id:
            url += f"&lastFileId={last_file_id}"
            
        conn.request("GET", url, "", headers)
        res = conn.getresponse()
        data = res.read()
        data_dict = json.loads(data)
        
        if data_dict.get("code") != 0:
            raise Exception(data_dict.get("message", "未知错误"))
        
        file_list = data_dict.get("data", {}).get("fileList", [])
        last_file_id = data_dict.get("data", {}).get("lastFileId")
        
        # 处理文件列表数据
        processed_files = []
        for file in file_list:
            # 跳过已删除的文件
            if file.get("trashed") == 1:
                continue
                
            file_type = "文件夹" if file.get("type") == 1 else "文件"
            category_map = {0: "未知", 1: "音频", 2: "视频", 3: "图片"}
            category = category_map.get(file.get("category", 0), "未知")
            file_status = "正常" if file.get("status") <= 100 else "驳回"
            
            # 计算文件大小的可读形式
            size = file.get("size", 0)
            size_str = format_file_size(size)
            
            processed_file = {
                "fileId": file.get("fileId"),
                "filename": file.get("filename"),
                "type": file_type,
                "size": size_str,
                "raw_size": size,
                "etag": file.get("etag"),
                "status": file_status,
                "parentFileId": file.get("parentFileId"),
                "category": category,
                "trashed": "否"  # 已经过滤掉了trashed=1的文件
            }
            processed_files.append(processed_file)
        
        return processed_files, last_file_id
    
    def get_download_url(self, file_id):
        """获取文件下载链接"""
        if not self.token:
            raise Exception("未登录")
            
        conn = http.client.HTTPSConnection(self.BASE_URL)
        headers = self.get_headers()
        
        try:
            conn.request("GET", f"/api/v1/file/download_info?fileId={file_id}", "", headers)
            res = conn.getresponse()
            data = res.read()
            data_dict = json.loads(data)
            
            if data_dict.get("code") != 0:
                raise Exception(data_dict.get("message", "未知错误"))
            
            return data_dict.get("data", {}).get("downloadUrl")
        except Exception as e:
            raise Exception(f"获取下载链接失败: {e}")
    
    def get_access_token(self, client_id, client_secret):
        """获取访问令牌"""
        conn = http.client.HTTPSConnection(self.BASE_URL)
        payload = json.dumps({
            "clientID": client_id,
            "clientSecret": client_secret
        })
        headers = {
            'Platform': 'open_platform',
            'Content-Type': 'application/json'
        }
        
        conn.request("POST", "/api/v1/access_token", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data_dict = json.loads(data)
        
        # 检查API返回是否成功
        if data_dict.get("code") != 0:
            error_msg = data_dict.get('message', '未知错误')
            raise Exception(f"获取token失败: {error_msg}")
                
        access_token = data_dict["data"]["accessToken"]
        expired_at = data_dict["data"]["expiredAt"]
        
        return access_token, expired_at