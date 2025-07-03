#!/bin/bash

# Percipio Python SDK 自动安装脚本
# 作者: AI Assistant
# 版本: 1.0
# 日期: 2025-07-03

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要使用root用户运行此脚本"
        exit 1
    fi
}

# 检查系统架构
check_architecture() {
    ARCH=$(uname -m)
    log_info "检测到系统架构: $ARCH"
    
    case $ARCH in
        x86_64)
            CAMPORT_ARCH="x64"
            ;;
        aarch64|arm64)
            CAMPORT_ARCH="Aarch64"
            ;;
        armv7l)
            CAMPORT_ARCH="armv7hf"
            ;;
        i686|i386)
            CAMPORT_ARCH="i686"
            ;;
        *)
            log_error "不支持的架构: $ARCH"
            exit 1
            ;;
    esac
    
    log_info "使用架构: $CAMPORT_ARCH"
}

# 检查Python版本
check_python() {
    log_info "检查Python环境..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_info "Python版本: $PYTHON_VERSION"
        
        # 检查是否为Python 3.8+
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 8 ]]; then
            log_success "Python版本符合要求"
        else
            log_warning "建议使用Python 3.8或更高版本"
        fi
    else
        log_error "未找到Python3，请先安装Python3"
        exit 1
    fi
}

# 安装系统依赖
install_system_deps() {
    log_info "安装系统依赖..."
    
    # 检测包管理器
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        log_info "使用apt-get安装依赖..."
        sudo apt-get update
        sudo apt-get install -y \
            build-essential \
            cmake \
            swig \
            python3-dev \
            python3-pip \
            libusb-1.0-0-dev \
            git \
            wget \
            curl
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        log_info "使用yum安装依赖..."
        sudo yum groupinstall -y "Development Tools"
        sudo yum install -y \
            cmake \
            swig \
            python3-devel \
            python3-pip \
            libusb1-devel \
            git \
            wget \
            curl
    elif command -v dnf &> /dev/null; then
        # Fedora
        log_info "使用dnf安装依赖..."
        sudo dnf groupinstall -y "Development Tools"
        sudo dnf install -y \
            cmake \
            swig \
            python3-devel \
            python3-pip \
            libusb1-devel \
            git \
            wget \
            curl
    else
        log_error "不支持的包管理器，请手动安装依赖"
        exit 1
    fi
    
    log_success "系统依赖安装完成"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    # 降级numpy到1.x版本以兼容pcammls
    pip3 install "numpy<2"
    pip3 install opencv-python matplotlib
    
    log_success "Python依赖安装完成"
}

# 下载并编译pcammls
install_pcammls() {
    log_info "开始安装pcammls..."
    
    # 创建临时目录
    TEMP_DIR="/tmp/pcammls_install"
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # 克隆pcammls仓库
    log_info "克隆pcammls仓库..."
    if git clone https://github.com/alphaliang/pcammls.git .; then
        log_success "仓库克隆成功"
    else
        log_error "仓库克隆失败"
        exit 1
    fi
    
    # 创建构建目录
    mkdir -p build
    cd build
    
    # 配置cmake
    log_info "配置cmake构建..."
    if cmake .. -DCAMPORT_ARCH=$CAMPORT_ARCH; then
        log_success "cmake配置成功"
    else
        log_error "cmake配置失败"
        exit 1
    fi
    
    # 编译
    log_info "开始编译..."
    CPU_CORES=$(nproc)
    if make -j$CPU_CORES; then
        log_success "编译成功"
    else
        log_error "编译失败"
        exit 1
    fi
    
    # 安装
    log_info "安装到系统..."
    if sudo make install; then
        log_success "安装成功"
    else
        log_error "安装失败"
        exit 1
    fi
    
    # 更新动态链接库缓存
    sudo ldconfig
    
    # 清理临时目录
    cd /
    rm -rf "$TEMP_DIR"
    
    log_success "pcammls安装完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    # 创建环境变量配置文件
    ENV_FILE="$HOME/.percipio_env"
    cat > "$ENV_FILE" << EOF
# Percipio Python SDK 环境配置
export PYTHONPATH=/usr/local/pcammls/PYTHON:\$PYTHONPATH
export LD_LIBRARY_PATH=/usr/local/pcammls/lib64:\$LD_LIBRARY_PATH
EOF
    
    # 添加到bashrc
    if ! grep -q "percipio_env" "$HOME/.bashrc"; then
        echo "" >> "$HOME/.bashrc"
        echo "# Percipio SDK 环境配置" >> "$HOME/.bashrc"
        echo "source $ENV_FILE" >> "$HOME/.bashrc"
        log_success "环境变量已添加到 ~/.bashrc"
    else
        log_info "环境变量已存在于 ~/.bashrc"
    fi
    
    # 立即加载环境变量
    source "$ENV_FILE"
    
    log_success "环境变量配置完成"
}

