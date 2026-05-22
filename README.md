# CS2 行情悬浮窗

基于 [SteamDT 开放平台 API](https://doc.steamdt.com/) 的 macOS 桌面常驻悬浮行情工具。
显示 CS2 大盘指数以及收藏饰品在悠悠有品（YOUPIN）的在售价 / 求购价，3 分钟自动刷新。

## 启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

首次启动会弹窗要求输入 SteamDT 的 API_KEY，之后保存在 `~/.steamdt/config.json`。

## 操作

- 鼠标按住悬浮窗任意位置即可拖动
- 右键菜单：
  - 添加饰品：弹出搜索框，输入 ≥ 2 个字符进行模糊匹配，选择确认
  - 删除：右键单击某一行饰品时菜单中会出现"删除：xxx"
  - 立即刷新：强制拉取最新价格
  - 退出：关闭程序

## 配置文件

`~/.steamdt/` 目录：

- `config.json`：API_KEY、窗口位置
- `watchlist.json`：收藏饰品列表
- `base_cache.json`：饰品字典缓存（每日刷新）
