import boto3
import botocore
import os
from datetime import datetime
import email
from email import policy
import subprocess
import sys


# 🔹 CONFIG
BUCKET_NAME = "ing-independent-useast-prod"
PREFIX = "INFORHMS/SES/"
PROFILES = [
    "fpg-proj-ing-prod1",
    "fpg-proj-ing-prod",
]
REGION = "us-east-1"


# 🔹 AWS LOGIN (SSO)
def aws_login(log_callback=None, profiles=None):
    try:
        profiles = profiles or PROFILES + [
            "fpg-cust-independent",
            "fpg-cust-rosewood",
            "fpg-proj-padraig",
            "fpg-cust-gf-hotels",
            "fpg-cust-davidson-hospitality",
            "fpg-cust-kempinski-hotels-resorts",
            "fpg-cust-jannah-hotels-resorts",
        ]

        for profile in profiles:
            try:
                if log_callback:
                    log_callback(f"🔐 Logging in: {profile}")

                subprocess.run(
                    ["aws", "sso", "login", "--profile", profile],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            except subprocess.CalledProcessError:
                if log_callback:
                    log_callback(f"⚠ SSO login failed: {profile}")
                continue

        return True, "SSO login completed"

    except Exception as e:
        return False, f"AWS Login Error: {str(e)}"


# 🔹 SAFE SESSION CREATION
def get_s3_client(log_callback=None):
    for profile in PROFILES:
        try:
            if log_callback:
                log_callback(f"🔄 Creating AWS session using profile: {profile}")

            session = boto3.Session(profile_name=profile, region_name=REGION)
            s3 = session.client("s3")

            # Test credentials
            s3.list_buckets()

            if log_callback:
                log_callback(f"✅ AWS Profile login success: {profile}")

            return s3

        except botocore.exceptions.ProfileNotFound:
            if log_callback:
                log_callback(f"❌ Profile not found: {profile}")
            continue

        except botocore.exceptions.NoCredentialsError:
            if log_callback:
                log_callback(f"❌ No AWS credentials found for profile: {profile}")
            continue

        except Exception as e:
            if log_callback:
                log_callback(f"❌ AWS connection error for profile {profile}: {str(e)}")
            continue

    # 🔁 Fallback to default credentials
    try:
        if log_callback:
            log_callback("🔄 Trying default AWS credentials...")

        session = boto3.Session(region_name=REGION)
        s3 = session.client("s3")
        s3.list_buckets()

        if log_callback:
            log_callback("✅ Default AWS login success")

        return s3

    except Exception as e:
        if log_callback:
            log_callback(f"❌ Default login failed: {str(e)}")
        return None


# 🔹 LOCATION DETECTION
def detect_location(subject, sender):
    subject = subject.upper() if subject else ""
    sender = sender.lower() if sender else ""

    if "BNAMVN" in subject:
        return "BNAMVN"

    if "info@piersixtysixresort.com" in sender:
        return "PIER66"

    return None


# 🔹 MAIN DOWNLOAD FUNCTION
def download_data(selected_location, date_input, base_path, log_callback):

    try:
        s3 = get_s3_client(log_callback)

        if not s3:
            log_callback("❌ Unable to connect to AWS. Stopping process.")
            return

        try:
            selected_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            log_callback("❌ Invalid date format. Use YYYY-MM-DD")
            return

        paginator = s3.get_paginator('list_objects_v2')

        data_found = False
        log_callback(f"⬇ Starting download for {selected_location} | {date_input}")

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):

            contents = page.get('Contents')
            if not contents:
                continue

            for obj in contents:

                try:
                    file_time = obj['LastModified'].replace(tzinfo=None)

                    if file_time.date() != selected_date:
                        continue

                    key = obj['Key']

                    # 🔹 Get object
                    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
                    raw_email = response['Body'].read()

                    # 🔹 Parse email safely
                    try:
                        msg = email.message_from_bytes(raw_email, policy=policy.default)
                    except Exception:
                        log_callback(f"⚠ Skipped invalid email: {key}")
                        continue

                    subject = msg.get('Subject', '')
                    sender = msg.get('From', '')

                    location = detect_location(subject, sender)

                    if location != selected_location:
                        continue

                    data_found = True

                    # 🔹 Create folder
                    download_dir = os.path.join(base_path, selected_location, date_input)
                    os.makedirs(download_dir, exist_ok=True)

                    # 🔹 Save email
                    file_name = os.path.basename(key)
                    eml_path = os.path.join(download_dir, file_name)

                    with open(eml_path, "wb") as f:
                        f.write(raw_email)

                    log_callback(f"[{location}] Email → {file_name}")

                    # 🔹 Attachments
                    for part in msg.iter_attachments():
                        try:
                            filename = part.get_filename()

                            if filename:
                                file_path = os.path.join(download_dir, filename)

                                with open(file_path, "wb") as f:
                                    f.write(part.get_payload(decode=True))

                                log_callback(f"[{location}] Attachment → {filename}")

                        except Exception as att_err:
                            log_callback(f"⚠ Attachment error → {att_err}")

                except Exception as file_err:
                    log_callback(f"⚠ File Error → {file_err}")

        if not data_found:
            log_callback("❌ No data found for selected filters")
        else:
            log_callback("✅ Download completed successfully")

    except Exception as e:
        log_callback(f"❌ Fatal Error → {str(e)}")