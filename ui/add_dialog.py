"""添加饰品对话框：支持联想搜索 + 直接粘贴 marketHashName。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class AddDialog(QDialog):
    item_chosen = pyqtSignal(str, str)  # marketHashName, displayName

    def __init__(self, base_dict: list[dict], parent=None, dict_error: str = ""):
        super().__init__(parent)
        self.setWindowTitle("添加饰品")
        self.setModal(True)
        self.resize(480, 460)

        self._base = base_dict or []
        self._dict_error = dict_error
        self._selected: tuple[str, str] | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        layout.addWidget(QLabel("搜索关键词（空格分隔多词）或直接粘贴英文 market hash name："))

        self.input = QLineEdit()
        self.input.setPlaceholderText("如：AK 红线 / Redline FT / AK-47 | Redline (Field-Tested)")
        layout.addWidget(self.input)

        self.list = QListWidget()
        layout.addWidget(self.list, stretch=1)

        # 选中条目的预览（实际要写入 watchlist 的值）
        preview = QHBoxLayout()
        preview.addWidget(QLabel("将添加："))
        self.preview_label = QLabel("—")
        self.preview_label.setStyleSheet("color: #2563eb;")
        self.preview_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        preview.addWidget(self.preview_label, stretch=1)
        layout.addLayout(preview)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.cancel_btn = QPushButton("取消")
        self.ok_btn = QPushButton("添加")
        self.ok_btn.setDefault(True)
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.ok_btn)
        layout.addLayout(btns)

        # 输入防抖
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._refresh_suggestions)

        self.input.textChanged.connect(lambda _t: (self._timer.start(), self._update_preview()))
        self.list.itemSelectionChanged.connect(self._on_select)
        self.list.itemDoubleClicked.connect(lambda _i: self._accept())
        self.ok_btn.clicked.connect(self._accept)
        self.cancel_btn.clicked.connect(self.reject)

        self._render_status()
        self._update_preview()

    # ----- 状态行 -----

    def _render_status(self) -> None:
        if self._dict_error:
            self.status.setText(
                f"⚠ 字典加载失败：{self._dict_error}\n"
                "可直接粘贴英文 market hash name（如 AK-47 | Redline (Field-Tested)）后点添加。"
            )
            self.status.setStyleSheet("color: #b91c1c;")
        elif not self._base:
            self.status.setText("字典为空。可直接粘贴英文 market hash name 后点添加。")
            self.status.setStyleSheet("color: #b45309;")
        else:
            self.status.setText(f"字典已加载 {len(self._base):,} 件饰品，输入关键词联想搜索。")
            self.status.setStyleSheet("color: #6b7280;")

    # ----- 联想搜索 -----

    def _refresh_suggestions(self) -> None:
        q = self.input.text().strip().lower()
        self.list.clear()
        if not q or not self._base:
            return

        keywords = [k for k in q.split() if k]
        results: list[tuple[int, str, str]] = []  # (score, mhn, name)
        for entry in self._base:
            name = (entry.get("name") or "")
            mhn = (entry.get("marketHashName") or "")
            hay = (name + " " + mhn).lower()
            if not all(k in hay for k in keywords):
                continue
            # 简单评分：完整子串匹配优先，名称更短优先
            score = 0
            if q in name.lower() or q in mhn.lower():
                score -= 1000
            score += len(name) + len(mhn)
            results.append((score, mhn, name))

        results.sort(key=lambda x: x[0])
        for _score, mhn, name in results[:50]:
            label = f"{name}\n  {mhn}" if name and name != mhn else mhn
            li = QListWidgetItem(label)
            li.setData(Qt.ItemDataRole.UserRole, (mhn, name or mhn))
            self.list.addItem(li)

    # ----- 选中态 / 预览 -----

    def _on_select(self) -> None:
        items = self.list.selectedItems()
        if items:
            self._selected = items[0].data(Qt.ItemDataRole.UserRole)
        else:
            self._selected = None
        self._update_preview()

    def _update_preview(self) -> None:
        target = self._effective_choice()
        if target is None:
            self.preview_label.setText("—")
            self.ok_btn.setEnabled(False)
            return
        mhn, name = target
        self.preview_label.setText(f"{name}  ·  {mhn}" if name != mhn else mhn)
        self.ok_btn.setEnabled(True)

    def _effective_choice(self) -> tuple[str, str] | None:
        # 优先用列表中选中的条目
        if self._selected:
            return self._selected
        # 否则用输入框里的文本作为 marketHashName（手动模式）
        raw = self.input.text().strip()
        if len(raw) >= 4 and not raw.isdigit():
            return (raw, raw)
        return None

    def _accept(self) -> None:
        target = self._effective_choice()
        if target is None:
            return
        self.item_chosen.emit(*target)
        self.accept()
