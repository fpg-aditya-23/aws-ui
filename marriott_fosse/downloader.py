import boto3
import os
from datetime import datetime, timedelta
import zipfile

def download_data(location, date_input, base_path, logger):

    BUCKET_NAME = "ing-marriott"
    PREFIX = "PROD-FOSSE/ses/"
    SSO_PROFILE = "fpg-proj-padraig"

    TRACK_FILE = os.path.join(base_path, "marriott_track.txt")

    session = boto3.Session(profile_name=SSO_PROFILE)
    s3 = session.client('s3')

    target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

    # =========================
    # FOLDERS
    # =========================
    SES_DIR = os.path.join(base_path, "SES", date_input)
    ZIP_DIR = os.path.join(base_path, "ZIP")

    os.makedirs(SES_DIR, exist_ok=True)
    os.makedirs(ZIP_DIR, exist_ok=True)

    logger(f"📂 SES: {SES_DIR}")
    logger(f"📦 ZIP: {ZIP_DIR}")

    downloaded_set = set()
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "r") as f:
            downloaded_set = set(f.read().splitlines())

    new_files = []

    paginator = s3.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
        for obj in page.get('Contents', []):

            file_time = obj['LastModified'] + timedelta(hours=5, minutes=30)

            if file_time.date() != target_date:
                continue

            key = obj['Key']

            if key in downloaded_set:
                continue

            file_name = key.split("/")[-1]
            local_path = os.path.join(SES_DIR, file_name)

            try:
                # =========================
                # DOWNLOAD FILE
                # =========================
                s3.download_file(BUCKET_NAME, key, local_path)

                # convert to .eml
                eml_path = os.path.splitext(local_path)[0] + ".eml"
                os.rename(local_path, eml_path)

                new_files.append(eml_path)

                # track file
                with open(TRACK_FILE, "a") as f:
                    f.write(key + "\n")

                logger(f"✅ Downloaded: {os.path.basename(eml_path)}")

            except Exception as e:
                logger(f"❌ Error: {e}")

    # =========================
    # ZIP INPUT FILES (UNCHANGED)
    # =========================
    if new_files:
        zip_path = os.path.join(ZIP_DIR, f"{date_input}.zip")

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in new_files:
                zipf.write(f, os.path.basename(f))

        logger(f"📦 ZIP Created: {zip_path}")
        return zip_path

    logger("⚠ No files found")
    return None