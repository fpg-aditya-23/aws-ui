import subprocess
import sys
import os

from .downloader import download_data
from .fosse_sort import run_fosse_sort   # ✅ direct function call

def run_marriott(location, date_input, base_path, logger):

    logger("🚀 Marriott Process Started")

    try:
        # =========================
        # STEP 1: DOWNLOAD + ZIP
        # =========================

        zip_path = download_data(location, date_input, base_path, logger)

        if not zip_path:
            logger("❌ No ZIP created. Stopping.")
            return

        logger(f"📦 ZIP Ready: {zip_path}")

        # =========================
        # STEP 2: SORT EMAILS
        # =========================

        run_fosse_sort(zip_path, base_path, date_input)

        logger("✅ Sorting Completed")

    except Exception as e:
        logger(f"❌ Error: {e}")