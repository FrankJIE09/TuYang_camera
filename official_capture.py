#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Percipio深度相机官方Python SDK采集脚本
"""

import os
import sys
import time
import cv2
import numpy as np
from datetime import datetime

# 添加pcammls路径
sys.path.insert(0, '/usr/local/pcammls/PYTHON')
import pcammls

class PercipioCapture:
    def __init__(self, device_id="207000159351"):
        self.device_id = device_id
        self.sdk = pcammls.PercipioSDK()
        self.handle = None
        self.event = None
        self.is_connected = False
        
        # 创建输出目录
        self.output_dir = "captured_images"
        self.color_dir = os.path.join(self.output_dir, "color")
        self.depth_dir = os.path.join(self.output_dir, "depth")
        
        for dir_path in [self.output_dir, self.color_dir, self.depth_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
    
    def connect_device(self):
        """连接相机"""
        print(f"正在连接相机 ID: {self.device_id}")
        
        dev_list = self.sdk.ListDevice()
        
        if len(dev_list) == 0:
            print("未找到任何设备")
            return False
        
        print(f"找到 {len(dev_list)} 个设备:")
        for dev in dev_list:
            print(f"  {dev.id} - {dev.modelName}")
        
        # 直接使用设备ID连接
        self.handle = self.sdk.Open(self.device_id)
        if not self.sdk.isValidHandle(self.handle):
            print("无法打开设备")
            return False
        
        self.event = DeviceEvent()
        self.sdk.DeviceRegiststerCallBackEvent(self.event)
        
        self.is_connected = True
        print("设备连接成功！")
        return True
    
    def enable_streams(self):
        """启用深度流"""
        if not self.is_connected:
            return False
        
        print("启用深度流...")
        
        ret = self.sdk.DeviceStreamEnable(self.handle, pcammls.PERCIPIO_STREAM_DEPTH)
        if ret != pcammls.TY_STATUS_OK:
            print(f"启用深度流失败: {ret}")
            return False
        
        print("深度流启用成功")
        return True
    
    def start_stream(self):
        """开始流传输"""
        if not self.is_connected:
            return False
        
        print("开始流传输...")
        ret = self.sdk.DeviceStreamOn(self.handle)
        if ret != pcammls.TY_STATUS_OK:
            print(f"启动流失败: {ret}")
            return False
        
        print("流传输已启动")
        return True
    
    def capture_frames(self, num_frames=5):
        """采集指定数量的帧"""
        if not self.is_connected:
            return
        
        print(f"开始采集 {num_frames} 帧图像...")
        
        for frame_idx in range(num_frames):
            print(f"采集第 {frame_idx + 1}/{num_frames} 帧...")
            
            frames = self.sdk.DeviceStreamRead(self.handle, 2000)
            
            if len(frames) == 0:
                print("未读取到帧数据")
                continue
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for frame in frames:
                if frame.streamID == pcammls.PERCIPIO_STREAM_DEPTH:
                    depth_data = frame.as_nparray()
                    if depth_data is not None:
                        depth_filename = f"depth_frame_{frame_idx:02d}_{timestamp}.png"
                        depth_path = os.path.join(self.depth_dir, depth_filename)
                        cv2.imwrite(depth_path, depth_data)
                        print(f"  深度图像已保存: {depth_path}")
            
            time.sleep(1.0)
        
        print("采集完成！")
    
    def close(self):
        """关闭设备连接"""
        if self.is_connected and self.handle:
            self.sdk.DeviceStreamOff(self.handle)
            self.sdk.Close(self.handle)
            self.is_connected = False
            print("设备连接已关闭")


class DeviceEvent(pcammls.DeviceEvent):
    def __init__(self):
        pcammls.DeviceEvent.__init__(self)
        self.offline = False
    
    def run(self, handle, eventID):
        if eventID == pcammls.TY_EVENT_DEVICE_OFFLINE:
            print("设备离线事件")
            self.offline = True
        return 0


def main():
    print("=== Percipio深度相机官方Python SDK采集程序 ===")
    
    capture = PercipioCapture()
    
    try:
        if not capture.connect_device():
            return
        
        if not capture.enable_streams():
            return
        
        if not capture.start_stream():
            return
        
        print("等待流稳定...")
        time.sleep(2)
        
        capture.capture_frames(num_frames=5)
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        capture.close()


if __name__ == "__main__":
    main() 