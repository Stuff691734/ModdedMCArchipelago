from worlds.AutoWorld import World, WebWorld
from BaseClasses import Item, Location, ItemClassification, Region, CollectionState, Tutorial
import json

from .options import ModdedMinecraftOptions, UnlockType, CheckDifficulty, OPTION_GROUPS
from worlds.LauncherComponents import Component, components, Type, launch as launch_component
from .Locations import location_name_to_id, item_name_to_id
from Utils import user_path


class ModdedMinecraftLocation(Location):
    game = "Modded Minecraft"

class ModdedMinecraftItem(Item):
    game = "Modded Minecraft"


class ModdedMinecraftWebWorld(WebWorld):
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide for setting up the Modded Minecraft randomizer connected to Archipelago",
        "English",
        "setup_en.md",
        "setup/en",
        ["Stuff691734"]
    )]
    option_groups = OPTION_GROUPS


class ModdedMinecraftWorld(World):
    game = "Modded Minecraft"
    
    topology_present = True

    options_dataclass = ModdedMinecraftOptions

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    web = ModdedMinecraftWebWorld()

    def generate_early(self) -> None:
        # get data from checks file
        fileName = user_path("ModdedMinecraftDataFile.json")
        try:
            with open(fileName) as file:
                checks:dict[str, int] = json.load(file)

        except (json.JSONDecodeError, FileNotFoundError):
            checks:dict[str, int] = {}

        defaultItems = ["1 minecraft:iron_ingot"]

        # TODO: keep as dict and make it add as next id
        def addItem(item, outList:list):
            if outList.count(item) == 0:
                outList.append(item)

        updated_checks = list(checks)
        for item in defaultItems:
            addItem(item, updated_checks)

        for item in self.options.checks.keys():
            addItem(item, updated_checks)

        checks = {check: i+6 for i, check in enumerate(updated_checks)}
        with open(fileName, "w") as file:
            json.dump(checks, file)

        self.item_name_to_id = checks
        self.location_name_to_id = checks
    
    def create_filler(self):
        return self.create_item("1 minecraft:iron_ingot", ItemClassification.filler)

    def get_filler_item_name(self) -> str:
        return "1 minecraft:iron_ingot"


    def create_items(self) -> None:
        total_locations = len(self.multiworld.get_unfilled_locations(self.player))
        item_pool = []
        items = {}
        if self.options.unlock_type == UnlockType.option_tab:
            for name, details in self.options.checks.items():
                if details["parent_id"] == None:
                    item_pool += [self.create_item(name)]

        if self.options.unlock_type == UnlockType.option_tree:
            # create all items that are not the direct end of a branch
            items = {}
            for details in self.options.checks.values():
                if details["parent_id"] != None:
                    items.setdefault(
                        details["parent_id"], 
                        self.create_item(details["parent_id"])
                    )

            item_pool += [item for item in items.values()]

        for i in range(total_locations - len(item_pool)):
            item_pool.append(self.create_filler())

        self.multiworld.itempool += item_pool

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        regions:dict[str:Region] = {}
        for name, details in self.options.checks.items():
            if self.options.unlock_type == self.options.unlock_type.option_tab:
                region = regions.setdefault(
                    self.get_root(name), 
                    Region(self.get_root(name), self.player, self.multiworld)
                )

            elif self.options.unlock_type == self.options.unlock_type.option_tree:
                if details["parent_id"] != None:
                    region = regions.setdefault(
                        details["parent_id"], 
                        Region(details["parent_id"], self.player, self.multiworld)
                    )

            if (self.options.check_difficulty == CheckDifficulty.option_normal and details["type"] == "task") or \
                    (self.options.check_difficulty == CheckDifficulty.option_goal and details["type"] != "challenge") or \
                        self.options.check_difficulty == CheckDifficulty.option_challenge:
                # task on normal, task+goal on goal, everything on challenge
                location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                region.locations.append(location)

        for region in regions.values():
            if self.options.unlock_type == self.options.unlock_type.option_tab:
                menu.connect(
                    region, 
                    f"menu -> {region.name}", 
                    lambda state, name=region.name: state.has(name, self.player)
                )
            elif self.options.unlock_type == self.options.unlock_type.option_tree:
                # connect regions sequentially
                if self.get_parent_id(region.name) == None:
                    menu.connect(
                        region, 
                        f"menu -> {region.name}", 
                        lambda state, name=region.name: state.has(name, self.player)
                    )
                else:
                    # menu.connect(region, f"menu -> {region.name}", lambda state, name=region.name: state.has(name, self.player))
                    parent_region = regions[self.get_parent_id(region.name)]
                    parent_region.connect(
                        region, 
                        f"{parent_region.name} -> {region.name}", 
                        lambda state, name=region.name: state.has(name, self.player)
                    )
        
        self.multiworld.regions += [i for i in regions.values()]  + [menu]

    def fill_slot_data(self):
        slot_data = {**self.options.as_dict(
            "final_goal", 
            "unlock_type",
            "death_link"
            )}
        return slot_data

    def set_rules(self) -> None:
        if self.options.unlock_type == self.options.unlock_type.option_tab:
            goal = self.get_root(self.options.final_goal.current_key)
        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            goal = self.get_parent_id(self.options.final_goal.current_key) or self.options.final_goal.current_key
        
        self.multiworld.completion_condition[self.player] = lambda state, goal=goal: state.has(goal, self.player)
    
    def create_item(self, name: str, classification:ItemClassification = ItemClassification.progression) -> ModdedMinecraftItem:
        return ModdedMinecraftItem(name, classification, self.location_name_to_id[name], self.player)
    
    def get_root(self, item: str) -> str:
        if self.get_parent_id(item) == None:
            return item
        try:
            return self.get_root(self.get_parent_id(item))
        except KeyError:
            return item

    def get_parent_id(self, item: str) -> str|None:
        return self.options.checks[item]["parent_id"]