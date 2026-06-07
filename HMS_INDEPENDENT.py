import boto3
import os
from datetime import datetime, timedelta
import email
from email import policy

CONFIG = {
    "bucket": "ing-independent-useast-prod",
    "prefix": "INFORHMS/SES/",
    "profile": "fpg-proj-ing-prod1"
}

LOCATIONS = {
    "TYSCMV": [
        "TYSCMV",
        "CAMP MARGARITAVILLE",
        "PIGEON FORGE",
        "RV RESORT",
        "LODGE"
    ],

    "SSIKP": [
        "SSIKP",
        "THE KING AND PRINCE",
        "KING AND PRINCE",
        "BEACH",
        "GOLF RESORT"
    ],

    "EAM": [
        "EAM",
        "EAST MIAMI",
        "EAST, MIAMI"
    ]
}


def find_code(text):
    text = text.upper()

    for code, patterns in LOCATIONS.items():
        for pattern in patterns:
            if pattern.upper() in text:
                return code

    return None


def download_data(location, date_input, base_path, logger):

    try:

        session = boto3.Session(profile_name=CONFIG["profile"])
        s3 = session.client("s3")

        start_date = datetime.strptime(date_input, "%Y-%m-%d")
        end_date = start_date + timedelta(days=1)

        pms_folder = os.path.join(base_path, "HMS")
        os.makedirs(pms_folder, exist_ok=True)

        date_folder = os.path.join(pms_folder, date_input)
        os.makedirs(date_folder, exist_ok=True)

        not_found_dir = os.path.join(date_folder, "HMS_NOT_FOUND")
        os.makedirs(not_found_dir, exist_ok=True)

        downloaded = 0

        logger(f"⬇ Starting HMS → {location}")

        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(
                Bucket=CONFIG["bucket"],
                Prefix=CONFIG["prefix"]):

            for obj in page.get("Contents", []):

                file_time = obj["LastModified"].replace(
                    tzinfo=None
                ) + timedelta(hours=5, minutes=30)

                if not (start_date <= file_time < end_date):
                    continue

                try:

                    key = obj["Key"]

                    raw_email = s3.get_object(
                        Bucket=CONFIG["bucket"],
                        Key=key
                    )["Body"].read()

                    msg = email.message_from_bytes(
                        raw_email,
                        policy=policy.default
                    )

                    full_text = key
                    full_text += str(msg.get("Subject", ""))
                    full_text += str(msg.get("From", ""))

                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True)
                            if body:
                                full_text += body.decode(
                                    errors="ignore"
                                )

                    code = find_code(full_text)

                    if code != location:
                        continue

                    target_dir = os.path.join(
                        date_folder,
                        code
                    )

                    os.makedirs(target_dir, exist_ok=True)

                    file_name = key.split("/")[-1] + ".eml"

                    eml_path = os.path.join(
                        target_dir,
                        file_name
                    )

                    with open(eml_path, "wb") as f:
                        f.write(raw_email)

                    for part in msg.iter_attachments():

                        filename = part.get_filename()

                        if filename:

                            payload = part.get_payload(
                                decode=True
                            )

                            with open(
                                    os.path.join(
                                        target_dir,
                                        filename
                                    ),
                                    "wb"
                            ) as f:
                                f.write(payload)

                    downloaded += 1

                    logger(
                        f"✅ {file_name} → {code}"
                    )

                except Exception as e:
                    logger(f"❌ {e}")

        if downloaded == 0:
            logger("❌ No data found")

        logger(
            f"✅ HMS Done → Downloaded: {downloaded}"
        )

    except Exception as e:
        logger(f"❌ AWS Error → {e}")