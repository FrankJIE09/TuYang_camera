#!/bin/bash

# Percipio SDK 当前conda环境配置脚本
set -e

echo "==== Percipio SDK 当前conda环境配置脚本 ===="

# 检查conda环境
if [[ -z "$CONDA_PREFIX" ]]; then
    echo "错误: 当前未激活任何conda环境，请先 conda activate 你的环境"
    exit 1
fi

# 检查SDK是否已安装
if [[ ! -d "/usr/local/pcammls" ]]; then
    echo "错误: 未找到Percipio SDK，请先运行 install_sdk.sh"
    exit 1
fi

# 安装Python依赖
echo "安装Python依赖..."
pip install "numpy<2" opencv-python matplotlib

# 配置环境变量
echo "配置环境变量到当前环境: $CONDA_PREFIX"
ACTIVATE_SCRIPT="$CONDA_PREFIX/etc/conda/activate.d/percipio_sdk.sh"
mkdir -p "$(dirname "$ACTIVATE_SCRIPT")"

cat > "$ACTIVATE_SCRIPT" << 'SCRIPT_EOF'
#!/bin/bash
export PYTHONPATH="/usr/local/pcammls/PYTHON:$PYTHONPATH"
export LD_LIBRARY_PATH="/usr/local/pcammls/lib64:$LD_LIBRARY_PATH"
echo "Percipio SDK 环境变量已激活"
SCRIPT_EOF

chmod +x "$ACTIVATE_SCRIPT"

# 立即生效
source "$ACTIVATE_SCRIPT"

# 测试SDK
echo "测试SDK..."
python -c "import pcammls; print('pcammls导入成功！')"

echo ""
echo "==== 配置完成！====="
echo "下次激活该环境时会自动配置Percipio SDK环境变量。"
 