# 测试安装
test_installation() {
    log_info "测试安装..."
    
    # 测试pcammls导入
    if python3 -c "import pcammls; print('pcammls导入成功！')" 2>/dev/null; then
        log_success "pcammls导入测试通过"
    else
        log_error "pcammls导入测试失败"
        return 1
    fi
    
    # 测试基本功能
    if python3 -c "
import pcammls
sdk = pcammls.PercipioSDK()
dev_list = sdk.ListDevice()
print(f'找到 {len(dev_list)} 个设备')
" 2>/dev/null; then
        log_success "基本功能测试通过"
    else
        log_warning "基本功能测试失败（可能是没有连接设备）"
    fi
    
    log_success "安装测试完成"
}

# 创建示例脚本
create_examples() {
    log_info "创建示例脚本..."
    
    # 获取当前目录
    CURRENT_DIR=$(pwd)
    
    # 创建示例目录
    EXAMPLES_DIR="$CURRENT_DIR/examples"
    mkdir -p "$EXAMPLES_DIR"
    
    # 创建简单的测试脚本
    cat > "$EXAMPLES_DIR/test_sdk.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Percipio SDK 测试脚本
"""

import sys
sys.path.insert(0, '/usr/local/pcammls/PYTHON')
import pcammls

def test_sdk():
    print("=== Percipio SDK 测试 ===")
    
    try:
        # 创建SDK实例
        sdk = pcammls.PercipioSDK()
        print("✓ SDK实例创建成功")
        
        # 列出设备
        dev_list = sdk.ListDevice()
        print(f"✓ 找到 {len(dev_list)} 个设备")
        
        for i, dev in enumerate(dev_list):
            print(f"  设备 {i+1}: {dev.id} - {dev.modelName}")
        
        if len(dev_list) > 0:
            print("✓ 设备检测正常")
        else:
            print("⚠ 未检测到设备（请检查连接）")
        
        print("✓ SDK测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_sdk()
EOF
    
    # 创建快速采集脚本
    cat > "$EXAMPLES_DIR/quick_capture.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速采集脚本
"""

import sys
import os
sys.path.insert(0, '/usr/local/pcammls/PYTHON')
import pcammls
import cv2
import time
from datetime import datetime

def quick_capture():
    print("=== 快速采集测试 ===")
    
    try:
        sdk = pcammls.PercipioSDK()
        dev_list = sdk.ListDevice()
        
        if len(dev_list) == 0:
            print("未找到设备")
            return False
        
        # 使用第一个设备
        device_id = dev_list[0].id
        print(f"使用设备: {device_id}")
        
        # 打开设备
        handle = sdk.Open(device_id)
        if not sdk.isValidHandle(handle):
            print("无法打开设备")
            return False
        
        # 启用深度流
        sdk.DeviceStreamEnable(handle, pcammls.PERCIPIO_STREAM_DEPTH)
        sdk.DeviceStreamOn(handle)
        
        print("等待流稳定...")
        time.sleep(2)
        
        # 采集一帧
        frames = sdk.DeviceStreamRead(handle, 2000)
        if len(frames) > 0:
            for frame in frames:
                if frame.streamID == pcammls.PERCIPIO_STREAM_DEPTH:
                    depth_data = frame.as_nparray()
                    if depth_data is not None:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"quick_capture_{timestamp}.png"
                        cv2.imwrite(filename, depth_data)
                        print(f"✓ 图像已保存: {filename}")
                        break
        
        # 清理
        sdk.DeviceStreamOff(handle)
        sdk.Close(handle)
        
        print("✓ 快速采集完成")
        return True
        
    except Exception as e:
        print(f"✗ 采集失败: {e}")
        return False

if __name__ == "__main__":
    quick_capture()
EOF
    
    # 设置执行权限
    chmod +x "$EXAMPLES_DIR/test_sdk.py"
    chmod +x "$EXAMPLES_DIR/quick_capture.py"
    
    log_success "示例脚本创建完成: $EXAMPLES_DIR"
}

# 显示使用说明
show_usage() {
    echo ""
    echo "=========================================="
    echo "Percipio Python SDK 安装完成！"
    echo "=========================================="
    echo ""
    echo "📁 安装位置: /usr/local/pcammls/"
    echo "🐍 Python包: pcammls"
    echo "🔧 架构: $CAMPORT_ARCH"
    echo ""
    echo "📋 使用方法:"
    echo "1. 重新加载环境变量:"
    echo "   source ~/.bashrc"
    echo ""
    echo "2. 测试SDK:"
    echo "   python3 examples/test_sdk.py"
    echo ""
    echo "3. 快速采集:"
    echo "   python3 examples/quick_capture.py"
    echo ""
    echo "4. 导入SDK:"
    echo "   python3 -c \"import pcammls; print('SDK导入成功')\""
    echo ""
    echo "📚 示例脚本位置: $PWD/examples/"
    echo "🔗 官方文档: https://doc.percipio.xyz/cam/latest/index.html"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "Percipio Python SDK 自动安装脚本"
    echo "=========================================="
    echo ""
    
    # 检查系统
    check_root
    check_architecture
    check_python
    
    # 安装依赖
    install_system_deps
    install_python_deps
    
    # 安装pcammls
    install_pcammls
    
    # 配置环境
    setup_environment
    
    # 测试安装
    test_installation
    
    # 创建示例
    create_examples
    
    # 显示使用说明
    show_usage
}

# 运行主函数
main "$@" 