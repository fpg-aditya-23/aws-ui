import boto3
import os
from datetime import datetime, timedelta

# 🔹 CONFIG
BUCKET_NAME = "ing-marriott-useast-prod"
PROFILE = "fpg-proj-ing-prod1"

# 🔥 LOCATION PREFIX MAP
LOCATION_PREFIX = {
    "TPAPK": "FSPMS/raw_data/TPAPK/",
    "TPAMC": "FSPMS/raw_data/TPAMC/",
    "BOSLW": "FSPMS/raw_data/BOSLW/",
    "PHXBD": "FSPMS/raw_data/PHXBD/",
    "DENMS": "FSPMS/raw_data/DENMS/",

    # 🔥 NEW
    "BNAGO": "FSPMS/raw_data/BNAGO/",
    "DENMS": "FSPMS/raw_data/DENMS/"
}


def download_data(location, date_input, base_path, log_callback):

    try:
        if location not in LOCATION_PREFIX:
            log_callback(f"❌ Invalid location: {location}")
            return

        prefix = LOCATION_PREFIX[location]

        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        # =========================
        # 🔥 FINAL STRUCTURE
        # base_path / FSPMS / DATE / LOCATION
        # =========================

        pms_folder = os.path.join(base_path, "FSPMS")
        os.makedirs(pms_folder, exist_ok=True)

        date_folder = os.path.join(pms_folder, date_input)
        os.makedirs(date_folder, exist_ok=True)

        location_folder = os.path.join(date_folder, location)
        os.makedirs(location_folder, exist_ok=True)

        log_callback(f"📂 PMS Folder: {pms_folder}")
        log_callback(f"📅 Date Folder: {date_folder}")
        log_callback(f"📍 Location Folder: {location_folder}")

        downloaded_count = 0

        log_callback(f"⬇ Starting FSPMS {location}")

        paginator = s3.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            for obj in page.get('Contents', []):

                try:
                    # 🔥 IST FIX
                    file_time = obj['LastModified'].replace(tzinfo=None) + timedelta(hours=5, minutes=30)

                    if not (start_date <= file_time < end_date):
                        continue

                    key = obj['Key']
                    file_name = key.split("/")[-1]

                    local_path = os.path.join(location_folder, file_name)

                    # 🔥 prevent overwrite
                    base, ext = os.path.splitext(local_path)
                    counter = 1
                    while os.path.exists(local_path):
                        local_path = f"{base}_{counter}{ext}"
                        counter += 1

                    s3.download_file(BUCKET_NAME, key, local_path)

                    downloaded_count += 1
                    log_callback(f"✅ {location} → {os.path.basename(local_path)}")

                except Exception as e:
                    log_callback(f"❌ File Error → {e}")

        if downloaded_count == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Downloaded {downloaded_count} files")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")