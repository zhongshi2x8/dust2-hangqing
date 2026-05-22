#!/usr/bin/env bash
# 在 macOS 上构建 CS2行情.app
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[1/3] 创建虚拟环境"
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[2/3] 安装依赖（含 PyInstaller）"
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple "pyinstaller>=6.0"

echo "[3/3] 开始打包"
rm -rf build dist
pyinstaller --noconfirm cs2_quote.spec

echo ""
echo "✅ 完成：dist/CS2行情.app"
echo "   双击即可运行。如要分发，可以右键 → 压缩，或者用 hdiutil create 打 dmg。"
