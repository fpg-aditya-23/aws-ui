import sys
import json
import os

from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QDate, QTimer, QThread, Signal

# 🔹 EXISTING IMPORTS
from HMS import download_data, aws_login
from HMS_VHNOLA import download_data as download_data_VHNOLA
from HMS_EHK import download_data as download_data_EHK
from REZEN_6903 import download_data as download_data_6903
from STAYNTOUCH import download_data as download_data
from FSPMS_TPAPK import download_data as download_data_TPAPK
from marriott_fosse.runner import run_marriott
from ONQ import download_onq
from gf_hhm_remington import download_data as download_data_FOSSE
from OPERA import download_data as download_data_OPERA
from STAYNTOUCH_DAVIDSON import download_data as download_data_DAVIDSON
from KEMPINSKI import download_data as download_data_KEMPINSKI
from URC_SEP import download_data as download_data_URC
from LIGHTSPEED import download_data as download_data_LIGHTSPEED
from LANGHAM import download_data as download_data_LANGHAM
from HMS_INDEPENDENT import download_data as download_data_HMS_INDEPENDENT
from protel import download_data as download_data_Protel
from JEHA import download_data as download_data_JEHA

# 🔥 WORKER THREAD
class DownloadWorker(QThread):
    finished = Signal(str, bool)
    log_signal = Signal(str)

    def __init__(self, location, date, base_path):
        super().__init__()
        self.location = location
        self.date = date
        self.base_path = base_path
        self.data_found = True

    def run(self):
        try:
            def logger(msg):
                if "No data found" in msg:
                    self.data_found = False
                self.log_signal.emit(msg)

            if self.location == "VHNOLA":
                download_data_VHNOLA(self.location, self.date, self.base_path, logger)

            elif self.location == "EHK":
                download_data_EHK(self.location, self.date, self.base_path, logger)

            elif self.location in ["FDC", "PDC", "94964", "680269"]:
                download_data_Protel(self.location, self.date, self.base_path, logger)

            elif self.location == "6903":
                download_data_6903(self.location, self.date, self.base_path, logger)

            elif self.location in ["PLSRT", "LONHB", "JAXAM"]:
                download_data_OPERA(self.location, self.date, self.base_path, logger)

            elif self.location in ["RDHS", "LTHL", "WNBG", "WAVE2", "BGLOW", "ELCT", "FTLO"]:
                download_data_DAVIDSON(self.location, self.date, self.base_path, logger)

            elif self.location in ["ZEPH", "TPSM", "OERMKW"]:
                download_data(self.location, self.date, self.base_path, logger)

            elif self.location in ["TPAPK", "TPAMC", "BOSLW", "PHXBD", "DENMS","BNAGO"]:
                download_data_TPAPK(self.location, self.date, self.base_path, logger)

            elif self.location in ["GF", "HHM", "REMINGTON"]:
                download_data_FOSSE(self.location, self.date, self.base_path, logger)

            elif self.location == "MARRIOTT":
                run_marriott(self.location, self.date, self.base_path, logger)

            elif self.location in ["OLBCLCI", "AMSCSDI", "PARPYPY", "BERWAWA", "OLBBRQQ", "VIEHIHI"]:
                download_onq(self.location, self.date, self.base_path, logger)

            elif self.location in ["KIPEK4", "KINKG1", "KISHA5", "NUPEK6", "KITNA1"]:
                download_data_KEMPINSKI(self.location, self.date, self.base_path, logger)

            elif self.location == "PUXUAN":
                download_data_URC(self.location, self.date, self.base_path, logger)

            elif self.location == "PHXLC":
                download_data_LIGHTSPEED(self.location, self.date, self.base_path, logger)

            elif self.location in ["TLSHX"]:
                download_data_LANGHAM(self.location, self.date, self.base_path, logger)

            elif self.location == "JEHA":
                download_data_JEHA(self.date, self.base_path, logger)

            elif self.location in ["TYSCMV", "SSIKP", "EAM"]:
                download_data_HMS_INDEPENDENT(self.location, self.date, self.base_path, logger)

            else:
                download_data(self.location, self.date, self.base_path, logger)

        except Exception as e:
            self.log_signal.emit(f"❌ Error → {e}")
            self.data_found = False

        self.finished.emit(self.location, self.data_found)


class AWSDownloaderUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AWS Downloader")

        screen = QApplication.primaryScreen().availableGeometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.8)

        self.resize(width, height)
        self.move((screen.width() - width) // 2, (screen.height() - height) // 2)
        self.setMinimumSize(900, 500)

        self.config_path = "config.json"

        self.workers = []

        # ✅ NEW: counters
        self.total_tasks = 0
        self.completed_tasks = 0
        self.active_downloads = 0

        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {}

        main = QWidget()
        self.setCentralWidget(main)
        layout = QVBoxLayout(main)

        self.status_card = QLabel("🔴 AWS Not Connected")
        layout.addWidget(self.status_card)

        self.login_btn = QPushButton("Connect AWS")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        date_layout = QHBoxLayout()

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("yyyy-MM-dd")

        date_layout.addWidget(QLabel("Date:"))
        date_layout.addWidget(self.date_input)
        layout.addLayout(date_layout)

        body = QHBoxLayout()

        self.locations_layout = QVBoxLayout()
        self.location_rows = {}
        self.pms_checkboxes = {}

        PMS_LOCATIONS = {
            "HMS": ["PIER66", "BNAMVN", "VHNOLA", "EHK"],
            "Rezen": ["6903"],
            "PROTEL": ["FDC", "PDC", "94964", "680269"],
            "OPERA": ["PLSRT", "LONHB", "JAXAM"],
            "StayNTouch": ["ZEPH", "TPSM", "OERMKW"],
            "StayNTouch(DAVIDSON)": ["RDHS", "LTHL", "WNBG", "WAVE2", "BGLOW", "ELCT", "FTLO"],
            "FSPMS": ["TPAPK", "TPAMC", "BOSLW", "PHXBD", "DENMS", "BNAGO"],
            "FOSSE": ["GF", "HHM", "REMINGTON", "MARRIOTT"],
            "ONQ": ["OLBCLCI", "AMSCSDI", "PARPYPY", "BERWAWA", "OLBBRQQ", "VIEHIHI"],
            "KEMPINSKI(SEP)": ["KIPEK4", "KINKG1", "KISHA5", "NUPEK6", "KITNA1"],
            "URC(SEP)": ["PUXUAN"],
            "LIGHTSPEED": ["PHXLC"],
            "LANGHAM": ["TLSHX","JEHA"],
            "HMS(INDEPENDENT)": ["TYSCMV", "SSIKP", "EAM"],
        }

        for pms, locations in PMS_LOCATIONS.items():

            pms_checkbox = QCheckBox(pms)
            pms_checkbox.setStyleSheet("font-size:16px; font-weight:bold; color:#38bdf8;")
            self.pms_checkboxes[pms] = pms_checkbox
            self.locations_layout.addWidget(pms_checkbox)

            pms_checkbox.stateChanged.connect(
                lambda state, locs=locations: self.toggle_pms(state, locs)
            )

            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            self.locations_layout.addWidget(line)

            for loc in locations:
                row = QHBoxLayout()

                checkbox = QCheckBox()
                label = QLabel(f"   {loc}")

                download_btn = QPushButton("Download")
                path_btn = QPushButton()

                saved_path = self.config.get(loc, "")

                if saved_path:
                    path_btn.setText("Path Selected")
                    path_btn.setToolTip(saved_path)
                else:
                    path_btn.setText("Select Path")

                self.location_rows[loc] = {
                    "path": saved_path,
                    "checkbox": checkbox,
                    "path_btn": path_btn
                }

                download_btn.clicked.connect(lambda _, l=loc: self.download_single(l))
                path_btn.clicked.connect(lambda _, l=loc: self.select_path_for_location(l))

                row.addWidget(checkbox)
                row.addWidget(label)
                row.addStretch()
                row.addWidget(download_btn)
                row.addWidget(path_btn)

                self.locations_layout.addLayout(row)

        scroll_widget = QWidget()
        scroll_widget.setLayout(self.locations_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_widget)

        left = QVBoxLayout()
        left.addWidget(QLabel("Locations"))
        left.addWidget(scroll)

        self.bulk_btn = QPushButton("Download Selected")
        self.bulk_btn.clicked.connect(self.download_selected)
        left.addWidget(self.bulk_btn)

        self.status_label = QLabel("Idle")
        self.status_label.setAlignment(Qt.AlignCenter)

        right = QVBoxLayout()
        right.addWidget(self.status_label)

        body.addLayout(left, 60)
        body.addLayout(right, 40)

        layout.addLayout(body)

        self.logs = QTextEdit()
        self.logs.setMaximumHeight(150)
        self.logs.setReadOnly(True)
        layout.addWidget(self.logs)

    def log(self, msg):
        self.logs.append(msg)

    def handle_login(self):
        success, msg = aws_login()
        self.log(msg)

        if success:
            self.status_card.setText("🟢 AWS Connected")
        else:
            self.status_card.setText("🔴 AWS Error")

    def toggle_pms(self, state, locations):
        for loc in locations:
            self.location_rows[loc]["checkbox"].setChecked(state)

    def select_path_for_location(self, location):
        folder = QFileDialog.getExistingDirectory(self, f"Select Folder for {location}")

        if folder:
            self.location_rows[location]["path"] = folder
            self.config[location] = folder

            btn = self.location_rows[location]["path_btn"]
            btn.setText("Path Selected")
            btn.setToolTip(folder)

            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)

            self.log(f"📁 {location} Path: {folder}")

    def download_single(self, location):
        self.total_tasks = 1
        self.completed_tasks = 0
        self.active_downloads = 1
        self.start_download(location)

    def download_selected(self):
        selected = [
            loc for loc, data in self.location_rows.items()
            if data["checkbox"].isChecked()
        ]

        if not selected:
            self.log("⚠ No location selected")
            return

        self.total_tasks = len(selected)
        self.completed_tasks = 0
        self.active_downloads = len(selected)

        for loc in selected:
            self.start_download(loc)

    def start_download(self, location):
        date = self.date_input.date().toString("yyyy-MM-dd")
        base_path = self.location_rows[location]["path"]

        if not base_path:
            self.log(f"⚠ Select path for {location}")
            return

        self.log(f"⬇ Starting {location}")

        self.status_label.setText(
            f"⏳ Downloading {location} ({self.completed_tasks+1}/{self.total_tasks})"
        )

        worker = DownloadWorker(location, date, base_path)
        worker.log_signal.connect(self.log)
        worker.finished.connect(self.handle_finished)

        worker.start()
        self.workers.append(worker)

    def handle_finished(self, location, data_found):
        self.completed_tasks += 1
        self.active_downloads -= 1

        if not data_found:
            msg = f"❌ {location} No Data"
        else:
            msg = f"✅ {location} Downloaded"

        self.log(msg)

        self.status_label.setText(
            f"{msg} ({self.completed_tasks}/{self.total_tasks})"
        )

        if self.active_downloads == 0:
            self.status_label.setText(
                f"🎉 All Downloads Completed ({self.completed_tasks}/{self.total_tasks})"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AWSDownloaderUI()
    window.show()
    sys.exit(app.exec())