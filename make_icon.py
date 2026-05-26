"""生成 dust2 应用图标。

输出：
- assets/icon.png         (1024x1024 主图)
- assets/icon.icns        (macOS .app)
- assets/icon.ico         (Windows .exe)

依赖：PyQt6 (画图) + Pillow (打包 .ico) + iconutil (macOS 内置，打包 .icns)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)


# dust2 风格配色：沙漠主题
BG_TOP = "#c08555"        # 沙土亮
BG_BOTTOM = "#5b3a1f"     # 沙土暗
ACCENT = "#ffd166"        # 黄色高亮（仿炸弹计时器灯）
TEXT_COLOR = "#fff8e7"    # 暖白


def make_pixmap(size: int) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    radius = int(size * 0.22)

    # 圆角背景渐变
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor(BG_TOP))
    grad.setColorAt(1.0, QColor(BG_BOTTOM))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size, size, radius, radius)

    # 内描边（细微立体感）
    pen_w = max(1, int(size * 0.012))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 35), pen_w))
    inset = pen_w
    p.drawRoundedRect(
        inset,
        inset,
        size - 2 * inset,
        size - 2 * inset,
        max(0, radius - inset),
        max(0, radius - inset),
    )

    # 右上小红/黄点（点缀 / 炸点灯）
    dot_r = int(size * 0.07)
    dot_cx = int(size * 0.78)
    dot_cy = int(size * 0.22)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(ACCENT))
    p.drawEllipse(dot_cx - dot_r, dot_cy - dot_r, dot_r * 2, dot_r * 2)

    # 主文字 "dust2"
    text = "dust2"
    font = QFont("Helvetica")
    font.setPointSize(int(size * 0.30))
    font.setWeight(QFont.Weight.Black)
    font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 94)
    p.setFont(font)
    p.setPen(QColor(TEXT_COLOR))
    p.drawText(QRect(0, int(size * 0.05), size, size), Qt.AlignmentFlag.AlignCenter, text)

    p.end()
    return pix


def make_mac_icns(out_dir: Path) -> Path:
    iconset = out_dir / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)

    # macOS iconset 标准命名
    pairs = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    for size, name in pairs:
        make_pixmap(size).save(str(iconset / name), "PNG")

    icns_path = out_dir / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)],
        check=True,
    )
    return icns_path


def make_windows_ico(out_dir: Path) -> Path:
    from PIL import Image

    sizes = [16, 32, 48, 64, 128, 256]
    tmp_files: list[Path] = []
    for s in sizes:
        tmp = out_dir / f"_tmp_{s}.png"
        make_pixmap(s).save(str(tmp), "PNG")
        tmp_files.append(tmp)
    base = Image.open(str(tmp_files[-1]))  # 用最大的作为基础
    ico_path = out_dir / "icon.ico"
    base.save(str(ico_path), format="ICO", sizes=[(s, s) for s in sizes])
    for f in tmp_files:
        f.unlink()
    return ico_path


def main() -> int:
    # 必须先构造 QGuiApplication 再用 QPixmap，且要持有引用避免被 GC
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    _ = app  # keep alive

    out_dir = Path(__file__).parent / "assets"
    out_dir.mkdir(exist_ok=True)

    # 主 PNG（运行时 setWindowIcon 用）
    master = make_pixmap(1024)
    master.save(str(out_dir / "icon.png"), "PNG")

    icns = make_mac_icns(out_dir)
    ico = make_windows_ico(out_dir)

    print(f"✓ {out_dir / 'icon.png'}")
    print(f"✓ {icns}")
    print(f"✓ {ico}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
