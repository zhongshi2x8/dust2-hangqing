"""持仓信息对话框：同时设置持有数量 + 成本单价。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)


class HoldingDialog(QDialog):
    submitted = pyqtSignal(int, float)  # quantity, cost_price

    def __init__(
        self,
        item_label: str,
        current_qty: int = 0,
        current_cost: float = 0.0,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("持仓信息")
        self.setModal(True)
        self.resize(380, 200)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        name_label = QLabel(item_label)
        name_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(0, 99999)
        self.qty_spin.setValue(max(0, int(current_qty)))
        self.qty_spin.setSuffix(" 件")
        form.addRow("持有数量：", self.qty_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0.0, 9_999_999.99)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setSingleStep(1.0)
        self.cost_spin.setValue(max(0.0, float(current_cost)))
        self.cost_spin.setPrefix("¥ ")
        form.addRow("成本单价：", self.cost_spin)

        layout.addLayout(form)

        hint = QLabel(
            "数量 0 = 仅关注，不计入持仓总价。\n"
            "成本 0 = 未设置，不参与盈亏计算（但仍计入持仓总价）。"
        )
        hint.setStyleSheet("color: #6b7280; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 让"持有数量"输入框默认聚焦
        self.qty_spin.setFocus()
        self.qty_spin.selectAll()

    def _on_ok(self) -> None:
        self.submitted.emit(int(self.qty_spin.value()), float(self.cost_spin.value()))
        self.accept()
