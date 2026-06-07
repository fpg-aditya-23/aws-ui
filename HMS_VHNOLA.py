import boto3
import os
import re
from datetime import datetime
from email import policy
import email
from concurrent.futures import ThreadPoolExecutor

# 🔹 CONFIG
BUCKET_NAME = "ing-virgin-hotels-useast-prod"
PREFIX = "INFORHMS/SES/"
PROFILE = "fpg-proj-ing-prod1"

LOCATION_NAME = "VHNOLA"
FULL_NAME = "VIRGIN HOTELS NEW ORLEANS"


# 🔥 NORMALIZER
def normalize(text):
    return re.sub(r'[^A-Z0-9 ]', ' ', text.upper())


# 🔹 MAIN FUNCTION (UI CALL)
def download_data(selected_location, date_input, base_path, log_callback):

    try:
        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

        log_callback(f"⬇ Starting {selected_location}")

        # 🔹 PATH
        date_folder = os.path.join(base_path, selected_location, date_input)
        os.makedirs(date_folder, exist_ok=True)

        # 🔹 EXISTING FILES
        existing_files = set()
        for root, dirs, files in os.walk(date_folder):
            for f in files:
                existing_files.add(f)

        paginator = s3.get_paginator('list_objects_v2')

        all_objects = []
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
            all_objects.extend(page.get('Contents', []))

        downloaded = 0
        skipped = 0

        # 🔹 PROCESS FUNCTION
        def process_object(obj):
            nonlocal downloaded, skipped

            try:
                key = obj['Key']
                file_name = key.split("/")[-1]

                if file_name in existing_files:
                    skipped += 1
                    return

                if obj['LastModified'].date() != target_date:
                    return

                raw = s3.get_object(Bucket=BUCKET_NAME, Key=key)['Body'].read()
                msg = email.message_from_bytes(raw, policy=policy.default)

                subject = (msg.get("subject") or "").upper()
                subject_words = set(normalize(subject).split())

                name_words = set(normalize(FULL_NAME).split())

                # 🔹 MATCH LOGIC
                if LOCATION_NAME not in subject_words and len(name_words.intersection(subject_words)) < 2:
                    return

                # 🔹 SAVE PATH
                final_path = date_folder
                os.makedirs(final_path, exist_ok=True)

                eml_path = os.path.join(final_path, file_name + ".eml")

                with open(eml_path, "wb") as f:
                    f.write(raw)

                log_callback(f"[{LOCATION_NAME}] Email → {eml_path}")

                # 🔹 ATTACHMENTS
                for part in msg.walk():

                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True)
                        if body:
                            with open(eml_path + ".txt", "wb") as f:
                                f.write(body)

                    if part.get_filename():
                        att_name = part.get_filename()
                        att_path = os.path.join(final_path, att_name)

                        with open(att_path, "wb") as f:
                            f.write(part.get_payload(decode=True))

                        log_callback(f"[{LOCATION_NAME}] Attachment → {att_path}")

                downloaded += 1

            except Exception as e:
                log_callback(f"⚠ File Error → {e}")

        # 🔹 MULTITHREAD
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(process_object, all_objects)

        if downloaded == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Completed | Downloaded: {downloaded} | Skipped: {skipped}")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")