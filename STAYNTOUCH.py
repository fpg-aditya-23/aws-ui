import boto3
import os
import re
from datetime import datetime
from email import policy
import email
from concurrent.futures import ThreadPoolExecutor

# 🔹 CONFIG (ONLY OLD BUCKETS)
CONFIGS = [
    {
        "bucket": "ing-pebblebrook-hotel",
        "prefix": "PROD-StayNTouch/ses/",
        "profile": "fpg-proj-padraig",
        "locations": {
            "ZEPH": "HOTEL ZEPHYR SAN FRANCISCO"
        }
    },
    {
        "bucket": "ing-independent",
        "prefix": "PROD-STAYNTOUCH/ses/",
        "profile": "fpg-proj-padraig",
        "locations": {
            "TPSM": "THE PIERSIDE SANTA MONICA",
            "OERMKW": "OCEANS EDGE RESORT AND MARINA KEY WEST"
        }
    }
]


# 🔹 NORMALIZE
def normalize(text):
    return re.sub(r'[^A-Z0-9 ]', ' ', text.upper())


# 🔹 MAIN FUNCTION
def download_data(location, date_input, base_path, log_callback):

    try:
        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

        # =========================
        # 🔥 FOLDER STRUCTURE
        # base / STAYNTOUCH / DATE / LOCATION
        # =========================
        pms_folder = os.path.join(base_path, "STAYNTOUCH")
        os.makedirs(pms_folder, exist_ok=True)

        date_folder = os.path.join(pms_folder, date_input)
        os.makedirs(date_folder, exist_ok=True)

        location_folder = os.path.join(date_folder, location)
        os.makedirs(location_folder, exist_ok=True)

        log_callback(f"📂 PMS Folder: {pms_folder}")
        log_callback(f"📅 Date Folder: {date_folder}")
        log_callback(f"📍 Location Folder: {location_folder}")
        log_callback(f"⬇ Starting → {location}")

        downloaded = 0

        for config in CONFIGS:

            session = boto3.Session(profile_name=config["profile"])
            s3 = session.client('s3')

            paginator = s3.get_paginator('list_objects_v2')

            all_objects = []
            for page in paginator.paginate(Bucket=config["bucket"], Prefix=config["prefix"]):
                all_objects.extend(page.get('Contents', []))

            def process(obj):
                nonlocal downloaded

                try:
                    if obj['LastModified'].date() != target_date:
                        return

                    key = obj['Key']
                    file_name = key.split("/")[-1]

                    raw = s3.get_object(Bucket=config["bucket"], Key=key)['Body'].read()
                    msg = email.message_from_bytes(raw, policy=policy.default)

                    subject = normalize(msg.get("subject") or "")
                    subject_words = set(subject.split())

                    matched = None

                    for loc_id, full_name in config["locations"].items():
                        name_words = set(normalize(full_name).split())

                        if loc_id in subject_words or len(name_words.intersection(subject_words)) >= 2:
                            matched = loc_id
                            break

                    # 🔥 ONLY SELECTED LOCATION
                    if matched != location:
                        return

                    # 🔥 SAVE EML
                    eml_path = os.path.join(location_folder, file_name + ".eml")

                    base, ext = os.path.splitext(eml_path)
                    counter = 1
                    while os.path.exists(eml_path):
                        eml_path = f"{base}_{counter}{ext}"
                        counter += 1

                    with open(eml_path, "wb") as f:
                        f.write(raw)

                    log_callback(f"✅ {matched} → {os.path.basename(eml_path)}")

                    # 🔹 ATTACHMENTS
                    for part in msg.iter_attachments():
                        filename = part.get_filename()
                        if filename:
                            file_path = os.path.join(location_folder, filename)

                            base, ext = os.path.splitext(file_path)
                            counter = 1
                            while os.path.exists(file_path):
                                file_path = f"{base}_{counter}{ext}"
                                counter += 1

                            with open(file_path, "wb") as f:
                                f.write(part.get_payload(decode=True))

                    downloaded += 1

                except Exception as e:
                    log_callback(f"❌ Error → {e}")

            # 🔥 MULTITHREAD
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(process, all_objects)

        if downloaded == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Downloaded {downloaded} files")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")