import os
import json
import http.client
import requests
import hashlib
import math
import time
from PySide6.QtCore import QThread, Signal

class DownloadThread(QThread):
    progress_signal = Signal(int, int)  # 下载进度信号 (已下载大小, 总大小)
    finished_signal = Signal(bool, str)  # 完成信号 (是否成功, 错误信息)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        
    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(self.save_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 发送进度信号
                        self.progress_signal.emit(downloaded, total_size)
                
                self.finished_signal.emit(True, "")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class UploadThread(QThread):
    progress_signal = Signal(int, int, str)  # 上传进度信号 (当前分片, 总分片数, 状态信息)
    finished_signal = Signal(bool, str, str)  # 完成信号 (是否成功, 文件ID或错误信息, 文件名)
    
    def __init__(self, file_path, access_token, parent_folder_id="0"):
        super().__init__()
        self.file_path = file_path
        self.access_token = access_token
        self.parent_folder_id = parent_folder_id
        
    def run(self):
        try:
            # 获取文件信息
            md5, size, name = self.get_file_info(self.file_path)
            if not md5:
                self.finished_signal.emit(False, f"无法读取文件: {self.file_path}", "")
                return
                
            self.progress_signal.emit(0, 100, f"正在创建上传任务: {name}")
            
            # 创建上传任务
            conn = http.client.HTTPSConnection("open-api.123pan.com")
            payload = json.dumps({
                "parentFileID": self.parent_folder_id,
                "filename": name,
                "etag": md5,
                "size": size
            })
            headers = {
                'Content-Type': 'application/json',
                'Platform': 'open_platform',
                'Authorization': self.access_token
            }
            
            try:
                conn.request("POST", "/upload/v1/file/create", payload, headers)
                res = conn.getresponse()
                data = res.read()
                response_data = json.loads(data.decode("utf-8"))
                
                # 检查响应是否有效
                if response_data is None or "data" not in response_data:
                    self.finished_signal.emit(False, f"API返回无效响应: {data.decode('utf-8')}", name)
                    return
                    
                # 检查是否秒传
                if response_data.get("data", {}).get("reuse", False):
                    file_id = response_data.get("data", {}).get("fileID")
                    self.progress_signal.emit(100, 100, "文件秒传成功")
                    self.finished_signal.emit(True, str(file_id), name)
                    return
                
                # 非秒传情况，提取preuploadID和sliceSize
                preupload_id = response_data.get("data", {}).get("preuploadID")
                slice_size = response_data.get("data", {}).get("sliceSize")
                
                if not preupload_id or not slice_size:
                    self.finished_signal.emit(False, "获取上传参数失败", name)
                    return
                
                # 计算分片数量
                total_slices = math.ceil(size / slice_size)
                self.progress_signal.emit(0, total_slices, f"准备分片上传，共{total_slices}个分片")
                
                # 上传所有分片
                all_slices_uploaded = True
                for slice_no in range(1, total_slices + 1):
                    self.progress_signal.emit(slice_no, total_slices, f"正在上传第 {slice_no}/{total_slices} 个分片...")
                    
                    # 获取上传URL
                    presigned_url = self.get_upload_url(self.access_token, preupload_id, slice_no)
                    if not presigned_url:
                        all_slices_uploaded = False
                        break
                    
                    # 计算分片的起始位置
                    start_pos = (slice_no - 1) * slice_size
                    
                    # 上传分片
                    if not self.upload_slice(presigned_url, self.file_path, start_pos, slice_size):
                        all_slices_uploaded = False
                        break
                    
                    self.progress_signal.emit(slice_no, total_slices, f"第 {slice_no}/{total_slices} 个分片上传成功")
                
                if all_slices_uploaded:
                    self.progress_signal.emit(total_slices, total_slices, "所有分片上传成功，正在完成上传...")
                    
                    # 通知服务器上传完成
                    complete_result = self.complete_upload(self.access_token, preupload_id)
                    
                    if complete_result:
                        if complete_result.get("async", False):
                            self.progress_signal.emit(total_slices, total_slices, "等待服务器处理...")
                            # 异步轮询获取上传结果
                            final_result = self.check_upload_result(self.access_token, preupload_id)
                            
                            if final_result and final_result.get("completed", False):
                                file_id = final_result.get("fileID")
                                self.finished_signal.emit(True, str(file_id), name)
                            else:
                                self.finished_signal.emit(False, "文件上传可能未完成，请稍后检查", name)
                        else:
                            # 无需异步查询，直接获取文件ID
                            completed = complete_result.get("completed", False)
                            file_id = complete_result.get("fileID")
                            
                            if completed:
                                self.finished_signal.emit(True, str(file_id), name)
                            else:
                                self.finished_signal.emit(False, "文件上传未完成，请稍后检查", name)
                    else:
                        self.finished_signal.emit(False, "完成上传请求失败", name)
                else:
                    self.finished_signal.emit(False, "分片上传失败", name)
            
            except Exception as e:
                self.finished_signal.emit(False, f"上传过程中发生错误: {str(e)}", name)
        
        except Exception as e:
            self.finished_signal.emit(False, f"上传线程发生错误: {str(e)}", "")
    
    def get_file_info(self, file_path):
        # 计算 MD5
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # 分块读取
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
        except FileNotFoundError:
            return None, None, None
        
        # 获取大小
        file_size = os.path.getsize(file_path)
        
        # 提取文件名
        file_name = os.path.basename(file_path)
        
        return (
            md5_hash.hexdigest(),
            file_size,
            file_name
        )
    
    def get_upload_url(self, access_token, preupload_id, slice_no):
        """获取分片上传地址"""
        conn = http.client.HTTPSConnection("open-api.123pan.com")
        payload = json.dumps({
            "preuploadID": preupload_id,
            "sliceNo": slice_no
        })
        headers = {
            'Content-Type': 'application/json',
            'Platform': 'open_platform',
            'Authorization': access_token
        }
        conn.request("POST", "/upload/v1/file/get_upload_url", payload, headers)
        res = conn.getresponse()
        data = res.read()
        response_data = json.loads(data.decode("utf-8"))
        
        if response_data.get("code") == 0:
            return response_data.get("data", {}).get("presignedURL")
        else:
            return None
    
    def upload_slice(self, presigned_url, file_path, start_pos, slice_size):
        """上传文件分片"""
        # 从URL中提取主机名和路径
        url_parts = presigned_url.replace("https://", "").split("/", 1)
        host = url_parts[0]
        path = "/" + url_parts[1] if len(url_parts) > 1 else "/"
        
        conn = http.client.HTTPSConnection(host)
        
        # 读取指定位置的文件分片
        with open(file_path, "rb") as f:
            f.seek(start_pos)
            slice_data = f.read(slice_size)
        
        headers = {
            'Content-Type': 'application/octet-stream'
        }
        
        conn.request("PUT", path, slice_data, headers)
        res = conn.getresponse()
        
        # 检查上传状态
        if res.status == 200:
            return True
        else:
            data = res.read()
            return False
    
    def complete_upload(self, access_token, preupload_id):
        """通知服务器上传完成"""
        conn = http.client.HTTPSConnection("open-api.123pan.com")
        payload = json.dumps({
            "preuploadID": preupload_id
        })
        headers = {
            'Content-Type': 'application/json',
            'Platform': 'open_platform',
            'Authorization': access_token
        }
        conn.request("POST", "/upload/v1/file/upload_complete", payload, headers)
        res = conn.getresponse()
        data = res.read()
        response_data = json.loads(data.decode("utf-8"))
        
        if response_data.get("code") == 0:
            return response_data.get("data", {})
        else:
            return None
    
    def check_upload_result(self, access_token, preupload_id, max_retries=30, retry_interval=1):
        """异步轮询获取上传结果"""
        conn = http.client.HTTPSConnection("open-api.123pan.com")
        payload = json.dumps({
            "preuploadID": preupload_id
        })
        headers = {
            'Content-Type': 'application/json',
            'Platform': 'open_platform',
            'Authorization': access_token
        }
        
        for retry in range(max_retries):
            conn.request("POST", "/upload/v1/file/upload_async_result", payload, headers)
            res = conn.getresponse()
            data = res.read()
            response_data = json.loads(data.decode("utf-8"))
            
            if response_data.get("code") == 0:
                result_data = response_data.get("data", {})
                if result_data.get("completed", False):
                    return result_data
                time.sleep(retry_interval)
            else:
                return None
        
        return None