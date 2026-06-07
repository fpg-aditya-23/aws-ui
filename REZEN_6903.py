import boto3
import os
from datetime import datetime, timedelta
import email
from email import policy

# 🔹 CONFIG
BUCKET_NAME = "ing-rosewood-rezen-apnortheast-2"
PREFIX = "Rezen/SES/"
PROFILE = "fpg-cust-rosewood"

LOCATION_NAME = "6903"


# 🔹 MAIN FUNCTION (UI CALL)
def download_data(selected_location, date_input, base_path, log_callback):

    try:
        session = boto3.Session(profile_name=PROFILE)
        s3 = session.client('s3')

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        log_callback(f"⬇ Starting {selected_location}")

        # 🔹 PATH
        download_dir = os.path.join(base_path, selected_location, date_input)
        os.makedirs(download_dir, exist_ok=True)

        paginator = s3.get_paginator('list_objects_v2')

        total_files = 0

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
            for obj in page.get('Contents', []):

                try:
                    file_time = obj['LastModified'].replace(tzinfo=None) + timedelta(hours=5, minutes=30)

                    if not (start_date <= file_time < end_date):
                        continue

                    key = obj['Key']
                    file_name = key.split("/")[-1]
                    eml_path = os.path.join(download_dir, file_name + ".eml")

                    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                    raw_email = response['Body'].read()

                    # 🔹 SAVE EMAIL
                    with open(eml_path, "wb") as f:
                        f.write(raw_email)

                    log_callback(f"[{LOCATION_NAME}] Email → {eml_path}")
                    total_files += 1

                    msg = email.message_from_bytes(raw_email, policy=policy.default)

                    # 🔹 BODY
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True)
                            if body:
                                txt_path = eml_path + ".txt"
                                with open(txt_path, "wb") as f:
                                    f.write(body)

                    # 🔹 ATTACHMENTS
                    for part in msg.iter_attachments():
                        filename = part.get_filename()
                        if filename:
                            file_path = os.path.join(download_dir, filename)

                            with open(file_path, "wb") as f:
                                f.write(part.get_payload(decode=True))

                            log_callback(f"[{LOCATION_NAME}] Attachment → {file_path}")

                except Exception as e:
                    log_callback(f"⚠ File Error → {e}")

        if total_files == 0:
            log_callback("❌ No data found")
        else:
            log_callback(f"✅ Completed | Downloaded: {total_files}")

    except Exception as e:
        log_callback(f"❌ AWS Error → {e}")