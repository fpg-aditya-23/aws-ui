import json
import os
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify

from HMS import aws_login
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

app = Flask(__name__, template_folder="templates", static_folder="static")
config_path = "config.json"

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
    "LANGHAM": ["TLSHX", "JEHA"],
    "HMS(INDEPENDENT)": ["TYSCMV", "SSIKP", "EAM"],
}

state = {
    "logs": [],
    "status_card": "🔴 AWS Not Connected",
    "status_label": "Idle",
    "total_tasks": 0,
    "completed_tasks": 0,
    "active_downloads": 0,
}
state_lock = threading.Lock()


def load_config():
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def save_config(config):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


config = load_config()


def append_log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    with state_lock:
        state["logs"].append(line)
        if len(state["logs"]) > 500:
            state["logs"] = state["logs"][-500:]


def update_status_label(text: str):
    with state_lock:
        state["status_label"] = text


def update_status_card(text: str):
    with state_lock:
        state["status_card"] = text


def run_download(location: str, date: str, base_path: str):
    data_found = True

    def logger(msg):
        if "No data found" in msg:
            nonlocal data_found
            data_found = False
        append_log(msg)

    try:
        if location == "VHNOLA":
            download_data_VHNOLA(location, date, base_path, logger)
        elif location == "EHK":
            download_data_EHK(location, date, base_path, logger)
        elif location in ["FDC", "PDC", "94964", "680269"]:
            download_data_Protel(location, date, base_path, logger)
        elif location == "6903":
            download_data_6903(location, date, base_path, logger)
        elif location in ["PLSRT", "LONHB", "JAXAM"]:
            download_data_OPERA(location, date, base_path, logger)
        elif location in ["RDHS", "LTHL", "WNBG", "WAVE2", "BGLOW", "ELCT", "FTLO"]:
            download_data_DAVIDSON(location, date, base_path, logger)
        elif location in ["ZEPH", "TPSM", "OERMKW"]:
            download_data(location, date, base_path, logger)
        elif location in ["TPAPK", "TPAMC", "BOSLW", "PHXBD", "DENMS", "BNAGO"]:
            download_data_TPAPK(location, date, base_path, logger)
        elif location in ["GF", "HHM", "REMINGTON"]:
            download_data_FOSSE(location, date, base_path, logger)
        elif location == "MARRIOTT":
            run_marriott(location, date, base_path, logger)
        elif location in ["OLBCLCI", "AMSCSDI", "PARPYPY", "BERWAWA", "OLBBRQQ", "VIEHIHI"]:
            download_onq(location, date, base_path, logger)
        elif location in ["KIPEK4", "KINKG1", "KISHA5", "NUPEK6", "KITNA1"]:
            download_data_KEMPINSKI(location, date, base_path, logger)
        elif location == "PUXUAN":
            download_data_URC(location, date, base_path, logger)
        elif location == "PHXLC":
            download_data_LIGHTSPEED(location, date, base_path, logger)
        elif location in ["TLSHX"]:
            download_data_LANGHAM(location, date, base_path, logger)
        elif location == "JEHA":
            download_data_JEHA(date, base_path, logger)
        elif location in ["TYSCMV", "SSIKP", "EAM"]:
            download_data_HMS_INDEPENDENT(location, date, base_path, logger)
        else:
            download_data(location, date, base_path, logger)
    except Exception as e:
        append_log(f"❌ Error → {e}")
        data_found = False

    result_message = f"✅ {location} Downloaded" if data_found else f"❌ {location} No Data"
    append_log(result_message)

    with state_lock:
        state["completed_tasks"] += 1
        state["active_downloads"] -= 1
        if state["active_downloads"] == 0:
            state["status_label"] = f"🎉 All Downloads Completed ({state['completed_tasks']}/{state['total_tasks']})"
        else:
            state["status_label"] = f"⏳ Downloading {location} ({state['completed_tasks']}/{state['total_tasks']})"


def start_downloads(locations, date):
    if not locations:
        append_log("⚠ No location selected")
        return False

    missing_paths = [loc for loc in locations if not config.get(loc)]
    if missing_paths:
        for loc in missing_paths:
            append_log(f"⚠ Select path for {loc}")
        return False

    with state_lock:
        state["total_tasks"] += len(locations)
        state["active_downloads"] += len(locations)
        state["status_label"] = f"⏳ Starting {len(locations)} download(s)"

    for location in locations:
        base_path = config[location]
        append_log(f"⬇ Starting {location}")
        thread = threading.Thread(target=run_download, args=(location, date, base_path), daemon=True)
        thread.start()

    return True


@app.route("/")
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "index.html",
        pms_locations=PMS_LOCATIONS,
        config=config,
        state=state,
        today=today,
    )


@app.route("/api/login", methods=["POST"])
def login():
    success, msg = aws_login(append_log)
    update_status_card("🟢 AWS Connected" if success else "🔴 AWS Error")
    return jsonify({"success": success, "message": msg, "status_card": state["status_card"]})


@app.route("/api/save-path", methods=["POST"])
def save_path():
    payload = request.json or {}
    location = payload.get("location")
    path = payload.get("path", "").strip()

    if not location or not path:
        return jsonify({"success": False, "message": "Location and path are required."}), 400

    config[location] = path
    save_config(config)
    append_log(f"📁 {location} Path: {path}")
    return jsonify({"success": True, "message": "Path saved."})


@app.route("/api/download", methods=["POST"])
def download():
    payload = request.json or {}
    locations = payload.get("locations", [])
    date = payload.get("date")

    if not date:
        return jsonify({"success": False, "message": "Date is required."}), 400

    if isinstance(locations, str):
        locations = [locations]

    if not locations:
        return jsonify({"success": False, "message": "No locations selected."}), 400

    result = start_downloads(locations, date)
    return jsonify({"success": result, "message": "Download started." if result else "Download failed."})


@app.route("/api/logs", methods=["GET"])
def logs():
    with state_lock:
        return jsonify({"logs": state["logs"], "status_label": state["status_label"], "status_card": state["status_card"], "total_tasks": state["total_tasks"], "completed_tasks": state["completed_tasks"], "active_downloads": state["active_downloads"]})


@app.route("/api/status", methods=["GET"])
def status():
    with state_lock:
        return jsonify({
            "status_card": state["status_card"],
            "status_label": state["status_label"],
            "total_tasks": state["total_tasks"],
            "completed_tasks": state["completed_tasks"],
            "active_downloads": state["active_downloads"],
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
