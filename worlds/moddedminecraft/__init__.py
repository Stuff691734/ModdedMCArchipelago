import functools
import json

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
    tutorials = (
        Tutorial(
            "Multiworld Setup Guide",
            "A guide for setting up the Modded Minecraft randomizer connected to Archipelago",
            "English",
            "setup_en.md",
            "setup/en",
            ["Stuff691734"],
        ),
    )
    option_groups = OPTION_GROUPS


class ModdedMinecraftWorld(World):
    game = "Modded Minecraft"

    topology_present = True

    options_dataclass = ModdedMinecraftOptions

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    web = ModdedMinecraftWebWorld()

    filtered_advancements: dict[str:dict] = {}
    filtered_ftb_quests: dict[str:dict] = {}

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

        # =========================================================================================
        # create dicts with values we need instead of using all values
        # also makes later logic easier as dependencies are already considered here
        # TODO: why loop through each list multiple times
        # =========================================================================================

        def recursively_add_advancements(advancement: str):
            # if it is already there, no need to look at it or its dependencies again
            if self.filtered_advancements.get(advancement) is None:
                try:
                    details = self.options.checks["Advancements"][advancement]
                except KeyError:
                    details = {"type": None, "parent_id": [None]}
                self.filtered_advancements.setdefault(advancement, details)
                parent_advancement = details["parent_id"][0]
                if parent_advancement is not None:
                    recursively_add_advancements(parent_advancement)

        if "Advancements" in self.options.activated_modules:
            for advancement, details in self.options.checks["Advancements"].items():
                if self.valid_check_difficulty(details["type"], "Advancements"):
                    recursively_add_advancements(advancement)


        def recursively_add_quests(quest: str):
            # if it is already there, no need to look at it or its dependencies again
            if self.filtered_ftb_quests.get(quest) is None:
                # no longer care if it is a valid check difficulty, just need to make sure it has a path to it
                self.filtered_ftb_quests.setdefault(quest, self.options.checks["FTBQuests"][quest])
                for advancement_id in self.options.checks["FTBQuests"][quest]["advancement_dependencies"]:
                    recursively_add_advancements(advancement_id)

                for parent_id in self.options.checks["FTBQuests"][quest]["parent_id"]:
                    recursively_add_quests(parent_id)
        if "FTBQuests" in self.options.activated_modules:
            for quest, details in self.options.checks["FTBQuests"].items():
                if self.valid_check_difficulty(details["type"], "FTBQuests"):
                    recursively_add_quests(quest)


        # =========================================================================================
        # ensure end goal is in filtered advancements and/or quests
        # =========================================================================================
        goal_type, goal_name = self.options.final_goal.current_key.split(maxsplit=1)
        if goal_type == "adv":
            # same logic as above just changed to start at the goal
            self.filtered_advancements[goal_name] = self.options.checks["Advancements"][goal_name]
            parent_advancement = self.options.checks["Advancements"][goal_name]["parent_id"][0]
            while parent_advancement is not None:
                try:
                    parent_details = self.options.checks["Advancements"][parent_advancement]
                except KeyError:
                    parent_details = {"type": None, "parent_id": [None]}
                self.filtered_advancements[parent_advancement] = parent_details
                parent_advancement = parent_details["parent_id"][0]
        elif goal_type == "ftb":
            recursively_add_quests(goal_name)




    def create_filler(self):
        return self.create_item(f"item {self.get_filler_item_name()}", ItemClassification.filler)

    def get_filler_item_name(self) -> str:
        return self.random.choices(
            list(self.options.filler_items.keys()),
            list(self.options.filler_items.values())
        )[0]

    def create_items(self) -> None:
        total_locations = len(self.multiworld.get_unfilled_locations(self.player))

        item_pool = []
        filler_items = []
        if self.options.unlock_type == UnlockType.option_tab:
            # Advancements Tab Mode
            items: dict[str: ModdedMinecraftItem] = {}
            for name in self.filtered_advancements:
                items.setdefault(
                    self.get_advancement_root(name),
                    self.create_item(f"adv {self.get_advancement_root(name)}")
                )

            if self.options.advancement_checks_give_items:
                for item in self.filtered_advancements:
                    if items.get(item) is None:
                        filler_items.append(self.create_item(f"adv {item}", ItemClassification.filler))

            item_pool += list(items.values())
            # FTB Quests Tab Mode
            items: dict[str:ModdedMinecraftItem] = {}
            for details in self.filtered_ftb_quests.values():
                items.setdefault(details["chapter"], self.create_item(f"ftb {details['chapter']}"))

            if self.options.quest_checks_give_rewards:
                for item in self.filtered_ftb_quests:
                    if items.get(item) is None:
                        filler_items.append(self.create_item(f"ftb {item}", ItemClassification.filler))

            item_pool += list(items.values())

        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            # Advancements Tree Mode
            items: dict[str:ModdedMinecraftItem] = {}
            for check, details in self.filtered_advancements.items():
                parent_id = details["parent_id"][0]
                item_name = check if parent_id is None else parent_id

                items.setdefault(item_name, self.create_item(f"adv {item_name}"))

            if self.options.advancement_checks_give_items:
                for item in self.filtered_advancements:
                    if items.get(item) is None:
                        filler_items.append(self.create_item(f"adv {item}", ItemClassification.filler))

            item_pool += list(items.values())

            # FTB Quests Tree Mode
            items: dict[str:ModdedMinecraftItem] = {}
            for check, details in self.filtered_ftb_quests.items():
                if details["parent_id"] == []:
                    items.setdefault(check, self.create_item(f"ftb {check}"))
                else:
                    for parent_id in details["parent_id"]:
                        items.setdefault(parent_id, self.create_item(f"ftb {parent_id}"))

            if self.options.quest_checks_give_rewards:
                for item in self.filtered_ftb_quests:
                    # reward randomization, should always have enough space
                    if items.get(item) is None:
                        filler_items.append(self.create_item(f"ftb {item}", ItemClassification.filler))

            item_pool += list(items.values())
            if total_locations - len(item_pool) > 0:
                # avoid overfilling filler items
                item_pool += self.random.sample(filler_items, min(len(filler_items), total_locations - len(item_pool)))

        item_pool += [self.create_filler() for _ in range(total_locations - len(item_pool))]

        self.multiworld.itempool += item_pool

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)

        regions = []
        if self.options.unlock_type == UnlockType.option_tab:
            # Advancement Tab Mode
            advancement_regions: dict[str:Region] = {}
            for check, details in self.filtered_advancements.items():
                # if self.valid_check_difficulty(details["type"], "Advancements"):
                name = f"adv {check}"
                region = advancement_regions.setdefault(
                    self.get_advancement_root(check),
                    Region(self.get_advancement_root(check), self.player, self.multiworld),
                )

                if self.valid_check_difficulty(details["type"], "Advancement"):
                    # only add as location if it has a valid difficulty
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
            # TODO: combine with tree style generation to build out tree, just with different conditions
            quest_regions: dict[str:Region] = {}
            for check, details in self.filtered_ftb_quests.items():
                region = quest_regions.setdefault(
                    check, Region(check, self.player, self.multiworld)
                )
                name = f"ftb {check}"
                if self.valid_check_difficulty(details["type"], "FTBQuests"):
                    # only add as location if it has a valid difficulty
                    location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                    region.locations.append(location)

            # TODO: make this one loop
            # with a condition of having the "base" item/check found
            for region in quest_regions.values():
                advancements = []
                if "Advancements" in self.options.activated_modules:
                    dependencies = self.options.checks["FTBQuests"][region.name]["advancement_dependencies"]
                    advancements = [f"adv {self.get_advancement_root(adv_id)}" for adv_id in dependencies]
                connection_conditions = functools.partial(
                    lambda check, advancements, state: state.has_all([check, *advancements], self.player),
                    f"ftb {self.get_ftb_quest_chapter(region.name)}",
                    advancements # most of the time is empty
                )
                parent_ids = self.get_ftb_quest_parent_ids(region.name)
                if parent_ids == []:
                    menu.connect(
                        region,
                        f"menu -> {region.name}",
                        connection_conditions
                    )
                else:
                    for parent_id in parent_ids:
                        parent_region = quest_regions.get(parent_id)
                        parent_region.connect(
                            region,
                            f"{parent_region.name} -> {region.name}",
                            connection_conditions
                        )
            regions += list(quest_regions.values())

        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            # Advancements Tree Mode
            advancement_regions: dict[str:Region] = {}
            for check, details in self.filtered_advancements.items():
                parent_id = details["parent_id"][0]
                name = f"adv {check}"
                advancement_id = parent_id if parent_id is not None else check

                region = advancement_regions.setdefault(
                    advancement_id,
                    Region(advancement_id, self.player, self.multiworld),
                )
                if self.valid_check_difficulty(details["type"], "Advancements"):
                    # only add as location if it has a valid difficulty
                    location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                    region.locations.append(location)
            for region in advancement_regions.values():
                # base of advancement tree
                parent_id = self.get_advancement_parent_id(region.name)
                if parent_id is None:
                    menu.connect(
                        region,
                        f"menu -> {region.name}",
                        lambda state, name=region.name: state.has(f"adv {name}", self.player),
                    )
                else:
                    parent_region = advancement_regions[parent_id]
                    parent_region.connect(
                        region,
                        f"{parent_region.name} -> {region.name}",
                        lambda state, name=region.name: state.has(f"adv {name}", self.player),
                    )
            regions += list(advancement_regions.values())
            # FTB Quests Tree Mode
            quest_regions: dict[str:Region] = {}
            for check, details in self.filtered_ftb_quests.items():
                region = quest_regions.setdefault(
                    check, Region(check, self.player, self.multiworld)
                )
                name = f"ftb {check}"
                if self.valid_check_difficulty(details["type"], "FTBQuests"):
                    # only add as location if it has a valid difficulty
                    location = ModdedMinecraftLocation(self.player, name, self.location_name_to_id[name], region)
                    region.locations.append(location)

            condition = {
                "all_completed": lambda parents, state: state.has_all(parents, self.player),
                "one_completed": lambda parents, state: state.has_any(parents, self.player),
                "all_started": lambda parents, state: state.has_all(parents, self.player),
                "one_started": lambda parents, state: state.has_any(parents, self.player)
            }

            for region in quest_regions.values():
                parent_ids = self.get_ftb_quest_parent_ids(region.name)
                required_checks = [f"ftb {parent_id}" for parent_id in parent_ids]

                if "Advancements" in self.options.activated_modules:
                    # only have advancements as dependencies if randomizing advancements
                    for advancement_id in self.options.checks["FTBQuests"][region.name]["advancement_dependencies"]:
                        required_checks += [f"adv {self.get_advancement_parent_id(advancement_id) or advancement_id}"]

                if parent_ids == []:
                    menu.connect(
                        region,
                        f"menu -> {region.name}",
                        lambda state, name=region.name: state.has(f"ftb {name}", self.player),
                    )
                else:
                    dependent_type = self.options.checks["FTBQuests"][region.name]["dependant_type"]

                    connection_conditions = functools.partial(
                        condition[dependent_type],
                        required_checks
                    )

                    if len(parent_ids) >= 2 and dependent_type in ["all_completed", "all_started"]:
                        # connection_conditions = lambda parents, state: state.has_all(parents, self.player)
                        def region_condition(base_condition, regions, state) -> bool:
                            return base_condition(state) and all(
                                state.can_reach_region(region, self.player) for region in regions
                            )

                        connection_conditions = functools.partial(
                            region_condition,
                            connection_conditions,
                            parent_ids
                        )
                        entrances = []
                        regions_to_connect = []

                        for parent_id in parent_ids:
                            parent_region = quest_regions.get(parent_id)
                            regions_to_connect.append(parent_region)
                            entrances.append(parent_region.connect(
                                region,
                                f"{parent_region.name} -> {region.name}",
                                connection_conditions
                            ))
                        for entrance in entrances:
                            for region_to_connect in regions_to_connect:
                                self.multiworld.register_indirect_condition(region_to_connect, entrance)
                    else:
                        for parent_id in parent_ids:
                            parent_region = quest_regions.get(parent_id)
                            parent_region.connect(
                                region,
                                f"{parent_region.name} -> {region.name}",
                                connection_conditions
                            )

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
            "ftb_quest_check_shape",
            "advancement_checks_give_items",
            "quest_checks_give_rewards"
        )
        options["activated_modules"] = "|".join(options["activated_modules"])
        options["advancement_check_difficulty"] = "|".join(options["advancement_check_difficulty"])
        options["ftb_quest_check_shape"] = "|".join(options["ftb_quest_check_shape"])

        return options

    def set_rules(self) -> None:
        goal_type, goal_name = self.options.final_goal.current_key.split(maxsplit=1)
        if self.options.unlock_type == UnlockType.option_tab:
            if goal_type == "adv":
                goal = f"adv {self.get_advancement_root(goal_name)}"
                self.multiworld.completion_condition[self.player] = (
                    lambda state: state.has(goal, self.player) and
                    state.can_reach_region(self.get_advancement_root(goal_name), self.player)
                )
            elif goal_type == "ftb":
                details = self.filtered_ftb_quests[goal_name]
                goal = f"ftb {self.get_ftb_quest_chapter(goal_name)}"
                self.multiworld.completion_condition[self.player] = lambda state: state.has(goal, self.player) and all(
                        state.can_reach_region(region, self.player) for region in details["parent_id"]
                    )
        elif self.options.unlock_type == self.options.unlock_type.option_tree:
            if goal_type == "adv":
                goal_name = self.get_advancement_parent_id(goal_name) or goal_name
                goal = f"adv {goal_name}"
                self.multiworld.completion_condition[self.player] = (
                    lambda state: state.has(goal, self.player) and
                    state.can_reach_region(goal_name, self.player)
                )
            elif goal_type == "ftb":
                details = self.filtered_ftb_quests[goal_name]
                parent_ids = [f"ftb {parent_id}" for parent_id in details["parent_id"]]
                condition = {
                    "all_completed": lambda state: state.has_all(parent_ids, self.player) and all(
                        state.can_reach_region(region, self.player) for region in details["parent_id"]
                    ),
                    "one_completed": lambda state: state.has_any(parent_ids, self.player) and any(
                        state.can_reach_region(region, self.player) for region in details["parent_id"]
                    ),
                    "all_started": lambda state: state.has_all(parent_ids, self.player) and all(
                        state.can_reach_region(region, self.player) for region in details["parent_id"]
                    ),
                    "one_started": lambda state: state.has_any(parent_ids, self.player) and any(
                        state.can_reach_region(region, self.player) for region in details["parent_id"]
                    )
                }
                self.multiworld.completion_condition[self.player] = condition[details["dependant_type"]]

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
        except KeyError:
            # missing advancement (possibly advancement has no display but is still a dependency)
            return None

    def get_ftb_quest_parent_ids(self, item: str) -> list[str]:
        return self.options.checks["FTBQuests"][item]["parent_id"]

    def valid_check_difficulty(self, check_difficulty: str, check_type: str) -> bool:
        if check_type == "Advancements":
            return (
                check_difficulty in self.options.advancement_check_difficulty
                    and "Advancements" in self.options.activated_modules
                )
        if check_type == "FTBQuests":
            return (
                check_difficulty in self.options.ftb_quest_check_shape
                    and "FTBQuests" in self.options.activated_modules
                )
        # not sure what would hit this, for now we just ignore it
        return False
