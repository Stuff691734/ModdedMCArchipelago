import json
from enum import StrEnum
import logging
import re

from BaseClasses import Item, ItemClassification, Location, Region, Tutorial
from Utils import user_path
from worlds.AutoWorld import WebWorld, World
from Options import OptionError

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

class CheckType(StrEnum):
    ADVANCEMENT = "adv"
    FTB_QUESTS = "ftb"


class ModdedMinecraftWorld(World):
    game = "Modded Minecraft"

    topology_present = True

    options_dataclass = ModdedMinecraftOptions

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id

    web = ModdedMinecraftWebWorld()

    # this exists to protect against edge cases in dependencies that use a minimum, where a situation where the user
    # can access region A but and has item from region B
    # and region C has a dependency for (A and B) with a minimum of 1
    # I don't like having to do this and kinda hope there's a smarter way to do this
    # but I didn't like how I was working around it previously (and it would be hard to add here)
    explicit_indirect_conditions = False


    def __init__(self, multiworld, player):
        self.filtered_checks: dict[str:dict] = {}
        super().__init__(multiworld, player)

    def generate_early(self) -> None:
        if not self.options.roots_unlocked and \
            len(self.options.start_inventory.items()) == 0 and \
            len(self.multiworld.game) == 1:
            # have an actual error instead of just having generation fail
            raise OptionError("This game has no starting items. Some possible solutions are to turn on "
            "starting with roots, add an item to start inventory or generate with another game")
        if self.options.checks.get(self.options.final_goal.current_key) is None:
            raise OptionError("The final goal does not appear to be in the check data")

        # get data from checks file
        file_name = user_path("ModdedMinecraftDataFile.json")
        try:
            with open(file_name, encoding="utf-8") as file:
                data = json.load(file)
                if data.get("version") == 3:
                    checks: list[str] = list(data.get("checks"))
                else:
                    checks = []

        except (json.JSONDecodeError, FileNotFoundError):
            checks: list[str] = []

        def add_item(item):
            if checks.count(item) == 0:
                checks.append(filter_text(item))

        for item in self.options.filler_items:
            add_item(f"item {item}")

        for advancement, details in self.options.checks.items():
            add_item(advancement)
            add_item(details["page"])
            for dependency in self.get_dependencies(details["dependencies"]):
                add_item(dependency)


        checks = {check: i + 6 for i, check in enumerate(checks)}
        with open(file_name, "w", encoding="utf-8") as file:
            json.dump({"version": 3, "checks": checks}, file)

        self.item_name_to_id = checks
        self.location_name_to_id = checks

        # =========================================================================================
        # creates a dict with values we need instead of using all values
        # also makes later logic easier as dependencies are already considered here
        # TODO: why loop through each list multiple times
        # =========================================================================================

        def recursively_add_checks(check: str):
            if self.filtered_checks.get(filter_text(check)) is None and self.is_module_activated(check):
                try:
                    details = self.options.checks[check]
                except KeyError:
                    details = {"type": None, "dependencies": [], "page": check}

                # make sure we don't accidently collect some advancement checks from quests or vice versa
                # details["dependencies"] = filter(self.is_module_activated, details["dependencies"])

                self.filtered_checks.setdefault(filter_text(check), details)
                for dependency in self.get_dependencies(details["dependencies"]):
                    recursively_add_checks(dependency)

        for check, details in self.options.checks.items():
            if self.valid_check_difficulty(details["type"], check):
                recursively_add_checks(check)

        # ensure end goal is in filtered advancements and/or quests
        recursively_add_checks(self.options.final_goal.current_key)


    def create_filler(self):
        return self.create_item(f"item {self.get_filler_item_name()}", ItemClassification.filler)

    def get_filler_item_name(self) -> str:
        return self.random.choices(
            map(filter_text, list(self.options.filler_items.keys())),
            list(self.options.filler_items.values())
        )[0]

    def create_items(self) -> None:
        total_locations = len(self.multiworld.get_unfilled_locations(self.player))

        item_pool = []
        filler_items = []
        items: dict[str: ModdedMinecraftItem] = {}
        for check, details in self.filtered_checks.items():
            if self.options.unlock_type == UnlockType.option_tab:
                # Tab Mode
                items.setdefault(details["page"], self.create_item(details["page"]))

            elif self.options.unlock_type == self.options.unlock_type.option_tree:
                # Tree Mode
                dependencies = self.get_dependencies(details["dependencies"])
                if not dependencies:
                    items.setdefault(check, self.create_item(check))
                else:
                    for dependency in dependencies:
                        items.setdefault(dependency, self.create_item(dependency))

        item_pool += list(items.values())

        for item in self.filtered_checks:
            if items.get(item) is None:
                # not already a check and it should be getting randomized
                if item.startswith(CheckType.ADVANCEMENT) and self.options.advancement_checks_give_items:
                    filler_items.append(self.create_item(item, ItemClassification.filler))
                if item.startswith(CheckType.FTB_QUESTS) and self.options.quest_checks_give_rewards:
                    filler_items.append(self.create_item(item, ItemClassification.filler))

        if total_locations - len(item_pool) > 0:
            # avoid overfilling filler items
            item_pool += self.random.sample(filler_items, min(len(filler_items), total_locations - len(item_pool)))

        item_pool += [self.create_filler() for _ in range(total_locations - len(item_pool))]

        self.multiworld.itempool += item_pool

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)

        # Create regions
        regions: dict[str:Region] = {}
        for check, details in self.filtered_checks.items():
            if self.is_module_activated(check):
                region = regions.setdefault(
                    check,
                    Region(check, self.player, self.multiworld),
                )

                if self.valid_check_difficulty(details["type"], check):
                    # only add as location if it has a valid difficulty
                    location = ModdedMinecraftLocation(self.player, check, self.location_name_to_id[check], region)
                    region.locations.append(location)

        for region_name, region in regions.items():
            dependencies = self.get_dependencies(self.filtered_checks[region_name]["dependencies"])
            if not dependencies:
                # no dependencies connect it to the base
                menu.connect(
                    region,
                    f"menu -> {region_name}",
                    self.get_dependency_rules(region_name)
                )
            else:
                # yes dependencies, connect to all dependencies
                for dependency in dependencies:
                    regions[dependency].connect(
                        region,
                        f"{dependency} -> {region_name}",
                        self.get_dependency_rules(region_name)
                    )

        # all region generation finished add to multiworld regions
        self.multiworld.regions += [*regions.values(), menu]

    def fill_slot_data(self):
        options = self.options.as_dict(
            "final_goal",
            "unlock_type",
            "death_link",
            "activated_modules",
            "advancement_check_difficulty",
            "ftb_quest_check_shape",
            "advancement_checks_give_items",
            "quest_checks_give_rewards",
            "roots_unlocked"
        )
        options["activated_modules"] = "|".join(options["activated_modules"])
        options["advancement_check_difficulty"] = "|".join(options["advancement_check_difficulty"])
        options["ftb_quest_check_shape"] = "|".join(options["ftb_quest_check_shape"])

        return options

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = self.get_dependency_rules(self.options.final_goal.current_key)

    def create_item(
        self,
        name: str,
        classification: ItemClassification = ItemClassification.progression
    ) -> ModdedMinecraftItem:
        return ModdedMinecraftItem(name, classification, self.location_name_to_id[name], self.player)


    def valid_check_difficulty(self, check_type: str, check_name: str) -> bool:
        if check_name.startswith(CheckType.ADVANCEMENT):
            return (
                "Advancements" in self.options.activated_modules and
                check_type in self.options.advancement_check_difficulty
            )
        if check_name.startswith(CheckType.FTB_QUESTS):
            return (
                "FTBQuests" in self.options.activated_modules and
                check_type in self.options.ftb_quest_check_shape
            )
        # not sure what would hit this, for now we just ignore it
        return False

    def is_module_activated(self, item: str) -> bool:
        if item.startswith(CheckType.ADVANCEMENT):
            return "Advancements" in self.options.activated_modules
        if item.startswith(CheckType.FTB_QUESTS):
            return "FTBQuests" in self.options.activated_modules
        logging.error("Found Item with invalid type: %s", item)
        return False

    def get_dependencies(self, dependencies: dict|list) -> list[str]:
        # this is a set to prevent duplicates and order doesn't matter
        output = set()
        if isinstance(dependencies, dict):
            output.update(self.get_dependencies(dependencies["checks"]))
        elif isinstance(dependencies, list):
            for dependency in dependencies:
                if isinstance(dependency, str):
                    output.add(dependency)
                elif isinstance(dependency, dict):
                    output.update(self.get_dependencies(dependency["checks"]))
                elif isinstance(dependency, list):
                    output.update(self.get_dependencies(dependency))

        return [item for item in output if self.is_module_activated(item)]


    def get_dependency_rules(self, check: str) -> callable:
        # TODO: Change to rule builder
        details = self.filtered_checks[check]
        if not details["dependencies"]:
            if self.options.roots_unlocked:
                return lambda state: True
            return lambda state, itself=check: state.has(itself, self.player)
        return lambda state, dependencies=details["dependencies"]: self._get_rule(state, dependencies)

    def _get_rule(self, state, dependencies: dict|list|str) -> bool:
        if isinstance(dependencies, str):
            # see comment on explicit_indirect_conditions
            if self.options.unlock_type == UnlockType.option_tab:
                return state.has(self.filtered_checks[dependencies]["page"], self.player) and state.can_reach_region(dependencies, self.player)
            return state.has(dependencies, self.player) and state.can_reach_region(dependencies, self.player)
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if not self._get_rule(state, dependency):
                    return False
            return True
        if isinstance(dependencies, dict):
            minimum = dependencies["minimum"]
            for dependency in dependencies["checks"]:
                if self._get_rule(state, dependency):
                    minimum -= 1
            return minimum <= 0

        logging.error("Found a dependency that was not a dict/list/str: %s, this should not happen", dependencies)
        return False


regex_exclusions = re.compile("[^\u0000-\uFFFF]", re.UNICODE)
def filter_text(text:str) -> str:
    """
    Ensures that text should be valid to be put into a database (needed for online hosting)
    """
    return regex_exclusions.sub("", text)
