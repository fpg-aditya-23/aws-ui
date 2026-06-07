import os
import zipfile
import pandas as pd
from email import policy
from email.parser import BytesParser
import shutil
import re


def run_fosse_sort(zip_file_path, base_path, date_input):

    # =========================
    # EXCEL FILE PATH
    # =========================
    excel_file_path = r"C:\FOSSE_SORTING_SCRIPT\BPO Fosse list 1.xlsx"

    # =========================
    # OUTPUT STRUCTURE
    # =========================
    sorting_folder = os.path.join(base_path, "SORTED_RAW")
    os.makedirs(sorting_folder, exist_ok=True)

    today_date = date_input
    unique_id = 1

    while True:
        output_folder = os.path.join(sorting_folder, f"{today_date}_{unique_id}")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            break
        unique_id += 1

    found_folder = os.path.join(output_folder, "found")
    not_found_folder = os.path.join(output_folder, "not_found")

    os.makedirs(found_folder, exist_ok=True)
    os.makedirs(not_found_folder, exist_ok=True)

    # =========================
    # HELPERS
    # =========================
    def get_unique_filename(directory, filename):
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename

        while os.path.exists(os.path.join(directory, new_filename)):
            new_filename = f"{base}_{counter}{ext}"
            counter += 1

        return new_filename

    def extract_body(msg):
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            return payload.decode("utf-8", errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="ignore")
        except:
            pass
        return "No message body found."

    def extract_attachments(msg, folder):
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get("Content-Disposition", None)

                if content_disposition and "attachment" in content_disposition:
                    filename = part.get_filename()

                    if filename:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload is None:
                                continue

                            unique_name = get_unique_filename(folder, filename)
                            path = os.path.join(folder, unique_name)

                            with open(path, "wb") as f:
                                f.write(payload)

                            attachments.append(unique_name)

                        except Exception as e:
                            print(f"Attachment error {filename}: {e}")

        return attachments

    def write_details(folder, name, subject, sender, to_field, body, attachments):
        path = os.path.join(folder, "details.txt")

        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"File: {name}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Sender: {sender}\n")
            f.write(f"To: {to_field}\n")
            f.write(f"Body:\n{body}\n")
            f.write("Attachments:\n")

            for a in attachments:
                f.write(f"  - {a}\n")

            f.write("=" * 80 + "\n")

    # =========================
    # LOAD EXCEL
    # =========================
    df = pd.read_excel(excel_file_path)

    df['Location ID'] = df['Location ID'].astype(str).str.strip().str.upper()
    df['Reports received'] = df['Reports received'].astype(str).str.strip().str.upper()

    # =========================
    # PROCESS ZIP
    # =========================
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:

        eml_files = [f for f in zip_ref.namelist() if f.lower().endswith(".eml")]

        print(f"Found {len(eml_files)} emails")

        for i, eml_filename in enumerate(eml_files, 1):

            print(f"Processing {i}/{len(eml_files)}")

            raw = zip_ref.read(eml_filename)
            msg = BytesParser(policy=policy.default).parsebytes(raw)

            subject = str(msg.get("subject", ""))
            sender = str(msg.get("from", ""))
            to_field = str(msg.get("to", ""))

            body = extract_body(msg)

            found = False
            location_found = "NAN"

            for _, row in df.iterrows():

                loc_id = str(row["Location ID"])
                rep = str(row["Reports received"])

                loc_pattern = re.compile(r'\b' + re.escape(loc_id) + r'\b', re.IGNORECASE)
                rep_pattern = re.compile(r'\b' + re.escape(rep) + r'\b', re.IGNORECASE)

                if (loc_pattern.search(subject) or loc_pattern.search(sender) or
                    rep_pattern.search(subject) or rep_pattern.search(sender)):

                    location_found = loc_id
                    found = True
                    break

            # =========================
            # SAVE FILES
            # =========================
            if found:
                folder = os.path.join(found_folder, f"Location_{location_found}")
            else:
                folder = not_found_folder

            os.makedirs(folder, exist_ok=True)

            unique_name = get_unique_filename(folder, os.path.basename(eml_filename))

            with open(os.path.join(folder, unique_name), "wb") as f:
                f.write(raw)

            attachments = extract_attachments(msg, folder)

            write_details(folder, unique_name, subject, sender, to_field, body, attachments)

    # =========================
    # FINAL OUTPUT
    # =========================
    print("DONE:", output_folder)
    print("FOUND:", found_folder)
    print("NOT FOUND:", not_found_folder)