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
from file_constants import *
import subprocess

PREPROCESS_CMD = "node"
PREPROCESS_ARGS = ["./nodejs/build_dexes.mjs"]

STATS_URL = "https://www.smogon.com/stats/"


def update():
    """Do whole update procedure.

    Delete existing files, download new ones, preprocess and validate.
    """
    print("Update started.")
    _download_data()
    print("Data downloaded.")

    format_playstats = {}
    format_ratings = {}

    for file in os.scandir(TEMP_DATA_DIR):
        try:
            threat_filename = file.path[:-5] + THREAT_FILE
            teammate_filename = file.path[:-5] + TEAMMATE_FILE
            format_name, times_played = \
                preprocess.prepare_files(file, threat_filename, teammate_filename)

            # Files are named like gen8ou-1500.json
            rating = file.name[:-5].split("-")[1]

            if format_name not in format_playstats:
                # Times played data is same for all ratings.
                format_playstats[format_name] = times_played
                format_ratings[format_name] = [rating]
            else:
                format_ratings[format_name].append(rating)
            print(file.name + " is valid.")
        except AssertionError as e:
            os.remove(file)
            print(file.name + " failed validation: " + str(e))

    top_formats = sorted(format_playstats,
                         key=format_playstats.get, reverse=True)[:10]

    with open(TEMP_DATA_DIR + TOP_FORMATS_FILE,
              "w", encoding="utf-8") as top_formats_fd:
        for form in top_formats:
            line = form + " " + ",".join(sorted(format_ratings[form])) + "\n"
            top_formats_fd.write(line)

    print("Running script preprocessing.")
    subprocess.call([PREPROCESS_CMD] + PREPROCESS_ARGS)

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

    chaos_url = STATS_URL + last_update + "chaos/"
    chaos_page = requests.get(chaos_url)

    if not os.path.isdir(TEMP_DATA_DIR):
        os.mkdir(TEMP_DATA_DIR)
    else:
        for file in os.scandir(TEMP_DATA_DIR):
            os.remove(file)

    for metagame in re.findall(r'<a href="(.*)"', chaos_page.text)[1:]:
        meta_url = chaos_url + metagame
        req = requests.get(meta_url)
        with open(TEMP_DATA_DIR + metagame, "wb") as metagame_fd:
            for chunk in req.iter_content(chunk_size=128):
                metagame_fd.write(chunk)
