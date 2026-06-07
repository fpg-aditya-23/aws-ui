import boto3
import os
from datetime import datetime, timedelta
import email
from email import policy

# 🔹 CONFIG
CONFIG = {
    "bucket": "ing-jannah-hotels-sep-apsouth1-prod",
    "prefix": "SEP/SES/",
    "profile": "fpg-cust-jannah-hotels-resorts"
}


# 🔹 FIND LOCATION CODE
def find_code(text):
    text = text.upper()

    phxlc_keywords = [
        "THE PHOENICIAN",
        "LUXURY COLLECTION",
        "SCOTTSDALE",
        "THE PHOENICIAN A LUXURY COLLECTION RESORT SCOTTSDALE",
        "THE PHOENICIAN, A LUXURY COLLECTION RESORT, SCOTTSDALE",
        "JANNAH EXECUTIVE HOTEL APARTMENTS",
        "JANNAH HOTELS",
        "PHXPC",
        "PRIVATE COLLECTION",
        "PHOENICIAN PRIVATE COLLECTION",
        "PHOENICIAN RESIDENCES"
    ]

    for keyword in phxlc_keywords:
        if keyword in text:
            return "PHXLC"

    return None


# 🔥 MAIN FUNCTION
def download_data(location, date_input, base_path, logger):

    try:

        session = boto3.Session(profile_name=CONFIG["profile"])
        s3 = session.client("s3")

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        # =========================
        # LIGHTSPEED / DATE
        # =========================
        pms_folder = os.path.join(base_path, "LIGHTSPEED")
        os.makedirs(pms_folder, exist_ok=True)

        date_folder = os.path.join(pms_folder, date_input)
        os.makedirs(date_folder, exist_ok=True)

        not_found_dir = os.path.join(date_folder, "LIGHTSPEED_NOT_FOUND")
        os.makedirs(not_found_dir, exist_ok=True)

        logger(f"⬇ Starting LIGHTSPEED → {location}")

        downloaded = 0
        sorted_count = 0

        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(
                Bucket=CONFIG["bucket"],
                Prefix=CONFIG["prefix"]):

            for obj in page.get("Contents", []):

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

                    msg = email.message_from_bytes(
                        raw_email,
                        policy=policy.default
                    )

                    file_name = key.split("/")[-1]
                    eml_name = file_name + ".eml"

                    # 🔹 Build searchable text
                    full_text = file_name

                    subject = str(msg.get("Subject", ""))
                    sender = str(msg.get("From", ""))

                    full_text += " " + subject
                    full_text += " " + sender

                    attachments = []

                    # 🔹 Body Search
                    for part in msg.walk():

                        if part.get_content_type() == "text/plain":

                            body = part.get_payload(decode=True)

                            if body:

                                try:
                                    body_text = body.decode(errors="ignore")
                                    full_text += " " + body_text
                                except:
                                    pass

                    # 🔹 Attachment Search
                    for part in msg.iter_attachments():

                        filename = part.get_filename()

                        if filename:

                            payload = part.get_payload(decode=True)

                            attachments.append((filename, payload))

                            full_text += " " + filename

                    # 🔹 Find Location
                    code = find_code(full_text)

                    if code:
                        target_dir = os.path.join(date_folder, code)
                    else:
                        target_dir = not_found_dir

                    os.makedirs(target_dir, exist_ok=True)

                    # 🔹 Save EML
                    eml_path = os.path.join(target_dir, eml_name)

                    base, ext = os.path.splitext(eml_path)
                    counter = 1

                    while os.path.exists(eml_path):
                        eml_path = f"{base}_{counter}{ext}"
                        counter += 1

                    with open(eml_path, "wb") as f:
                        f.write(raw_email)

                    # 🔹 Save Attachments
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
                    sorted_count += 1

                    logger(
                        f"✅ {os.path.basename(eml_path)} → "
                        f"{os.path.basename(target_dir)}"
                    )

                except Exception as e:
                    logger(f"❌ {key} → {e}")

        if downloaded == 0:
            logger("❌ No data found")

        logger(
            f"✅ LIGHTSPEED Done → "
            f"Downloaded: {downloaded}, "
            f"Sorted: {sorted_count}"
        )

    except Exception as e:
        logger(f"❌ AWS Error → {e}")