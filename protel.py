import boto3
import os
import re
from datetime import datetime
from email import policy
import email
from concurrent.futures import ThreadPoolExecutor

# 🔹 AWS PROFILE
PROFILE = "fpg-cust-independent"

# 🔹 BASE FOLDER NAME
BASE_FOLDER_NAME = "PROTEL"

# 🔹 CONFIG (ALL LOCATIONS)
CONFIGS = {
    "FDC": {
        "bucket": "ing-independent-fleur-de-chine-hotel-fdc-apeast1",
        "prefix": "SFTP/",
        "full_name": "FLEUR DE CHINE HOTEL"
    },
    "PDC": {
        "bucket": "ing-palais-de-chine-hotel-apeast1",
        "prefix": "SFTP/",
        "full_name": "PALAIS DE CHINE HOTEL"
    },
    "94964": {
        "bucket": "ing-independent-palazzo-venart-94964-eusouth1",
        "prefix": "SFTP/",
        "full_name": "PALAZZO VENART"
    },
    "680269": {
        "bucket": "ing-independent-aromalifestylehotel-680269-eusouth1",
        "prefix": "SFTP/",
        "full_name": "AROMA LIFESTYLE HOTEL"
    }
}

# 🔥 NORMALIZER
def normalize(text):
    return re.sub(r'[^A-Z0-9 ]', ' ', text.upper())


# 🔹 MAIN FUNCTION
def download_data(location_key, date_input, base_path, log_callback):

    try:
        if location_key not in CONFIGS:
            log_callback("❌ Invalid Location")
            return

        cfg = CONFIGS[location_key]

        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client("s3")

        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

        # 🔥 FINAL STRUCTURE: PROTEL > DATE > LOCATION
        date_folder = os.path.join(base_path, BASE_FOLDER_NAME, date_input)
        location_folder = os.path.join(date_folder, location_key)

        os.makedirs(location_folder, exist_ok=True)

        paginator = s3.get_paginator("list_objects_v2")

        objects = []
        for page in paginator.paginate(Bucket=cfg["bucket"], Prefix=cfg["prefix"]):
            objects.extend(page.get("Contents", []))

        downloaded = 0

        def process(obj):

            nonlocal downloaded

            try:
                key = obj["Key"]
                file_name = key.split("/")[-1]

                # 🔹 DATE FILTER
                if obj["LastModified"].date() != target_date:
                    return

                raw = s3.get_object(Bucket=cfg["bucket"], Key=key)["Body"].read()
                msg = email.message_from_bytes(raw, policy=policy.default)

                subject = (msg.get("subject") or "").upper()

                subject_words = set(normalize(subject).split())
                name_words = set(normalize(cfg["full_name"]).split())

                # 🔹 MATCH LOGIC
                if len(subject_words.intersection(name_words)) < 2:
                    return

                # 🔹 SAVE EMAIL
                eml_path = os.path.join(location_folder, file_name + ".eml")

                with open(eml_path, "wb") as f:
                    f.write(raw)

                log_callback(f"[{location_key}] Email → {eml_path}")

                # 🔹 SAVE ATTACHMENTS
                for part in msg.walk():

                    if part.get_filename():
                        att_name = part.get_filename()
                        att_path = os.path.join(location_folder, att_name)

                        with open(att_path, "wb") as f:
                            f.write(part.get_payload(decode=True))

                        log_callback(f"[{location_key}] Attachment → {att_path}")

                downloaded += 1

            except Exception as e:
                log_callback(f"⚠ Error [{location_key}] → {e}")

        with ThreadPoolExecutor(max_workers=10) as ex:
            ex.map(process, objects)

        log_callback(f"✅ DONE [{location_key}] | Downloaded: {downloaded}")

    except Exception as e:
        log_callback(f"❌ AWS ERROR → {e}")