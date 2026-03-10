import json

from Utils import user_path

location_name_to_id = {}
item_name_to_id = {}
try:
    with open(user_path("ModdedMinecraftDataFile.json")) as file:
        json_data = json.load(file)
        location_name_to_id = json_data
        item_name_to_id = json_data

except FileNotFoundError:
    with open(user_path("ModdedMinecraftDataFile.json"), "x") as file:
        file.write("{}")
