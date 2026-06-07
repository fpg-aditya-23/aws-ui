import boto3
import os
from datetime import datetime, timedelta
import email
from email import policy

# 🔹 CONFIG
CONFIG = {
    "bucket": "ing-kempinski-hotels-sep-apnortheast2-prod",
    "prefix": "SEP/SES/",
    "profile": "fpg-cust-kempinski-hotels-resorts",
    "codes": ["KIPEK4", "KINKG1", "KISHA5", "NUPEK6", "KITNA1"]
}


# 🔹 FIND LOCATION CODE
def find_code(text, codes):
    text_upper = text.upper()
    for code in codes:
        if code in text_upper:
            return code
    return None


# 🔥 MAIN FUNCTION (UI CONNECTED)
def download_data(location, date_input, base_path, logger):

    try:
        session = boto3.Session(profile_name=CONFIG["profile"])
        s3 = session.client('s3')

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        # =========================
        # 🔥 FOLDER STRUCTURE
        # base / KEMPINSKI(SEP) / DATE / LOCATION
        # =========================
        base_folder = os.path.join(base_path, "KEMPINSKI(SEP)", date_input)
        os.makedirs(base_folder, exist_ok=True)

        not_found_dir = os.path.join(base_folder, "KEMPINSKI_NOT_FOUND")
        os.makedirs(not_found_dir, exist_ok=True)

        logger(f"⬇ Starting KEMPINSKI(SEP) → {location}")

        download_count = 0
        sorted_count = 0

        paginator = s3.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=CONFIG["bucket"], Prefix=CONFIG["prefix"]):

            for obj in page.get('Contents', []):

                # 🔥 IST TIME FIX
                file_time = obj['LastModified'].replace(tzinfo=None) + timedelta(hours=5, minutes=30)

                if not (start_date <= file_time < end_date):
                    continue

                try:
                    key = obj['Key']
                    raw_email = s3.get_object(Bucket=CONFIG["bucket"], Key=key)['Body'].read()

                    file_name = key.split("/")[-1]
                    eml_name = file_name + ".eml"

                    msg = email.message_from_bytes(raw_email, policy=policy.default)

                    # 🔥 BUILD FULL TEXT
                    full_text = file_name + str(msg.get("Subject", ""))

                    # 🔹 BODY
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True)
                            if body:
                                full_text += body.decode(errors="ignore")

                    # 🔹 ATTACHMENT NAMES
                    for part in msg.iter_attachments():
                        filename = part.get_filename()
                        if filename:
                            full_text += filename

                    # 🔹 FIND CODE
                    code = find_code(full_text, CONFIG["codes"])

                    # 🔥 FILTER SELECTED LOCATION
                    if code != location:
                        continue

                    # 🔹 CREATE LOCATION FOLDER
                    target_dir = os.path.join(base_folder, code)
                    os.makedirs(target_dir, exist_ok=True)

                    # 🔹 SAVE EML
                    eml_path = os.path.join(target_dir, eml_name)

                    base, ext = os.path.splitext(eml_path)
                    counter = 1
                    while os.path.exists(eml_path):
                        eml_path = f"{base}_{counter}{ext}"
                        counter += 1

                    with open(eml_path, "wb") as f:
                        f.write(raw_email)

                    logger(f"✅ {eml_name} → {code}")

                    # 🔹 SAVE ATTACHMENTS
                    for part in msg.iter_attachments():
                        filename = part.get_filename()
                        if filename:
                            payload = part.get_payload(decode=True)

                            file_path = os.path.join(target_dir, filename)

                            base, ext = os.path.splitext(file_path)
                            counter = 1
                            while os.path.exists(file_path):
                                file_path = f"{base}_{counter}{ext}"
                                counter += 1

                            with open(file_path, "wb") as f:
                                f.write(payload)

                    download_count += 1
                    sorted_count += 1

                except Exception as e:
                    logger(f"❌ {key} → {e}")

        if download_count == 0:
            logger("❌ No data found")

        logger(f"✅ KEMPINSKI(SEP) Done → Downloaded: {download_count}, Sorted: {sorted_count}")

    except Exception as e:
        logger(f"❌ AWS Error → {e}")