"""Downloads and processes data from Smogon.

This module is responsible for downloading metagame data from Smogon.
It also ensures that the data is preprocessed and validated.
The actual mechanics of that preprocessing and validation exist elsewhere.
"""

import os
import re
import requests
import boto3
import preprocess
from build_speed_tiers import build_speed_tiers
from file_constants import *
import subprocess
from datetime import datetime

STATS_URL = "https://www.smogon.com/stats/"


def update():
    """Do whole update procedure.

    Delete existing files, download new ones, preprocess and validate.
    """
    print("Update started.")
    date = _download_data()
    print("Data downloaded.")

    format_playstats = {}
    format_counters = {}
    format_ratings = {}

    for file in sorted(os.scandir(TEMP_DATA_DIR), key=lambda f: f.name):  # Sort so we always start with 0 rating.
        try:
            # Files are named like gen8ou-1500.json
            rating = file.name[:-5].split("-")[1]
            raw_counters_filename = file.path.rsplit("-", 1)[0] + TEMP_COUNTERS_FILE

            # Doubles formats don't have good checks/counters data, but it's sometimes included in the raw data.
            if "doubles" not in file.name and "vgc" not in file.name:
                if rating == "0":  # We share counters data across ratings, and 0 rating has the most data.
                    preprocess.raw_counters(file, raw_counters_filename)

            threat_filename = file.path[:-5] + THREAT_FILE
            teammate_filename = file.path[:-5] + TEAMMATE_FILE
            format_name, times_played, has_counters = \
                preprocess.prepare_files(file, raw_counters_filename, threat_filename, teammate_filename)

            if format_name not in format_playstats:
                # Number of times played and the existence of counters is same for all ratings.
                format_playstats[format_name] = times_played
                format_counters[format_name] = has_counters
                format_ratings[format_name] = [rating]
            else:
                format_ratings[format_name].append(rating)

            print(file.name + " is valid.")
        except preprocess.ValidationError as e:
            os.remove(file)
            print(file.name + " failed validation: " + str(e))

    with open(TEMP_DATA_DIR + DATE_FILE, "w", encoding="utf-8") as date_fd:
        date_fd.write(date)

    top_formats = sorted(format_playstats, key=format_playstats.get, reverse=True)
    with open(TEMP_DATA_DIR + FORMATS_FILE, "w", encoding="utf-8") as top_formats_fd:
        for form in top_formats:
            line = form + " " + str(format_playstats[form]) + " "
            line += "C " if format_counters[form] else "N "
            rating_strings = sorted(format_ratings[form], key=lambda k: k[0])
            line += ",".join(rating_strings) + "\n"
            top_formats_fd.write(line)

    print("Building dexes.")
    subprocess.run(["npm", "install", "@pkmn/dex"], shell=True).check_returncode()
    subprocess.run(["node", "./nodejs/build_dexes.mjs"]).check_returncode()

    print("Building speed tiers.")
    build_speed_tiers()

    for file in os.scandir(TEMP_DATA_DIR):
        if file.name.endswith(TEMP_COUNTERS_FILE):
            os.remove(file)

    if os.path.isdir(DATA_DIR):
        for file in os.scandir(DATA_DIR):
            os.remove(file)
        os.rmdir(DATA_DIR)
    os.rename(TEMP_DATA_DIR, DATA_DIR)

    print("Clearing old files.")
    session = boto3.session.Session(aws_access_key_id=os.environ["S3_ACCESS_KEY"],
                                    aws_secret_access_key=os.environ["S3_SECRET_KEY"])
    bucket = session.resource("s3", endpoint_url=os.environ["S3_ENDPOINT"]).Bucket(os.environ["BUCKET"])
    bucket.objects.all().delete()
    print("Uploading.")
    for file in os.scandir(DATA_DIR):
        bucket.upload_file(file.path, file.name)

    print("Update complete!")


def _download_data():
    """Downloads the new data from Smogon."""
    stats_page = requests.get(STATS_URL)

    last_update = re.findall(r'<a href="(.*)"', stats_page.text)[-1]
    last_update_date = datetime.strptime(last_update, "%Y-%m/").strftime("%B %Y")
    chaos_url = STATS_URL + last_update + "chaos/"
    chaos_page = requests.get(chaos_url)

    if not os.path.isdir(TEMP_DATA_DIR):
        os.mkdir(TEMP_DATA_DIR)
    else:
        for file in os.scandir(TEMP_DATA_DIR):
            os.remove(file)

    # First link is just to go back, so we skip that.
    for metagame in re.findall(r'<a href="(.*)"', chaos_page.text)[1:]:
        meta_url = chaos_url + metagame
        req = requests.get(meta_url)
        with open(TEMP_DATA_DIR + metagame, "wb") as metagame_fd:
            for chunk in req.iter_content(chunk_size=128):
                metagame_fd.write(chunk)

    return last_update_date
