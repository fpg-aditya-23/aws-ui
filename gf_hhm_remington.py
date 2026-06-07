import boto3
import os
from datetime import datetime, timedelta
import email
from email import policy
from email.utils import parseaddr

# 🔹 MASTER CONFIG
CONFIGS = {

    "GF": {
        "bucket": "ing-gf-hotels-and-resorts-useast1",
        "prefix": "FOSSE/SES/",
        "profile": "fpg-cust-gf-hotels",
        "codes": ["LBBCY","CAKCC","MSNWM","MSNCW","WASPS","MGWMG","BWIEA","RSWNS","RSWFS","MCOUS","HOUCY","WASGL"]
    },

    "HHM": {
        "bucket": "ing-hhm-hospitality",
        "prefix": "PROD-FOSSE/ses/",
        "profile": "fpg-proj-padraig",
        "codes": ["MCOTE", "MCORL", "WASNY", "BOSBL"]
    },

    "REMINGTON": {
        "bucket": "ing-remington-hotel-and-restaurant-management",
        "prefix": "PROD-FOSSE/ses/",
        "profile": "fpg-proj-padraig",
        "codes": ["JAXRI", "BMGCY", "ATLBF"]
    }
}


# 🔹 FIND CODE
def find_code(text, sender, codes):

    text_upper = text.upper()

    # GF Special
    if sender:
        actual_email = parseaddr(sender)[1].lower()

        if "cakccfrontdesk" in actual_email:
            return "CAKCC"

    # HHM Special
    if "MCOTEFRONTDESK@HHMLP.COM" in text_upper:
        return "MCOTE"

    for code in codes:
        if code in text_upper:
            return code

    return None


# 🔥 MAIN FUNCTION
def download_data(location, date_input, base_path, logger):

    if location not in CONFIGS:
        logger(f"❌ Invalid location: {location}")
        return

    config = CONFIGS[location]

    session = boto3.Session(profile_name=config["profile"])
    s3 = session.client("s3")

    start_date = datetime.strptime(date_input, "%Y-%m-%d")
    end_date = start_date + timedelta(days=1, hours=4)

    # =========================
    # FOSSE > DATE > GF/HHM/REMINGTON
    # =========================

    fosse_folder = os.path.join(base_path, "FOSSE")
    os.makedirs(fosse_folder, exist_ok=True)

    date_folder = os.path.join(fosse_folder, date_input)
    os.makedirs(date_folder, exist_ok=True)

    group_folder = os.path.join(date_folder, location)
    os.makedirs(group_folder, exist_ok=True)

    not_found_dir = os.path.join(group_folder, "NOT FOUND")
    os.makedirs(not_found_dir, exist_ok=True)

    # 🔹 FOSSE ROOT FOLDER
    fosse_root = os.path.join(base_path, "FOSSE")
    os.makedirs(fosse_root, exist_ok=True)

    # 🔹 TRACK FILE INSIDE FOSSE FOLDER
    track_file = os.path.join(fosse_root, f"{location}_track.txt")

    downloaded_set = set()

    if os.path.exists(track_file):
        with open(track_file, "r") as f:
            downloaded_set = set(f.read().splitlines())

    download_count = 0
    sorted_count = 0

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=config["bucket"],
        Prefix=config["prefix"]
    ):

        for obj in page.get("Contents", []):

            key = obj["Key"]

            if key in downloaded_set:
                continue

            file_time = (
                obj["LastModified"].replace(tzinfo=None)
                + timedelta(hours=5, minutes=30)
            )

            if not (start_date <= file_time < end_date):
                continue

            try:

                raw_email = s3.get_object(
                    Bucket=config["bucket"],
                    Key=key
                )["Body"].read()

                file_name = key.split("/")[-1]
                eml_name = file_name + ".eml"

                msg = email.message_from_bytes(
                    raw_email,
                    policy=policy.default
                )

                full_text = file_name + str(msg.get("Subject", ""))
                sender = msg.get("From", "")

                # BODY
                for part in msg.walk():

                    if part.get_content_type() == "text/plain":

                        body = part.get_payload(decode=True)

                        if body:
                            full_text += body.decode(errors="ignore")

                # ATTACHMENTS
                attachments = []

                for part in msg.iter_attachments():

                    filename = part.get_filename()

                    if filename:

                        payload = part.get_payload(decode=True)

                        if payload:
                            attachments.append(
                                (filename, payload)
                            )

                            full_text += filename

                # FIND CODE
                code = find_code(
                    full_text,
                    sender,
                    config["codes"]
                )

                if code:

                    target_dir = os.path.join(
                        group_folder,
                        code
                    )

                    os.makedirs(
                        target_dir,
                        exist_ok=True
                    )

                else:
                    target_dir = not_found_dir

                # SAVE EML
                eml_path = os.path.join(
                    target_dir,
                    eml_name
                )

                base, ext = os.path.splitext(eml_path)
                counter = 1

                while os.path.exists(eml_path):
                    eml_path = f"{base}_{counter}{ext}"
                    counter += 1

                with open(eml_path, "wb") as f:
                    f.write(raw_email)

                # SAVE ATTACHMENTS
                for filename, payload in attachments:

                    file_path = os.path.join(
                        target_dir,
                        filename
                    )

                    base, ext = os.path.splitext(file_path)
                    counter = 1

                    while os.path.exists(file_path):
                        file_path = f"{base}_{counter}{ext}"
                        counter += 1

                    with open(file_path, "wb") as f:
                        f.write(payload)

                logger(
                    f"✅ [{location}] "
                    f"{os.path.basename(eml_path)} "
                    f"→ {os.path.basename(target_dir)}"
                )

                download_count += 1
                sorted_count += 1

                with open(track_file, "a") as f:
                    f.write(key + "\n")

            except Exception as e:
                logger(f"❌ [{location}] {key} → {e}")

    if download_count == 0:
        logger("❌ No data found")

    logger(
        f"✅ {location} Done → "
        f"Downloaded: {download_count}, "
        f"Sorted: {sorted_count}"
    )