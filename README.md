# CS2 行情悬浮窗

基于 [SteamDT 开放平台 API](https://doc.steamdt.com/) 的桌面常驻悬浮行情工具，
显示 CS2 大盘指数 + 收藏饰品在悠悠有品（YOUPIN）的在售价 / 求购价，
红涨绿跌、3 分钟自动刷新、支持中英文联想搜索。

[![Release](https://img.shields.io/github/v/release/zhongshi2x8/dust2-hangqing?label=download&color=brightgreen)](https://github.com/zhongshi2x8/dust2-hangqing/releases/latest)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

---

## 📥 下载（双击即用，无需装 Python）

> 最新版本：[**v1.3.0**](https://github.com/zhongshi2x8/dust2-hangqing/releases/tag/v1.3.0) — 持仓盈亏（成本价 + 红涨绿跌盈亏徽章）

| 平台 | 文件 | 大小 | 直链 |
| --- | --- | --- | --- |
| 🍎 **macOS (Apple Silicon)** | `CS2-Quote-macOS-arm64.zip` | 28 MB | [⬇️ 下载 v1.3.0](https://github.com/zhongshi2x8/dust2-hangqing/releases/download/v1.3.0/CS2-Quote-macOS-arm64.zip) |
| 🪟 **Windows** | `CS2-Quote-Windows.exe` | 38 MB | [⬇️ 下载 v1.3.0](https://github.com/zhongshi2x8/dust2-hangqing/releases/download/v1.3.0/CS2-Quote-Windows.exe) |

> Intel Mac 用户请[自行从源码构建](#-从源码构建)。
> 全部历史版本见 [Releases 页面](https://github.com/zhongshi2x8/dust2-hangqing/releases)。

---

## 🚀 安装运行

### macOS

1. 下载上面的 `CS2-Quote-macOS-arm64.zip` 并解压
2. **首次打开**：右键 `CS2行情.app` → **打开**（绕过未签名校验，只需一次，之后双击即可）
3. 弹窗输入 SteamDT 的 **API_KEY**（去 [steamdt.com](https://steamdt.com/) 个人中心 → API 管理免费申请）

### Windows

1. 下载上面的 `CS2-Quote-Windows.exe`
2. 双击运行（如被 Defender / 杀软误报，加白名单即可，PyInstaller 单文件的通病）
3. 弹窗输入 SteamDT API_KEY

---

## ⌨️ 操作

- **拖动**：鼠标按住悬浮窗任意位置即可拖到桌面任意位置（关闭时自动记忆位置）
- **手动刷新**：标题栏 `⟳` 按钮
- **缩放**：`Cmd +` 放大 / `Cmd -` 缩小 / `Cmd 0` 重置（Windows 上是 Ctrl）
- **右键菜单**：
  - 添加饰品：联想搜索，输入中英文关键词（空格分隔多词），例如 `AK 红线` / `AK Redline FT`
  - 持仓数量：设置该饰品的持有量，参与持仓总价计算
  - 删除：右键单击某一行饰品时菜单中会出现"删除：xxx"
  - 显示求购价：开关。关掉后只看在售价，价格旁边内联显示涨跌幅，窗口更紧凑
  - 透明度：5 档预设（40% – 100%）
  - 刷新间隔：1 / 3 / 5 / 10 / 30 分钟（SteamDT API 限制 ≥ 60 秒）
  - 窗口缩放：放大 / 缩小 / 重置
  - 立即刷新 / 退出

---

## ✨ 功能亮点

- **大盘指数**：顶部展示 CS2 broad market index + 较昨日涨跌（▲ / ▼）
- **持仓追踪 + 盈亏**：每件饰品可设置持有数量 + 成本单价，顶栏实时显示持仓总价 + 红涨绿跌的盈亏徽章
- **YOUPIN 实时价格**：每个收藏饰品的在售价 + 求购价（求购列可一键隐藏，隐藏后涨跌幅内联到价格旁）
- **红涨绿跌**：按国内行情习惯着色，价格下方/旁边一行带 ▲▼ 符号显示绝对涨幅 + 百分比
- **联想搜索**：内置 **39,166 件**饰品字典，支持中英文模糊匹配，无需联网查字典
- **可调刷新间隔**：1 / 3 / 5 / 10 / 30 分钟（受 SteamDT 限制 ≥ 60 秒）+ 手动刷新按钮
- **可调透明度**：5 档预设让悬浮窗不挡视线
- **窗口缩放**：右键菜单或 `Cmd ±` / `Cmd 0` 调整 80%~160%
- **常驻桌面**：无边框、置顶、深色风格，切换 App 时不会自动隐藏

---

## 🛠 从源码构建

> 提示：仓库已配置 [GitHub Actions](.github/workflows/release.yml)，推送 `v*` tag 会**自动**在云端构建 Mac + Windows 双平台二进制并附加到对应 Release，不需要本地手动构建。

### macOS

```bash
git clone https://github.com/zhongshi2x8/dust2-hangqing.git
cd dust2-hangqing
./build_macos.sh
# 产物：dist/CS2行情.app
```

### Windows

```cmd
git clone https://github.com/zhongshi2x8/dust2-hangqing.git
cd dust2-hangqing
build_windows.bat
REM 产物：dist\CS2行情.exe
```

### 直接源码运行（不打包）

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 📂 配置文件

`~/.steamdt/` 目录（Windows 是 `%USERPROFILE%\.steamdt\`）：

| 文件 | 内容 |
| --- | --- |
| `config.json` | API_KEY、窗口位置 |
| `watchlist.json` | 收藏饰品列表（可直接编辑迁移） |
| `base_cache.json` | 字典运行时缓存（已内置完整副本，可不存在） |

---

## 🧰 技术栈

- **UI**：[PyQt6](https://pypi.org/project/PyQt6/) 6.11
- **数据源**：[SteamDT 开放平台 REST API](https://doc.steamdt.com/)
- **打包**：[PyInstaller](https://pyinstaller.org/) 6.x（macOS `.app` bundle / Windows onefile `.exe`）

## ⚠️ 已知限制

- macOS 二进制为 Apple Silicon (arm64) 架构；Intel Mac 需自行 build
- `base_dict.json` 在 SteamDT 平台限制每天 1 次拉取，因此项目内打包了一份完整副本，运行时不再访问该接口
- 价格刷新固定 3 分钟一次（受 SteamDT `/price/batch` 每分钟 1 次的限制约束）

## License

MIT
