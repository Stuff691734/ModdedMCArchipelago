import json
import logging

from BaseClasses import Item, ItemClassification, Location, Region, Tutorial
from Utils import user_path
from worlds.AutoWorld import WebWorld, World

from .locations import item_name_to_id, location_name_to_id
from .options import OPTION_GROUPS, ModdedMinecraftOptions, UnlockType


class ModdedMinecraftLocation(Location):
    game = "Modded Minecraft"


class ModdedMinecraftItem(Item):
    game = "Modded Minecraft"


class ModdedMinecraftWebWorld(WebWorld):
    tutorials = [
        Tutorial(
            "Multiworld Setup Guide",
            "A guide for setting up the Modded Minecraft randomizer connected to Archipelago",
            "English",
            "setup_en.md",
            "setup/en",
            ["Stuff691734"],
        )
    ]
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
        file_name = user_path("ModdedMinecraftDataFile.json")
        try:
            with open(file_name, encoding="utf-8") as file:
                checks: list[str] = list(json.load(file))

        except (json.JSONDecodeError, FileNotFoundError):
            checks: list[str] = []

        # default_items = ["1 minecraft:iron_ingot"]

        def add_item(item, out_list: list):
            if out_list.count(item) == 0:
                out_list.append(item)

        for item in self.options.filler_items:
            add_item(f"item {item}", checks)

        for advancement, parent in self.options.checks["Advancements"].items():
            add_item(f"adv {advancement}", checks)
            # needed since sometimes dependencies don't always have displays
            # therefore aren't picked up by the generator
            add_item(f"adv {parent['parent_id'][0]}", checks)


        for quest, details in self.options.checks["FTBQuests"].items():
            add_item(f"ftb {quest}", checks)
            add_item(f"ftb {details['chapter']}", checks)
            for dependency in details["parent_id"]:
                add_item(f"ftb {dependency}", checks)


        checks = {check: i + 6 for i, check in enumerate(checks)}
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump(checks, file)

        self.item_name_to_id = checks
        self.location_name_to_id = checks


    def create_filler(self):
        return self.create_item(f"item {self.get_filler_item_name()}", ItemClassification.filler)

    def get_filler_item_name(self) -> str:
        return self.random.choice(list(self.options.filler_items))

    def create_items(self) -> None:
        total_locations = len(self.multiworld.get_unfilled_locations(self.player))
        item_pool = []
        if self.options.unlock_type == UnlockType.option_tab:
            # Advancements Tab Mode
            if "Advancements" in self.options.activated_modules:
                root_items: dict[str: ModdedMinecraftItem] = {}
                for name in self.options.checks["Advancements"]:
                    root_items.setdefault(
                        self.get_advancement_root(name),
                        self.create_item(f"adv {self.get_advancement_root(name)}")
                    )
                item_pool += list(root_items.values())
            # FTB Quests Tab Mode
            if "FTBQuests" in self.options.activated_modules:
                items: dict[str:ModdedMinecraftItem] = {}
                for details in self.options.checks["FTBQuests"].values():
                    items.setdefault(details["chapter"], self.create_item(f"ftb {details['chapter']}"))
                item_pool += list(items.values())

        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            # Advancements Tree Mode
            if "Advancements" in self.options.activated_modules:
                items: dict[str:ModdedMinecraftItem] = {}
                for check, details in self.options.checks["Advancements"].items():
                    if self.valid_check_difficulty(details["type"], "Advancements"):
                        parent_id = self.get_advancement_parent_id(check)
                        if parent_id is not None:
                            items.setdefault(parent_id, self.create_item(f"adv {parent_id}"))
                        else:
                            # this is really only nescessary if there is a root advancement with no dependencies
                            # extradisks I am looking at you
                            items.setdefault(check, self.create_item(f"adv {check}"))
                item_list = list(items)
                for item in item_list:
                    dependency = self.get_advancement_parent_id(item)
                    while dependency is not None and items.get(dependency) is None:
                        # dependency exists but isn't in the list of items yet
                        item_list.append(dependency)
                        items.setdefault(dependency, self.create_item(f"adv {dependency}"))
                        dependency = self.get_advancement_parent_id(item)
                item_pool += list(items.values())

            # FTB Quests Tree Mode
            if "FTBQuests" in self.options.activated_modules:
                items: dict[str:ModdedMinecraftItem] = {}
                for check, details in self.options.checks["FTBQuests"].items():
                    if self.valid_check_difficulty(details["type"], "FTBQuests"):
                        items.setdefault(check, self.create_item(f"ftb {check}"))
                for item in items:
                    self.add_ftb_quest_items(item, items)
                item_pool += list(items.values())

        for _ in range(total_locations - len(item_pool)):
            item_pool.append(self.create_filler())

        self.multiworld.itempool += item_pool

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)

        regions = []
        if self.options.unlock_type == UnlockType.option_tab:
            # Advancement Tab Mode
            if "Advancements" in self.options.activated_modules:
                advancement_regions: dict[str:Region] = {}
                for check, details in self.options.checks["Advancements"].items():
                    if self.valid_check_difficulty(details["type"], "Advancements"):
                        name = f"adv {check}"
                        region = advancement_regions.setdefault(
                            self.get_advancement_root(check),
                            Region(self.get_advancement_root(check), self.player, self.multiworld),
                        )
                        location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                        region.locations.append(location)
                for region in advancement_regions.values():
                    menu.connect(
                        region,
                        f"menu -> {region.name}",
                        lambda state, name=region.name: state.has(f"adv {name}", self.player)
                    )
                regions += list(advancement_regions.values())

            # FTB Quests Tab Mode
            if "FTBQuests" in self.options.activated_modules:
                quest_regions: dict[str:Region] = {}
                for check, details in self.options.checks["FTBQuests"].items():
                    if self.valid_check_difficulty(details["type"], "FTBQuests"):
                        region = quest_regions.setdefault(
                            details["chapter"], Region(details["chapter"], self.player, self.multiworld)
                        )
                        name = f"ftb {check}"
                        location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                        region.locations.append(location)
                # using tab unlock type we just connect everything to menu
                # with a condition of having the "base" item/check found
                for region in quest_regions.values():
                    if self.options.unlock_type == UnlockType.option_tab:
                        menu.connect(
                            region,
                            f"menu -> {region.name}",
                            lambda state, name=region.name: state.has(f"ftb {name}", self.player)
                        )
                regions += list(quest_regions.values())

        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            # Advancements Tree Mode
            if "Advancements" in self.options.activated_modules:
                advancement_regions: dict[str:Region] = {}
                for check, details in self.options.checks["Advancements"].items():
                    parent_id = self.get_advancement_parent_id(check)
                    name = f"adv {check}"
                    if self.valid_check_difficulty(details["type"], "Advancements") and parent_id is not None:
                        region = advancement_regions.setdefault(
                            parent_id,
                            Region(parent_id, self.player, self.multiworld),
                        )
                        location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                        region.locations.append(location)
                    elif self.valid_check_difficulty(details["type"], "Advancements") and parent_id is None:
                        region = advancement_regions.setdefault(
                            check,
                            Region(check, self.player, self.multiworld),
                        )
                        location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                        region.locations.append(location)
                for region in advancement_regions.values():
                    # base of advancement tree
                    if self.get_advancement_parent_id(region.name) is None:
                        menu.connect(
                            region,
                            f"menu -> {region.name}",
                            lambda state, name=region.name: state.has(f"adv {name}", self.player),
                        )
                    else:
                        parent_region = advancement_regions.get(self.get_advancement_parent_id(region.name))
                        if parent_region is None:
                            # can't find next up tree, presumably a difficulty that is not included
                            # we need to create these as not being there would leave checks inaccesible.
                            old_region = region
                            while parent_region is not None:
                                parent_region = advancement_regions.setdefault(
                                    Region(
                                        self.get_advancement_parent_id(old_region.name), self.player, self.multiworld
                                    )
                                )
                                parent_region.connect(
                                    old_region,
                                    f"{parent_region.name} -> {old_region.name}",
                                    lambda state, name=old_region.name: state.has(f"adv {name}", self.player),
                                )
                                old_region = parent_region
                                parent_region = advancement_regions.get(self.get_advancement_parent_id(old_region.name))
                        else:
                            parent_region.connect(
                                region,
                                f"{parent_region.name} -> {region.name}",
                                lambda state, name=region.name: state.has(f"adv {name}", self.player),
                            )
                regions += list(advancement_regions.values())
            # FTB Quests Tree Mode
            if "FTBQuests" in self.options.activated_modules:
                quest_regions: dict[str:Region] = {}
                for check, details in self.options.checks["FTBQuests"].items():
                    if self.valid_check_difficulty(details["type"], "FTBQuests"):
                        region = quest_regions.setdefault(
                            check, Region(check, self.player, self.multiworld)
                        )
                        name = f"ftb {check}"
                        location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                        region.locations.append(location)

                # logically connect back to the base
                for region in quest_regions.values():
                    self.connect_ftb_quests_parent_region(quest_regions, region, menu)

                regions += list(quest_regions.values())
        # all region generation finished add to multiworld regions
        self.multiworld.regions += [*regions, menu]

    def fill_slot_data(self):
        options = self.options.as_dict(
            "final_goal",
            "unlock_type",
            "death_link",
            "activated_modules",
            "advancement_check_difficulty",
            "ftb_quest_check_shape"
        )
        options["activated_modules"] = "|".join(options["activated_modules"])
        options["advancement_check_difficulty"] = "|".join(options["advancement_check_difficulty"])
        options["ftb_quest_check_shape"] = "|".join(options["ftb_quest_check_shape"])

        return options

    def set_rules(self) -> None:
        goal = None
        goal_type, goal_name = self.options.final_goal.current_key.split(maxsplit=1)
        if self.options.unlock_type == UnlockType.option_tab:
            if goal_type == "adv":
                goal = f"adv {self.get_advancement_root(goal_name)}"
            elif goal_type == "ftb":
                goal = f"ftb {self.get_ftb_quest_chapter(goal_name)}"
        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            if goal_type == "adv":
                goal = f"adv {self.get_advancement_parent_id(goal_name) or goal_name}"
            elif goal_type == "ftb":
                goal = f"ftb {self.get_ftb_quest_parent_id(goal_name)}"
        if goal is not None:
            self.multiworld.completion_condition[self.player] = lambda state, goal=goal: state.has(goal, self.player)

    def create_item(
        self,
        name: str,
        classification: ItemClassification = ItemClassification.progression
    ) -> ModdedMinecraftItem:
        return ModdedMinecraftItem(name, classification, self.location_name_to_id[name], self.player)

    def get_advancement_root(self, item: str) -> str:
        if self.get_advancement_parent_id(item) is None:
            return item
        return self.get_advancement_root(self.get_advancement_parent_id(item))

    def get_ftb_quest_chapter(self, item: str) -> str:
        return self.options.checks["FTBQuests"][item]["chapter"]

    def get_advancement_parent_id(self, item: str) -> str|None:
        try:
            return self.options.checks["Advancements"][item]["parent_id"][0]
        except KeyError as ex:
            logging.warning(
                "missing advancement (possibly advancement has no display but is still a dependency): %s",
                ex
                )
            return None

    def get_ftb_quest_parent_id(self, item: str) -> list[str]:
        return self.options.checks["FTBQuests"][item]["parent_id"]

    def connect_ftb_quests_parent_region(self, regions: dict[str:Region], region: Region, menu: Region):
        parent_ids = self.get_ftb_quest_parent_id(region.name)
        if parent_ids == []:
            menu.connect(
                region,
                f"menu -> {region.name}",
                lambda state, name=region.name: state.has(f"ftb {name}", self.player),
            )
        dependencies = [f"ftb {parent_id}" for parent_id in parent_ids]
        for parent_region_name in parent_ids:
            condition = {
                "all_completed":lambda state, name=region.name: state.has_all(dependencies, self.player),
                "one_completed":lambda state, name=region.name: state.has_any(dependencies, self.player),
                "all_started":lambda state, name=region.name: state.has_all(dependencies, self.player),
                "one_started":lambda state, name=region.name: state.has_any(dependencies, self.player)
            }

            parent_region = regions.get(parent_region_name)
            if parent_region is None:
                # dependency doesn't exist
                parent_region = regions.setdefault(
                    parent_region_name,
                    Region(parent_region_name, self.player, self.multiworld)
                )
                parent_region.connect(
                    region,
                    f"{parent_region.name} -> {region.name}",
                    condition[self.options.checks["FTBQuests"][region.name]["dependant_type"]]
                )

                self.connect_ftb_quests_parent_region(regions, parent_region, menu)

            else:
                # dependency already exists, simple
                parent_region.connect(
                    region,
                    f"{parent_region.name} -> {region.name}",
                    condition[self.options.checks["FTBQuests"][region.name]["dependant_type"]]
                )
    def add_ftb_quest_items(self, item: str, items: dict[str:Item]):
        if items.get(item) is None:
            items.setdefault(item, self.create_item(f"ftb {item}"))
            for dependency in self.get_ftb_quest_parent_id(item):
                self.add_ftb_quest_items(dependency, items)

    def valid_check_difficulty(self, check_difficulty: str, check_type: str) -> bool:
        if check_type == "Advancements":
            return check_difficulty in self.options.advancement_check_difficulty
        if check_type == "FTBQuests":
            return check_difficulty in self.options.ftb_quest_check_shape
        # not sure what would hit this, for now we just ignore it
        return False
