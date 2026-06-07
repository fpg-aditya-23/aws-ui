import boto3
import os
from datetime import datetime, timedelta


def get_s3_client():
    profile_name = os.getenv("AWS_PROFILE") or os.getenv("AWS_DEFAULT_PROFILE")
    if profile_name:
        session = boto3.Session(profile_name=profile_name)
    else:
        session = boto3.Session()
    return session.client("s3")


def download_onq(location, date_input, base_path, logger):
    s3 = get_s3_client()

    BUCKET_NAME = "ing-sftp-hilton"
    PREFIX = "SFTP/"

    LOCATION_PREFIX = {
        "OLBCLCI": "fpg_OLBCLCI",
        "AMSCSDI": "fpg_amscsdi",
        "PARPYPY": "fpg_parpypy",
        "BERWAWA": "fpg_berwawa",
        "OLBBRQQ": "fpg_OLBBRQQ",
        "VIEHIHI": "fpg_viehihi"
    }

    prefix_filter = LOCATION_PREFIX.get(location)

    if not prefix_filter:
        logger(f"❌ Invalid location: {location}")
        return

    target_date = datetime.strptime(date_input, "%Y-%m-%d").date()

    # =========================
    # 📁 STRUCTURE: ONQ / DATE
    # =========================
    BASE_ONQ = os.path.join(base_path, "ONQ", date_input)
    os.makedirs(BASE_ONQ, exist_ok=True)

    logger(f"📂 ONQ Folder: {BASE_ONQ}")
    logger(f"⬇ Starting {location}")

    paginator = s3.get_paginator("list_objects_v2")

    download_count = 0

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):

        for obj in page.get("Contents", []):

            try:
                file_date = (
                    obj["LastModified"] + timedelta(hours=5, minutes=30)
                ).date()

                if file_date != target_date:
                    continue

                key = obj["Key"]
                file_name = key.split("/")[-1]

                if not file_name.lower().startswith(prefix_filter.lower()):
                    continue

                # =========================
                # 📁 OPTIONAL: GROUP BY LOCATION INSIDE DATE
                # =========================
                location_folder = os.path.join(BASE_ONQ, location)
                os.makedirs(location_folder, exist_ok=True)

                local_path = os.path.join(location_folder, file_name)

                s3.download_file(BUCKET_NAME, key, local_path)

                logger(f"✅ {location} → {file_name}")
                download_count += 1

            except Exception as e:
                logger(f"❌ {location} ERROR → {e}")

    if download_count == 0:
        logger(f"❌ {location} No Data")

    logger("\n" + "=" * 50)
    logger(f"🎯 {location} DONE")
    logger("=" * 50)
    logger(f"📥 Total Files: {download_count}")