# Percipio深度相机Python SDK项目

这是一个用于Percipio深度相机的Python SDK配置和图像采集项目。项目包含了完整的SDK安装、环境配置和图像采集功能。

## 📋 项目概述

- **相机型号**: VMD02-4070
- **设备ID**: 207000159351
- **相机IP**: 192.168.6.203
- **支持功能**: 深度图像采集
- **SDK版本**: Percipio官方Python SDK (pcammls)

## 🚀 快速开始

### 1. 系统要求

- Linux系统 (Ubuntu 20.04+)
- Python 3.8+
- Conda (推荐) 或 系统Python
- 网络连接的Percipio深度相机

### 2. 自动安装SDK

```bash
# 克隆项目
git clone <your-repo-url>
cd camport3

# 运行自动安装脚本
chmod +x install_sdk.sh
./install_sdk.sh
```

### 3. 配置Conda环境

```bash
# 创建新的conda环境
chmod +x setup_conda_env.sh
./setup_conda_env.sh my_percipio_env

# 激活环境
conda activate my_percipio_env
```

### 4. 采集图像

```bash
# 运行官方SDK采集脚本
export PYTHONPATH=/usr/local/pcammls/PYTHON:$PYTHONPATH
python3 official_capture.py
```

## 📁 项目结构

```
camport3/
├── install_sdk.sh              # SDK自动安装脚本
├── setup_conda_env.sh          # Conda环境配置脚本
├── official_capture.py         # 官方SDK图像采集脚本
├── captured_images/            # 采集的图像存储目录
│   ├── color/                  # 彩色图像 (如果支持)
│   └── depth/                  # 深度图像
├── lib/                        # SDK库文件
├── include/                    # SDK头文件
├── sample/                     # C++示例代码
└── README.md                   # 项目说明文档
```

## 🔧 安装说明

### 方法一：自动安装 (推荐)

使用提供的脚本自动完成所有安装步骤：

```bash
./install_sdk.sh
```

该脚本会自动：
- 安装系统依赖 (cmake, swig, python3-dev等)
- 下载并编译pcammls Python绑定
- 配置环境变量
- 测试SDK功能

### 方法二：手动安装

1. **安装系统依赖**
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake swig python3-dev python3-pip libusb-1.0-0-dev git
```

2. **安装Python依赖**
```bash
pip install "numpy<2" opencv-python matplotlib
```

3. **编译pcammls**
```bash
git clone https://github.com/alphaliang/pcammls.git
cd pcammls
mkdir build && cd build
cmake .. -DCAMPORT_ARCH=x64
make -j$(nproc)
sudo make install
sudo ldconfig
```

4. **配置环境变量**
```bash
echo 'export PYTHONPATH=/usr/local/pcammls/PYTHON:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc
```

## 🐍 Conda环境配置

### 创建新环境

```bash
./setup_conda_env.sh my_env_name
```

### 在当前环境配置

```bash
# 激活您的conda环境
conda activate your_env

# 运行配置脚本
./setup_conda_env_current.sh
```

## 📸 图像采集

### 使用官方SDK采集

```python
import pcammls
import cv2
import numpy as np

# 创建SDK实例
sdk = pcammls.PercipioSDK()

# 列出设备
dev_list = sdk.ListDevice()
print(f"找到 {len(dev_list)} 个设备")

# 连接设备
handle = sdk.Open(dev_list[0].id)

# 启用深度流
sdk.DeviceStreamEnable(handle, pcammls.PERCIPIO_STREAM_DEPTH)
sdk.DeviceStreamOn(handle)

# 采集图像
frames = sdk.DeviceStreamRead(handle, 2000)
for frame in frames:
    if frame.streamID == pcammls.PERCIPIO_STREAM_DEPTH:
        depth_data = frame.as_nparray()
        cv2.imwrite("depth_image.png", depth_data)
        break

# 清理
sdk.DeviceStreamOff(handle)
sdk.Close(handle)
```

### 运行采集脚本

```bash
# 使用官方脚本采集5张深度图像
python3 official_capture.py
```

## 🔍 设备信息

### 相机规格

- **型号**: VMD02-4070
- **序列号**: 207000159351
- **IP地址**: 192.168.6.203
- **MAC地址**: 06:23:E9:1E:35:38
- **支持流**: 深度流 (1536×2048)

### 网络配置

- **电脑IP**: 192.168.6.54
- **相机IP**: 192.168.6.203
- **子网掩码**: 255.255.255.0
- **网络接口**: eth-e8:80:88:b6:86:f9

## 🛠️ 故障排除

### 常见问题

1. **SDK导入失败**
   ```bash
   # 检查环境变量
   echo $PYTHONPATH
   
   # 重新设置
   export PYTHONPATH=/usr/local/pcammls/PYTHON:$PYTHONPATH
   ```

2. **设备连接失败**
   ```bash
   # 检查网络连接
   ping 192.168.6.203
   
   # 检查设备列表
   ./sample/build/bin/ListDevices
   ```

3. **编译错误**
   ```bash
   # 检查依赖
   sudo apt-get install -y build-essential cmake swig python3-dev
   
   # 清理重新编译
   cd pcammls/build
   make clean
   make -j$(nproc)
   ```

### 日志查看

```bash
# 查看SDK日志
export TY_LOG_LEVEL=3
python3 your_script.py
```

## 📚 参考资料

- [Percipio官方文档](https://doc.percipio.xyz/cam/latest/index.html)
- [pcammls GitHub仓库](https://github.com/alphaliang/pcammls)
- [Percipio官网](https://www.percipio.xyz)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 📄 许可证

本项目基于Percipio SDK开发，请遵循相关许可证要求。

## 📞 支持

如有问题，请：
1. 查看[故障排除](#故障排除)部分
2. 提交GitHub Issue
3. 联系Percipio技术支持

---

**最后更新**: 2025-07-03
**版本**: 1.0.0 