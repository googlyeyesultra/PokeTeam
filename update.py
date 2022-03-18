import os
import analyze
import requests
import re

def update():
  stats_url = "https://www.smogon.com/stats/"
  data_dir = "./datasets/"
  temp_data_dir = "./datasets_temp/"
  top_formats_file = "top_formats"

  if os.path.isdir(data_dir):
    for file in os.scandir(data_dir):
      os.remove(file)
    os.rmdir(data_dir)

  stats_page = requests.get(stats_url)

  last_update = re.findall(r'\<a href="(.*)"', stats_page.text)[-1]

  chaos_url = stats_url + last_update + "chaos/"
  chaos_page = requests.get(chaos_url)

  if not os.path.isdir(temp_data_dir):
    os.mkdir(temp_data_dir)
  else:
    for file in os.scandir(temp_data_dir):
      os.remove(file)

  for metagame in re.findall(r'\<a href="(.*)"', chaos_page.text)[1:]:
    meta_url = chaos_url + metagame
    r = requests.get(meta_url)
    with open(temp_data_dir + metagame, "wb") as fd:
      for chunk in r.iter_content(chunk_size=128):
        fd.write(chunk)

  print("Data downloaded.")

  format_playstats = {}
  format_ratings = {}

  for file in os.scandir(temp_data_dir):
    try:
      threat_filename = file.path[:-5] + "_threats.npy"
      format_name, times_played = analyze.MetagameData.prepare_files(file, threat_filename)
      if format_name not in format_playstats:
        format_playstats[format_name] = times_played # Times played data is same for all ratings.
        format_ratings[format_name] = [file.name[:-5].split("-")[1]]
      else:
        format_ratings[format_name].append(file.name[:-5].split("-")[1])
      print(file.name + " is valid.")
    except AssertionError:
      os.remove(file)
      print(file.name + " failed validation.")

  top_formats = sorted(format_playstats, key=format_playstats.get, reverse=True)[:10]

  with open(temp_data_dir + top_formats_file, "w") as fd:
    for f in top_formats:
      line = f + " " + ",".join(sorted(format_ratings[f])) + "\n"
      fd.write(line)
  
  print("Update complete!")

  os.rename(temp_data_dir, data_dir)