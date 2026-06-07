import boto3
import os
from datetime import datetime, timedelta
import email
from email import policy


# 🔹 JEHA CONFIG
CONFIG = {
    "bucket": "ing-jannah-hotels-sep-apsouth1-prod",
    "prefix": "SEP/SES/",
    "profile": "fpg-cust-jannah-hotels-resorts"
}


# 🔹 KEYWORDS FOR CLASSIFICATION
def find_code(text):
    text = text.upper()

    keywords = [
        "JEHA",
        "JANNAH EXECUTIVE",
        "JANNAH HOTEL APARTMENTS",
        "JANNAH EXECUTIVE HOTEL APARTMENTS"
    ]

    for keyword in keywords:
        if keyword in text:
            return "JEHA"

    return None


# 🔥 MAIN FUNCTION
def download_data(date_input, base_path, logger):

    try:

        session = boto3.Session(profile_name=CONFIG["profile"])
        s3 = session.client("s3")

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        # 📁 FOLDER STRUCTURE (FIXED - NO "/" BUG)
        root_folder = os.path.join(base_path, "JEHA")
        date_folder = os.path.join(root_folder, date_input)
        not_found_dir = os.path.join(date_folder, "NOT_FOUND")

        os.makedirs(date_folder, exist_ok=True)
        os.makedirs(not_found_dir, exist_ok=True)

        logger("⬇ START JEHA DOWNLOAD")
        logger(f"BUCKET: {CONFIG['bucket']}")
        logger(f"PREFIX: {CONFIG['prefix']}")

        paginator = s3.get_paginator("list_objects_v2")

        downloaded = 0

        for page in paginator.paginate(
            Bucket=CONFIG["bucket"],
            Prefix=CONFIG["prefix"]
        ):

            if "Contents" not in page:
                continue

            for obj in page["Contents"]:

                try:

                    file_time = obj["LastModified"].replace(
                        tzinfo=None
                    ) + timedelta(hours=5, minutes=30)

                    if not (start_date <= file_time < end_date):
                        continue

                    key = obj["Key"]

                    raw_email = s3.get_object(
                        Bucket=CONFIG["bucket"],
                        Key=key
                    )["Body"].read()

                    msg = email.message_from_bytes(raw_email, policy=policy.default)

                    file_name = key.split("/")[-1]
                    eml_name = file_name + ".eml"

                    full_text = file_name
                    full_text += " " + str(msg.get("Subject", ""))
                    full_text += " " + str(msg.get("From", ""))

                    # 📩 EMAIL BODY
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True)
                            if body:
                                full_text += " " + body.decode(errors="ignore")

                    # 📎 ATTACHMENTS
                    attachments = []

                    for part in msg.iter_attachments():
                        filename = part.get_filename()
                        if filename:
                            payload = part.get_payload(decode=True)
                            attachments.append((filename, payload))
                            full_text += " " + filename

                    code = find_code(full_text)

                    # ✅ FIXED PATH LOGIC (NO / OPERATOR USED)
                    if code == "JEHA":
                        target_dir = os.path.join(date_folder, "JEHA")
                    else:
                        target_dir = not_found_dir

                    os.makedirs(target_dir, exist_ok=True)

                    # 💾 SAVE EMAIL FILE
                    eml_path = os.path.join(target_dir, eml_name)

                    base, ext = os.path.splitext(eml_path)
                    counter = 1

                    while os.path.exists(eml_path):
                        eml_path = f"{base}_{counter}{ext}"
                        counter += 1

                    with open(eml_path, "wb") as f:
                        f.write(raw_email)

                    # 💾 SAVE ATTACHMENTS
                    for filename, payload in attachments:

                        file_path = os.path.join(target_dir, filename)

                        base, ext = os.path.splitext(file_path)
                        counter = 1

                        while os.path.exists(file_path):
                            file_path = f"{base}_{counter}{ext}"
                            counter += 1

                        with open(file_path, "wb") as f:
                            f.write(payload)

                    downloaded += 1
                    logger(f"✅ {file_name} → {os.path.basename(target_dir)}")

                except Exception as e:
                    logger(f"❌ ERROR {key} → {str(e)}")

        if downloaded == 0:
            logger("❌ NO DATA FOUND")

        logger(f"🎯 JEHA DONE → Total Downloaded: {downloaded}")

    except Exception as e:
        logger(f"❌ FATAL ERROR → {str(e)}")