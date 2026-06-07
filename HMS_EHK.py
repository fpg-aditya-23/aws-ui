import boto3
import os
from datetime import datetime, timedelta
from email import policy
import email

# 🔹 CONFIG
BUCKET_NAME = "ing-independent-hms-apsoutheast1"
PREFIX = "HMS/SES/"
PROFILE = "fpg-cust-independent"

LOCATION_NAME = "EHK"


# 🔹 MAIN FUNCTION (UI CALL)
def download_data(selected_location, date_input, base_path, log_callback):

    try:
        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

        log_callback(f"⬇ Starting {selected_location}")

        # 🔹 PATH (same UI structure)
        download_dir = os.path.join(base_path, selected_location, date_input)
        os.makedirs(download_dir, exist_ok=True)

        paginator = s3.get_paginator('list_objects_v2')

        downloaded = 0

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):

            for obj in page.get('Contents', []):

                try:
                    # 🔥 IST FIX
                    ist_time = obj['LastModified'] + timedelta(hours=5, minutes=30)
                    file_date = ist_time.date()

                    if file_date != target_date:
                        continue

                    key = obj['Key']
                    file_name = key.split("/")[-1]

                    eml_path = os.path.join(download_dir, file_name + ".eml")

                    raw = s3.get_object(Bucket=BUCKET_NAME, Key=key)['Body'].read()

                    # 🔹 SAVE EMAIL
                    with open(eml_path, "wb") as f:
                        f.write(raw)

                    log_callback(f"[{LOCATION_NAME}] Email → {eml_path}")

                    msg = email.message_from_bytes(raw, policy=policy.default)

                    # 🔹 ATTACHMENTS
                    for part in msg.iter_attachments():
                        filename = part.get_filename()

                        if filename:
                            file_path = os.path.join(download_dir, filename)

                            # 🔥 prevent overwrite
                            base, ext = os.path.splitext(file_path)
                            counter = 1
                            while os.path.exists(file_path):
                                file_path = f"{base}_{counter}{ext}"
                                counter += 1

                            with open(file_path, "wb") as f:
                                f.write(part.get_payload(decode=True))

                            log_callback(f"[{LOCATION_NAME}] Attachment → {file_path}")

                    downloaded += 1

                except Exception as e:
                    log_callback(f"⚠ File Error → {e}")

        if downloaded == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Completed | Downloaded: {downloaded}")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")