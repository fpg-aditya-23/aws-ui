import boto3
import os
from datetime import datetime, timedelta

# 🔹 CONFIG
BUCKET_NAME = "ing-marriott-useast-prod"

# 🔥 BOTH PREFIXES (merge download)
PREFIXES = [
    "OPERA/raw_data/PLSRT/",
    "OPERA/raw_data/PLSRR/"
]

PROFILE = "fpg-proj-ing-prod1"


# 🔹 MAIN FUNCTION (UI CONNECTED)
def download_data(location, date_input, base_path, log_callback):

    try:
        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

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

        total_downloaded = 0

        log_callback("⬇ Starting OPERA PLSRT (Merged Data)")

        paginator = s3.get_paginator('list_objects_v2')

        # 🔥 LOOP BOTH PREFIXES
        for prefix in PREFIXES:

            log_callback(f"🔍 Processing prefix → {prefix}")

            for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
                for obj in page.get('Contents', []):

                    try:
                        file_time = obj['LastModified'].replace(tzinfo=None) + timedelta(hours=5, minutes=30)

                        if not (start_date <= file_time < end_date):
                            continue

                        key = obj['Key']
                        file_name = key.split("/")[-1]

                        local_path = os.path.join(download_dir, file_name)

                        # 🔥 avoid overwrite
                        base, ext = os.path.splitext(local_path)
                        counter = 1
                        while os.path.exists(local_path):
                            local_path = f"{base}_{counter}{ext}"
                            counter += 1

                        s3.download_file(BUCKET_NAME, key, local_path)

                        total_downloaded += 1
                        log_callback(f"✅ {os.path.basename(local_path)}")

                    except Exception as e:
                        log_callback(f"❌ File Error → {e}")

        if total_downloaded == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Downloaded {total_downloaded} files")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")