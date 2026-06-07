import boto3
import os
from datetime import datetime, timedelta

# 🔹 CONFIG
BUCKET_NAME = "ing-ihg-useast-prod"
PREFIX = "OPERA/raw_data/LONHB/"
PROFILE = "fpg-proj-ing-prod1"


# 🔹 MAIN FUNCTION (UI FORMAT)
def download_data(location, date_input, base_path, log_callback):

    try:
        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

        # =========================
        # 🔥 NEW STRUCTURE
        # base_path / LOCATION / DATE
        # =========================
        location_folder = os.path.join(base_path, location)
        os.makedirs(location_folder, exist_ok=True)

        download_dir = os.path.join(location_folder, date_input)
        os.makedirs(download_dir, exist_ok=True)

        log_callback(f"📂 Location Folder: {location_folder}")
        log_callback(f"📅 Date Folder: {download_dir}")

        download_count = 0

        log_callback(f"⬇ Starting OPERA {location}")

        paginator = s3.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
            for obj in page.get('Contents', []):

                try:
                    # 🔥 IST FIX
                    file_date = (obj['LastModified'] + timedelta(hours=5, minutes=30)).date()

                    if file_date != target_date:
                        continue

                    key = obj['Key']
                    file_name = key.split("/")[-1]

                    local_path = os.path.join(download_dir, file_name)

                    # 🔥 Prevent overwrite
                    base, ext = os.path.splitext(local_path)
                    counter = 1
                    while os.path.exists(local_path):
                        local_path = f"{base}_{counter}{ext}"
                        counter += 1

                    s3.download_file(BUCKET_NAME, key, local_path)

                    download_count += 1
                    log_callback(f"✅ {os.path.basename(local_path)}")

                except Exception as e:
                    log_callback(f"❌ File Error → {e}")

        if download_count == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Downloaded {download_count} files")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")