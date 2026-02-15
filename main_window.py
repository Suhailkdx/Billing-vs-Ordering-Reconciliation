from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QTableView, QToolBar
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView
import os
from PySide6.QtGui import QTextDocument, QDesktopServices
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtGui import QPageSize
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QMessageBox

import pandas as pd

from data_processing import process_data


# ---------------- TABLE MODEL ---------------- #

class PandasTableModel(QStandardItemModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()

        self.setColumnCount(len(df.columns))
        self.setHorizontalHeaderLabels(df.columns.tolist())

        for row in df.itertuples(index=False):
            items = []
            for col_index, value in enumerate(row):
                item = QStandardItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)

                # Color ONLY status column
                if df.columns[col_index] == "status":
                    if value == "FAILED":
                        item.setBackground(QColor("#feb2b2"))
                    elif value == "PASSED":
                        item.setBackground(QColor("#c6f6d5"))

                items.append(item)

            self.appendRow(items)


# ---------------- MAIN WINDOW ---------------- #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Billing vs Ordering Dashboard")
        self.resize(1200, 700)

        # ---- DATA ----
        self.billing_df = None
        self.orders_df = None
        self.master_df = None
        self.filtered_df = None

        # ---- CENTRAL WIDGET ----
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ---- BUTTONS ----
        self.load_billing_btn = QPushButton("Load Billing CSV")
        self.load_orders_btn = QPushButton("Load Orders CSV")

        self.load_billing_btn.clicked.connect(self.load_billing)
        self.load_orders_btn.clicked.connect(self.load_orders)

        main_layout.addWidget(self.load_billing_btn)
        main_layout.addWidget(self.load_orders_btn)

        # ---- FILTERS ----
        self.drug_filter = QComboBox()
        self.insurance_filter = QComboBox()
        self.bin_filter = QComboBox()

        self.drug_filter.currentIndexChanged.connect(self.apply_filters)
        self.insurance_filter.currentIndexChanged.connect(self.apply_filters)
        self.bin_filter.currentIndexChanged.connect(self.apply_filters)

        # ---- TOOLBAR ----
        filter_toolbar = QToolBar("Filters")
        filter_toolbar.setMovable(False)
        filter_toolbar.setFloatable(False)

        filter_toolbar.setStyleSheet("""
            QToolBar { spacing: 8px; padding: 6px; }
            QComboBox { min-width: 180px; padding: 4px; }
        """)

        filter_toolbar.addWidget(QLabel("Drug"))
        filter_toolbar.addWidget(self.drug_filter)
        filter_toolbar.addSeparator()

        filter_toolbar.addWidget(QLabel("Insurance"))
        filter_toolbar.addWidget(self.insurance_filter)
        filter_toolbar.addSeparator()

        filter_toolbar.addWidget(QLabel("BIN"))
        filter_toolbar.addWidget(self.bin_filter)

        self.addToolBar(filter_toolbar)

        export_pdf_btn = QPushButton("Export PDF")
        export_pdf_btn.clicked.connect(self.export_to_pdf)
        filter_toolbar.addSeparator()
        filter_toolbar.addWidget(export_pdf_btn)


        # ---- TABLE ----
        self.table = QTableView()
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)

        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(28)

        main_layout.addWidget(self.table)

    # ---------------- LOADERS ---------------- #

    def load_billing(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Billing CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self.billing_df = pd.read_csv(path)
            self.try_process()

    def load_orders(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Orders CSV", "", "CSV Files (*.csv)"
        )
        if path:
            self.orders_df = pd.read_csv(path)
            self.try_process()

    # ---------------- PROCESS ---------------- #

    def try_process(self):
        if self.billing_df is None or self.orders_df is None:
            return

        df = process_data(self.billing_df, self.orders_df)

        if df is None or df.empty:
            return

        self.master_df = df.copy()
        self.filtered_df = df.copy()

        self.update_filters()
        self.update_table(self.filtered_df)

    # ---------------- TABLE ---------------- #

    def update_table(self, df):
        if df is None or df.empty:
            self.table.setModel(None)
            return

        model = PandasTableModel(df)
        self.table.setModel(model)
        self.table.resizeColumnsToContents()

    # ---------------- FILTERS ---------------- #

    def update_filters(self):
        if self.master_df is None or self.master_df.empty:
            return

        self.drug_filter.blockSignals(True)
        self.insurance_filter.blockSignals(True)
        self.bin_filter.blockSignals(True)

        self.drug_filter.clear()
        self.insurance_filter.clear()
        self.bin_filter.clear()

        self.drug_filter.addItem("All")
        self.insurance_filter.addItem("All")
        self.bin_filter.addItem("All")

        for d in sorted(self.master_df["drug_name"].dropna().unique()):
            self.drug_filter.addItem(str(d))

        for i in sorted(self.master_df["insurance_name"].dropna().unique()):
            self.insurance_filter.addItem(str(i))

        for b in sorted(self.master_df["bin_number"].dropna().astype(str).unique()):
            self.bin_filter.addItem(b)

        self.drug_filter.blockSignals(False)
        self.insurance_filter.blockSignals(False)
        self.bin_filter.blockSignals(False)

    def apply_filters(self):
        if self.master_df is None or self.master_df.empty:
            return

        df = self.master_df

        drug = self.drug_filter.currentText()
        ins = self.insurance_filter.currentText()
        bin_ = self.bin_filter.currentText()

        if drug != "All":
            df = df[df["drug_name"] == drug]

        if ins != "All":
            df = df[df["insurance_name"] == ins]

        if bin_ != "All":
            df = df[df["bin_number"].astype(str) == bin_]

        self.filtered_df = df
        self.update_table(self.filtered_df)

    def export_to_pdf(self):
     if self.filtered_df is None or self.filtered_df.empty:
        return

     path, _ = QFileDialog.getSaveFileName(
        self,
        "Save PDF",
        "billing_vs_orders.pdf",
        "PDF Files (*.pdf)"
    )

     if not path:
        return

    # ✅ Ensure .pdf extension
     if not path.lower().endswith(".pdf"):
        path += ".pdf"

     df = self.filtered_df

    # ---------- Build HTML ----------
     html = """
    <html>
    <head>
    <style>
        body { font-family: Arial; font-size: 10pt; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #444; padding: 4px; text-align: center; }
        th { background-color: #f0f0f0; }
        .ok { background-color: #c6f6d5; }
        .short { background-color: #feb2b2; }
    </style>
    </head>
    <body>
    <h2>Billing vs Ordering Report</h2>
    <table>
        <tr>
    """

     for col in df.columns:
        html += f"<th>{col}</th>"
     html += "</tr>"

     for _, row in df.iterrows():
        html += "<tr>"
        for col in df.columns:
            val = row[col]
            cls = ""
            if col == "status":
                cls = "ok" if val == "OK" else "short" if val == "SHORT" else ""
            html += f'<td class="{cls}">{val}</td>'
        html += "</tr>"

     html += """
    </table>
    </body>
    </html>
    """

    # ---------- Print ----------
     doc = QTextDocument()
     doc.setHtml(html)

     printer = QPrinter(QPrinter.HighResolution)
     printer.setOutputFormat(QPrinter.PdfFormat)
     printer.setOutputFileName(path)
     printer.setPageSize(QPageSize(QPageSize.A4))

     doc.print_(printer)

    # ✅ Confirm file exists
     if not os.path.exists(path):
        QMessageBox.critical(self, "PDF Error", "PDF was not created.")
        return

    # ✅ Open PDF automatically
     QDesktopServices.openUrl(QUrl.fromLocalFile(path))


