import boto3
import os
from datetime import datetime, timedelta

# 🔹 CONFIG
BUCKET_NAME_MARRIOTT = "ing-marriott-useast-prod"
BUCKET_NAME_IHG = "ing-ihg-useast-prod"

PROFILE = "fpg-proj-ing-prod1"

# 🔥 LOCATION CONFIG
LOCATION_CONFIG = {
    "PLSRT": {
        "bucket": BUCKET_NAME_MARRIOTT,
        "prefixes": [
            "OPERA/raw_data/PLSRT/",
            "OPERA/raw_data/PLSRR/"
        ]
    },
    "LONHB": {
        "bucket": BUCKET_NAME_IHG,
        "prefixes": [
            "OPERA/raw_data/LONHB/"
        ]
    },
    "JAXAM": {
        "bucket": BUCKET_NAME_MARRIOTT,
        "prefixes": [
            "OPERA/raw_data/JAXAM/"
        ]
    }
}


# 🔹 MAIN FUNCTION
def download_data(location, date_input, base_path, log_callback):

    try:
        if location not in LOCATION_CONFIG:
            log_callback(f"❌ Invalid location: {location}")
            return

        config = LOCATION_CONFIG[location]
        bucket = config["bucket"]
        prefixes = config["prefixes"]

        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        # =========================
        # 🔥 FINAL STRUCTURE
        # base_path / OPERA / DATE / LOCATION
        # =========================
        pms_folder = os.path.join(base_path, "OPERA")
        os.makedirs(pms_folder, exist_ok=True)

        date_folder = os.path.join(pms_folder, date_input)
        os.makedirs(date_folder, exist_ok=True)

        location_folder = os.path.join(date_folder, location)
        os.makedirs(location_folder, exist_ok=True)

        log_callback(f"📂 PMS Folder: {pms_folder}")
        log_callback(f"📅 Date Folder: {date_folder}")
        log_callback(f"📍 Location Folder: {location_folder}")

        total_downloaded = 0

        log_callback(f"⬇ Starting OPERA {location}")

        paginator = s3.get_paginator('list_objects_v2')

        # 🔥 LOOP PREFIXES
        for prefix in prefixes:

            log_callback(f"🔍 Processing prefix → {prefix}")

            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):

                    try:
                        file_time = obj['LastModified'].replace(tzinfo=None) + timedelta(hours=5, minutes=30)

                        if not (start_date <= file_time < end_date):
                            continue

                        key = obj['Key']
                        file_name = key.split("/")[-1]

                        local_path = os.path.join(location_folder, file_name)

                        # 🔥 avoid overwrite
                        base, ext = os.path.splitext(local_path)
                        counter = 1
                        while os.path.exists(local_path):
                            local_path = f"{base}_{counter}{ext}"
                            counter += 1

                        s3.download_file(bucket, key, local_path)

                        total_downloaded += 1
                        log_callback(f"✅ {location} → {os.path.basename(local_path)}")

                    except Exception as e:
                        log_callback(f"❌ File Error → {e}")

        if total_downloaded == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Downloaded {total_downloaded} files")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")