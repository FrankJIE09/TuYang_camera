#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Percipio深度相机官方SDK测试程序
包括基础功能、帧率、稳定性等测试
"""

import os
import sys
import time
import json
import numpy as np
import cv2
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

# 添加pcammls路径
sys.path.insert(0, '/usr/local/pcammls/PYTHON')
import pcammls


class NumpyEncoder(json.JSONEncoder):
    """ 自定义编码器，用于处理Numpy数据类型 """

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    success: bool
    data: Dict
    error_message: Optional[str] = None
    execution_time: float = 0.0


class DeviceEvent(pcammls.DeviceEvent):
    def __init__(self):
        pcammls.DeviceEvent.__init__(self)
        self.offline = False

    def run(self, handle, eventID):
        if eventID == pcammls.TY_EVENT_DEVICE_OFFLINE:
            print("设备离线事件")
            self.offline = True
        return 0


class PercipioCameraTester:
    """Percipio相机测试类"""

    def __init__(self, device_id: str = "207000159351"):
        self.device_id = device_id
        self.sdk = pcammls.PercipioSDK()
        self.handle = None
        self.event = None
        self.is_connected = False
        self.test_results: List[TestResult] = []
        self.depth_scale_factor = None  # 深度比例因子

        # 设置日志
        self.logger = logging.getLogger("PercipioCameraTester")
        self.logger.setLevel(logging.INFO)

        # 创建结果目录
        self.results_dir = Path("test_results")
        self.results_dir.mkdir(exist_ok=True)

        # 测试参数（快速测试版本）
        self.test_params = {
            'frame_rate_test_duration': 10,  # 帧率测试持续时间（设为0跳过）
            'repeatability_test_count': 1000,  # 重复精度测试次数
            'stability_test_duration': 10,  # 稳定性测试持续时间（设为0跳过）
            'noise_test_count': 5,  # 噪声测试次数
        }

    def setup_camera(self) -> bool:
        """设置相机连接"""
        try:
            print(f"正在连接相机 ID: {self.device_id}")

            dev_list = self.sdk.ListDevice()

            if len(dev_list) == 0:
                self.logger.error("未找到任何设备")
                return False

            print(f"找到 {len(dev_list)} 个设备:")
            for dev in dev_list:
                print(f"  {dev.id} - {dev.modelName}")

            # 直接使用设备ID连接
            self.handle = self.sdk.Open(self.device_id)
            if not self.sdk.isValidHandle(self.handle):
                self.logger.error("无法打开设备")
                return False

            self.event = DeviceEvent()
            self.sdk.DeviceRegiststerCallBackEvent(self.event)

            self.is_connected = True
            self.logger.info("设备连接成功！")

            # 读取深度比例因子
            try:
                self.depth_scale_factor = self.sdk.DeviceReadCalibDepthScaleUnit(self.handle)
                self.logger.info(f"深度比例因子: {self.depth_scale_factor}")
            except Exception as e:
                self.logger.warning(f"无法读取深度比例因子: {e}")
                self.depth_scale_factor = 0.016  # 使用默认值

            # 启用深度流
            ret = self.sdk.DeviceStreamEnable(self.handle, pcammls.PERCIPIO_STREAM_DEPTH)
            if ret != pcammls.TY_STATUS_OK:
                self.logger.error(f"启用深度流失败: {ret}")
                return False

            # 开始流传输
            ret = self.sdk.DeviceStreamOn(self.handle)
            if ret != pcammls.TY_STATUS_OK:
                self.logger.error(f"启动流失败: {ret}")
                return False

            self.logger.info("流传输已启动")
            time.sleep(2)  # 等待流稳定
            return True

        except Exception as e:
            self.logger.error(f"设置相机失败: {e}")
            return False

    def capture_single_frame(self) -> Optional[np.ndarray]:
        """捕获单帧深度图像"""
        if not self.is_connected:
            return None

        try:
            frames = self.sdk.DeviceStreamRead(self.handle, 5000)

            if len(frames) == 0:
                return None

            for frame in frames:
                if frame.streamID == pcammls.PERCIPIO_STREAM_DEPTH:
                    depth_data = frame.as_nparray()
                    return depth_data

            return None

        except Exception as e:
            self.logger.error(f"捕获帧失败: {e}")
            return None

    def run_test(self, test_func, test_name: str, **kwargs) -> TestResult:
        """运行单个测试"""
        start_time = time.time()
        result = TestResult(test_name=test_name, success=False, data={})

        try:
            self.logger.info(f"开始测试: {test_name}")
            data = test_func(**kwargs)
            result.data = data
            result.success = True
            self.logger.info(f"测试完成: {test_name}")

        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"测试失败 {test_name}: {e}")

        result.execution_time = time.time() - start_time
        self.test_results.append(result)
        return result

    def test_basic_functionality(self) -> Dict:
        """基础功能测试"""
        data = {
            'device_info': None,
            'single_capture': None,
            'depth_stats': None
        }

        # 获取设备信息
        dev_list = self.sdk.ListDevice()
        if dev_list:
            for dev in dev_list:
                if dev.id == self.device_id:
                    data['device_info'] = {
                        'id': dev.id,
                        'modelName': dev.modelName,
                        'ip': getattr(dev, 'ip', 'Unknown'),
                        'sn': getattr(dev, 'sn', 'Unknown')
                    }
                    break

        # 单次拍摄测试
        depth_data = self.capture_single_frame()
        if depth_data is not None:
            data['single_capture'] = {
                'has_depth': True,
                'depth_shape': depth_data.shape,
                'depth_dtype': str(depth_data.dtype)
            }

            # 深度统计
            valid_mask = (depth_data > 0) & (depth_data < 65535)  # 假设16位深度
            if np.any(valid_mask):
                valid_depths = depth_data[valid_mask].astype(np.float64)  # 转换为float64
                
                # 使用深度比例因子转换为毫米
                if self.depth_scale_factor is not None:
                    valid_depths_mm = valid_depths * self.depth_scale_factor
                else:
                    valid_depths_mm = valid_depths * 0.016  # 默认比例因子
                
                data['depth_stats'] = {
                    'valid_pixels': int(np.sum(valid_mask)),
                    'total_pixels': int(valid_mask.size),
                    'valid_ratio': float(np.sum(valid_mask) / valid_mask.size),
                    'min_depth': float(np.min(valid_depths_mm)),
                    'max_depth': float(np.max(valid_depths_mm)),
                    'mean_depth': float(np.mean(valid_depths_mm)),
                    'std_depth': float(np.std(valid_depths_mm))
                }

        return data

    def test_frame_rate(self) -> Dict:
        """帧率测试"""
        duration = self.test_params['frame_rate_test_duration']
        frame_times = []
        success_count = 0
        total_count = 0

        start_time = time.time()
        end_time = start_time + duration

        self.logger.info(f"开始帧率测试，持续时间: {duration}秒")

        # 创建基于时间的进度条
        with tqdm(total=duration, desc="帧率测试", unit="秒", ncols=80) as pbar:
            while time.time() < end_time:
                frame_start = time.time()

                # 捕获帧
                depth_data = self.capture_single_frame()

                if depth_data is not None:
                    frame_end = time.time()
                    frame_times.append(frame_end - frame_start)
                    success_count += 1
                    time.sleep(0.5)  # 等待0.5秒
                else:
                    self.logger.warning("拍摄失败")

                total_count += 1

                # 更新进度条
                elapsed = time.time() - start_time
                pbar.n = min(duration, int(elapsed))
                pbar.set_postfix({
                    '成功': success_count,
                    '总数': total_count,
                    '成功率': f"{success_count/total_count*100:.1f}%" if total_count > 0 else "0%"
                })
                pbar.refresh()

        # 计算帧率
        if frame_times:
            avg_frame_time = np.mean(frame_times)
            std_frame_time = np.std(frame_times)
            min_frame_time = np.min(frame_times)
            max_frame_time = np.max(frame_times)

            # 计算实际帧率
            fps = success_count / duration
            fps_filtered = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        else:
            avg_frame_time = std_frame_time = min_frame_time = max_frame_time = 0
            fps = fps_filtered = 0

        return {
            'duration': duration,
            'total_attempts': total_count,
            'successful_captures': success_count,
            'success_rate': success_count / total_count if total_count > 0 else 0,
            'fps': fps,
            'fps_filtered': fps_filtered,
            'avg_frame_time': avg_frame_time,
            'std_frame_time': std_frame_time,
            'min_frame_time': min_frame_time,
            'max_frame_time': max_frame_time,
            'frame_times': frame_times
        }

    def test_repeatability(self) -> Dict:
        """重复精度测试 - 多点测试"""
        count = self.test_params['repeatability_test_count']
        target_points = 25  # 目标测试点数
        depth_maps = []
        all_test_points = []  # 存储所有测试点的数据
        success_count = 0

        self.logger.info(f"开始重复精度测试，测试次数: {count}，目标测试点数: {target_points}")

        # 首先获取一帧来确定有效区域和采样点
        initial_depth = self.capture_single_frame()
        if initial_depth is None:
            return {'error': '无法获取初始深度图像'}

        # 计算有效区域
        valid_mask = (initial_depth > 0) & (initial_depth < 65535)
        if not np.any(valid_mask):
            return {'error': '未找到有效深度区域'}

        valid_coords = np.where(valid_mask)
        
        # 在有效区域内均匀采样点
        if len(valid_coords[0]) >= target_points:
            # 随机选择目标数量的点
            indices = np.random.choice(len(valid_coords[0]), target_points, replace=False)
            test_y_coords = valid_coords[0][indices]
            test_x_coords = valid_coords[1][indices]
        else:
            # 如果有效点不够，使用所有有效点
            test_y_coords = valid_coords[0]
            test_x_coords = valid_coords[1]
            target_points = len(test_y_coords)
            self.logger.warning(f"有效点数量不足，使用所有 {target_points} 个有效点")

        self.logger.info(f"选择了 {target_points} 个测试点")

        # 为每个测试点创建数据存储
        point_data = {i: [] for i in range(target_points)}

        # 使用tqdm显示进度
        with tqdm(total=count, desc="重复精度测试", unit="次", ncols=80) as pbar:
            for i in range(count):
                # 在每次拍照前等待1秒，确保获取新图像
                time.sleep(1)
                
                # 捕获深度图像
                depth_data = self.capture_single_frame()

                if depth_data is not None:
                    # 记录每个测试点的深度值
                    for j in range(target_points):
                        y, x = test_y_coords[j], test_x_coords[j]
                        if 0 <= y < depth_data.shape[0] and 0 <= x < depth_data.shape[1]:
                            depth_value = depth_data[y, x]
                            if depth_value > 0 and depth_value < 65535:
                                # 使用深度比例因子转换为毫米
                                if self.depth_scale_factor is not None:
                                    depth_mm = depth_value * self.depth_scale_factor
                                else:
                                    depth_mm = depth_value * 0.016  # 默认比例因子
                                point_data[j].append(depth_mm)

                    depth_maps.append(depth_data)
                    success_count += 1

                    self.logger.debug(f"重复精度测试进度: {i + 1}/{count}")
                else:
                    self.logger.warning(f"第{i + 1}次拍摄失败")

                # 更新进度条
                pbar.update(1)
                pbar.set_postfix({
                    '成功': success_count,
                    '成功率': f"{success_count/(i+1)*100:.1f}%"
                })

        # 分析每个测试点的重复精度
        point_analysis = []
        valid_points = 0

        for i in range(target_points):
            if len(point_data[i]) >= 2:  # 至少需要2个有效测量值
                # 现在point_data[i]只包含深度值
                try:
                    depths = np.array(point_data[i], dtype=np.float64)
                    
                    # 计算该点的统计信息
                    mean_depth = np.mean(depths)
                    std_depth = np.std(depths)
                    max_depth_deviation = np.max(np.abs(depths - mean_depth))
                    depth_range = np.max(depths) - np.min(depths)
                    
                    point_analysis.append({
                        'point_id': i,
                        'coordinates': [test_x_coords[i], test_y_coords[i]],
                        'measurement_count': len(depths),
                        'mean_depth': mean_depth,
                        'std_depth': std_depth,
                        'max_depth_deviation': max_depth_deviation,
                        'depth_range': depth_range
                    })
                    valid_points += 1
                except Exception as e:
                    self.logger.warning(f"处理测试点 {i} 时出错: {e}")
                    continue

        if valid_points == 0:
            return {'error': '没有足够的有效测试点数据'}

        # 计算整体统计
        all_depth_stds = [p['std_depth'] for p in point_analysis]
        all_depth_deviations = [p['max_depth_deviation'] for p in point_analysis]
        all_depth_ranges = [p['depth_range'] for p in point_analysis]
        
        overall_stats = {
            'mean_depth_std': np.mean(all_depth_stds),
            'std_depth_std': np.std(all_depth_stds),
            'max_depth_std': np.max(all_depth_stds),
            'mean_depth_deviation': np.mean(all_depth_deviations),
            'std_depth_deviation': np.std(all_depth_deviations),
            'max_depth_deviation': np.max(all_depth_deviations),
            'mean_depth_range': np.mean(all_depth_ranges),
            'std_depth_range': np.std(all_depth_ranges)
        }

        return {
            'test_count': count,
            'success_count': success_count,
            'success_rate': success_count / count,
            'target_points': target_points,
            'valid_points': valid_points,
            'overall_stats': overall_stats,
            'point_analysis': point_analysis,
            'test_point_coordinates': [[test_x_coords[i], test_y_coords[i]] for i in range(target_points)],
            'raw_depth_data': point_data  # 保存每个点的原始深度数据
        }

    def test_stability(self) -> Dict:
        """稳定性测试"""
        duration = self.test_params['stability_test_duration']
        interval = 1.0  # 每秒拍摄一次
        measurements = []
        start_time = time.time()

        self.logger.info(f"开始稳定性测试，持续时间: {duration}秒")

        # 创建基于时间的进度条
        with tqdm(total=duration, desc="稳定性测试", unit="秒", ncols=80) as pbar:
            while time.time() - start_time < duration:
                test_start = time.time()

                # 捕获深度图像
                depth_data = self.capture_single_frame()

                if depth_data is not None:
                    # 计算深度统计
                    valid_mask = (depth_data > 0) & (depth_data < 65535)
                    if np.any(valid_mask):
                        valid_depths = depth_data[valid_mask]
                        
                        # 使用深度比例因子转换为毫米
                        if self.depth_scale_factor is not None:
                            mean_depth_mm = float(np.mean(valid_depths)) * self.depth_scale_factor
                            std_depth_mm = float(np.std(valid_depths)) * self.depth_scale_factor
                            min_depth_mm = float(np.min(valid_depths)) * self.depth_scale_factor
                            max_depth_mm = float(np.max(valid_depths)) * self.depth_scale_factor
                        else:
                            mean_depth_mm = float(np.mean(valid_depths)) * 0.016
                            std_depth_mm = float(np.std(valid_depths)) * 0.016
                            min_depth_mm = float(np.min(valid_depths)) * 0.016
                            max_depth_mm = float(np.max(valid_depths)) * 0.016
                        
                        measurement = {
                            'timestamp': time.time() - start_time,
                            'valid_pixels': int(np.sum(valid_mask)),
                            'total_pixels': int(valid_mask.size),
                            'valid_ratio': float(np.sum(valid_mask) / valid_mask.size),
                            'mean_depth': mean_depth_mm,
                            'std_depth': std_depth_mm,
                            'min_depth': min_depth_mm,
                            'max_depth': max_depth_mm
                        }
                        measurements.append(measurement)
                    else:
                        self.logger.warning("稳定性测试：无有效深度数据")
                else:
                    self.logger.warning("稳定性测试拍摄失败")

                # 等待到下一个间隔
                elapsed = time.time() - test_start
                if elapsed < interval:
                    time.sleep(interval - elapsed)

                # 更新进度条
                elapsed_total = time.time() - start_time
                pbar.n = min(duration, int(elapsed_total))
                pbar.set_postfix({
                    '测量数': len(measurements),
                    '平均深度': f"{measurements[-1]['mean_depth']:.1f}" if measurements else "N/A"
                })
                pbar.refresh()

        # 分析稳定性
        if measurements:
            success_rate = len(measurements) / int(duration / interval)

            # 分析深度稳定性
            valid_pixels_counts = [m['valid_pixels'] for m in measurements]
            mean_depths = [m['mean_depth'] for m in measurements]

            stability_metrics = {
                'valid_pixels_mean': np.mean(valid_pixels_counts),
                'valid_pixels_std': np.std(valid_pixels_counts),
                'mean_depth_mean': np.mean(mean_depths),
                'mean_depth_std': np.std(mean_depths)
            }
        else:
            success_rate = 0
            stability_metrics = {}

        return {
            'duration': duration,
            'total_measurements': len(measurements),
            'success_rate': success_rate,
            'stability_metrics': stability_metrics,
            'measurements': measurements[:50]  # 只保存前50个测量值
        }

    def test_noise(self) -> Dict:
        """噪声测试"""
        count = self.test_params['noise_test_count']
        depth_maps = []
        success_count = 0

        self.logger.info(f"开始噪声测试，测试次数: {count}")

        # 使用tqdm显示进度
        with tqdm(total=count, desc="噪声测试", unit="次", ncols=80) as pbar:
            for i in range(count):
                depth_data = self.capture_single_frame()

                if depth_data is not None:
                    # 确保深度数据转换为float64以保持精度
                    depth_data_float = depth_data.astype(np.float64)
                    depth_maps.append(depth_data_float)
                    success_count += 1
                    time.sleep(0.5)  # 等待0.5秒
                else:
                    self.logger.warning(f"第{i + 1}次噪声测试拍摄失败")

                # 更新进度条
                pbar.update(1)
                pbar.set_postfix({
                    '成功': success_count,
                    '成功率': f"{success_count/(i+1)*100:.1f}%"
                })

        if len(depth_maps) < 2:
            return {'error': '有效数据不足，无法分析噪声'}

        # 转换为numpy数组，确保使用float64类型
        depth_maps = np.array(depth_maps, dtype=np.float64)

        # 计算噪声统计
        # 假设相机和场景静止，深度变化主要由噪声引起
        mean_depth = np.mean(depth_maps, axis=0)
        std_depth = np.std(depth_maps, axis=0)

        # 计算有效区域的噪声
        valid_mask = (mean_depth > 0) & (mean_depth < 65535)
        if np.any(valid_mask):
            noise_mean = np.mean(std_depth[valid_mask])
            noise_std = np.std(std_depth[valid_mask])
            noise_max = np.max(std_depth[valid_mask])
            
            # 使用深度比例因子转换为毫米
            if self.depth_scale_factor is not None:
                noise_mean *= self.depth_scale_factor
                noise_std *= self.depth_scale_factor
                noise_max *= self.depth_scale_factor
            else:
                noise_mean *= 0.016
                noise_std *= 0.016
                noise_max *= 0.016
        else:
            noise_mean = noise_std = noise_max = 0

        return {
            'test_count': count,
            'success_count': success_count,
            'success_rate': success_count / count,
            'noise_mean': noise_mean,
            'noise_std': noise_std,
            'noise_max': noise_max,
            'mean_depth_shape': mean_depth.shape,
            'valid_pixels_ratio': np.sum(valid_mask) / valid_mask.size if valid_mask.size > 0 else 0
        }

    def run_all_tests(self) -> List[TestResult]:
        """运行所有测试"""
        if not self.setup_camera():
            self.logger.error("相机设置失败，无法进行测试")
            return []

        # 基础功能测试
        self.run_test(self.test_basic_functionality, "基础功能测试")

        # 帧率测试（如果持续时间大于0）
        if self.test_params['frame_rate_test_duration'] > 0:
            self.run_test(self.test_frame_rate, "帧率测试")

        # 重复精度测试
        self.run_test(self.test_repeatability, "重复精度测试")

        # 稳定性测试（如果持续时间大于0）
        if self.test_params['stability_test_duration'] > 0:
            self.run_test(self.test_stability, "稳定性测试")

        # 噪声测试（如果测试次数大于0）
        if self.test_params['noise_test_count'] > 0:
            self.run_test(self.test_noise, "噪声测试")

        return self.test_results

    def close(self):
        """关闭设备连接"""
        try:
            if self.is_connected and self.handle:
                # 先停止流传输
                try:
                    self.sdk.DeviceStreamOff(self.handle)
                except Exception as e:
                    self.logger.warning(f"停止流传输时出错: {e}")
                
                # 等待一下确保流完全停止
                time.sleep(0.5)
                
                # 关闭设备
                try:
                    self.sdk.Close(self.handle)
                except Exception as e:
                    self.logger.warning(f"关闭设备时出错: {e}")
                
                self.is_connected = False
                self.handle = None
                self.logger.info("设备连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭设备时出现异常: {e}")
            # 强制重置状态
            self.is_connected = False
            self.handle = None

    def save_results(self, filename: Optional[str] = None):
        """保存测试结果"""
        if filename is None:
            timestamp = int(time.time())
            filename = f"percipio_test_results_{timestamp}.json"

        filepath = self.results_dir / filename

        # 准备保存的数据
        save_data = {
            'test_timestamp': time.time(),
            'device_id': self.device_id,
            'test_params': self.test_params,
            'results': []
        }

        for result in self.test_results:
            result_data = {
                'test_name': result.test_name,
                'success': result.success,
                'execution_time': result.execution_time,
                'error_message': result.error_message,
                'data': result.data
            }
            save_data['results'].append(result_data)

        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

        self.logger.info(f"测试结果已保存: {filepath}")
        return filepath

    def generate_report(self, output_file: Optional[str] = None):
        """生成测试报告"""
        if output_file is None:
            timestamp = int(time.time())
            output_file = f"percipio_test_report_{timestamp}.md"

        filepath = self.results_dir / output_file

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Percipio深度相机测试报告\n\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"设备ID: {self.device_id}\n\n")

            # 测试参数
            f.write("## 测试参数\n\n")
            for key, value in self.test_params.items():
                f.write(f"- {key}: {value}\n")
            f.write("\n")

            # 测试结果摘要
            f.write("## 测试结果摘要\n\n")
            total_tests = len(self.test_results)
            successful_tests = sum(1 for r in self.test_results if r.success)
            f.write(f"- 总测试数: {total_tests}\n")
            f.write(f"- 成功测试数: {successful_tests}\n")
            if total_tests > 0:
                f.write(f"- 成功率: {successful_tests / total_tests * 100:.1f}%\n\n")
            else:
                f.write("- 成功率: 0.0%\n\n")

            # 详细结果
            f.write("## 详细测试结果\n\n")
            for result in self.test_results:
                f.write(f"### {result.test_name}\n\n")
                f.write(f"- 状态: {'成功' if result.success else '失败'}\n")
                f.write(f"- 执行时间: {result.execution_time:.2f}秒\n")

                if result.error_message:
                    f.write(f"- 错误信息: {result.error_message}\n")

                if result.success and result.data:
                    f.write("- 测试数据:\n")
                    f.write("```json\n")
                    f.write(json.dumps(result.data, indent=2, ensure_ascii=False, cls=NumpyEncoder))
                    f.write("\n```\n")

                if result.test_name == "重复精度测试":
                    stats = result.data.get('overall_stats', {})
                    f.write(f"- 重复精度（深度标准差）: {stats.get('mean_depth_std', 0):.3f} mm\n")
                    f.write(f"- 最大深度波动: {stats.get('max_depth_deviation', 0):.3f} mm\n")
                    
                    # 显示深度比例因子信息
                    if hasattr(self, 'depth_scale_factor') and self.depth_scale_factor:
                        f.write(f"- 深度比例因子: {self.depth_scale_factor}\n")
                        f.write("- 深度值已转换为毫米单位\n")
                    
                    # 显示每个点的详细深度数据
                    raw_data = result.data.get('raw_depth_data', {})
                    if raw_data:
                        f.write("- 每个测试点的详细深度数据（单位：毫米）:\n")
                        for point_id in range(min(5, len(raw_data))):  # 只显示前5个点
                            depths = raw_data.get(point_id, [])
                            if depths:
                                f.write(f"  - 测试点 {point_id}: {depths}\n")
                        if len(raw_data) > 5:
                            f.write(f"  - ... 还有 {len(raw_data) - 5} 个测试点\n")

                f.write("\n")

        self.logger.info(f"测试报告已生成: {filepath}")
        return filepath


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建测试器
    tester = PercipioCameraTester()

    try:
        # 运行所有测试
        print("开始Percipio深度相机全面测试...")
        results = tester.run_all_tests()

        # 立即保存结果和生成报告
        results_file = tester.save_results()
        report_file = tester.generate_report()

        # 打印摘要
        print("\n" + "=" * 50)
        print("测试完成！")
        print(f"结果文件: {results_file}")
        print(f"报告文件: {report_file}")

        successful_tests = sum(1 for r in results if r.success)
        print(f"成功测试: {successful_tests}/{len(results)}")

        # 显示关键结果
        for result in results:
            if result.success and result.data:
                if result.test_name == "帧率测试":
                    fps = result.data.get('fps', 0)
                    print(f"帧率: {fps:.2f} FPS")
                elif result.test_name == "重复精度测试":
                    stats = result.data.get('overall_stats', {})
                    print(f"重复精度（深度标准差）: {stats.get('mean_depth_std', 0):.3f} mm")
                    print(f"最大深度波动: {stats.get('max_depth_deviation', 0):.3f} mm")
                    if hasattr(tester, 'depth_scale_factor') and tester.depth_scale_factor:
                        print(f"深度比例因子: {tester.depth_scale_factor}")
                elif result.test_name == "稳定性测试":
                    metrics = result.data.get('stability_metrics', {})
                    print(f"稳定性测试 - 平均深度: {metrics.get('mean_depth_mean', 0):.1f} mm")
                    print(f"稳定性测试 - 深度标准差: {metrics.get('mean_depth_std', 0):.3f} mm")
                elif result.test_name == "噪声测试":
                    print(f"噪声测试 - 平均噪声: {result.data.get('noise_mean', 0):.3f} mm")
                    print(f"噪声测试 - 噪声标准差: {result.data.get('noise_std', 0):.3f} mm")
                    print(f"噪声测试 - 最大噪声: {result.data.get('noise_max', 0):.3f} mm")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        # 即使出错也尝试保存已完成的测试结果
        try:
            if hasattr(tester, 'test_results') and tester.test_results:
                results_file = tester.save_results()
                report_file = tester.generate_report()
                print(f"已保存部分结果: {results_file}")
                print(f"已生成部分报告: {report_file}")
        except Exception as save_error:
            print(f"保存结果时出错: {save_error}")
    finally:
        # 确保设备连接被正确关闭
        try:
            if hasattr(tester, 'is_connected') and tester.is_connected:
                tester.close()
        except Exception as close_error:
            print(f"关闭设备时出错: {close_error}")
            pass


if __name__ == "__main__":
    main()