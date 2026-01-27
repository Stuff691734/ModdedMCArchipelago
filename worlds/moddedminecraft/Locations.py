import json
from Utils import user_path

location_name_to_id = {}
item_name_to_id = {}
try:
    with open(user_path("ModdedMinecraftDataFile.json")) as file:
        jsonData = json.load(file)
        location_name_to_id = jsonData
        item_name_to_id = jsonData

except FileNotFoundError:
    with open(user_path("ModdedMinecraftDataFile.json"), "x") as file:
        file.write("{}")

except Exception as e:
    print(e)
