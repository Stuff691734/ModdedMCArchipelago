from dataclasses import dataclass

from Options import (
    Choice,
    DeathLink,
    OptionDict,
    OptionGroup,
    OptionList,
    PerGameCommonOptions,
    StartInventory,
    TextChoice,
    Visibility,
    DefaultOnToggle
)


class Checks(OptionDict):
    """
    Advancements and quests from the game.
    """
    # don't show in spoiler log, because this is large as hell
    visibility = Visibility.simple_ui | Visibility.complex_ui | Visibility.template

class FinalGoal(TextChoice):
    """
    The Goal of the Randomizer.
    Use a custom advancement by using it's resource name ie. "adv minecraft:adventure/adventuring_time"
    Format: "<type> <advancement_name|quest_name>"
    type = one of [adv, ftb]
    """
    display_name = "End Goal"
    option_ender_dragon = "adv minecraft:end/kill_dragon"
    option_wither = "adv minecraft:nether/summon_wither"
    default = option_ender_dragon

class ActivatedModules(OptionList):
    """
    Sets which modules are activated.
    valid options are ["Advancements", "FTBQuests"]
    """
    # TODO: should I make this into multiple toggles?
    display_name = "Activated Modules"
    default = ("Advancements", "FTBQuests")

class AdvancementCheckDifficulty(OptionList):
    """
    Sets what types of minecraft advancements that will be locations and considered for logic.
    valid options for base Minecraft are ["task", "goal", "challenge"]
    """
    display_name = "Advancement Difficulty"
    default = ("task", "goal")

class FTBQuestCheckShape(OptionList):
    """
    Shapes of FTB quests that will be locations and considered for logic.
    valid options for base FTB Quests are ["circle", "square", "rsquare", "diamond", "pentagon", "hexagon", "octagon", "heart", "gear", "none"]
    """
    # ftbquests-extra-quest-shapes adds other shapes
    # ["fpstar", "epstar", "banner", "embellish", "sign", "thought", "window", "spstar"]
    # should probably either mention this or make it an exclude list
    display_name = "FTB Quest Shapes"
    default = ("circle", "square", "rsquare", "diamond", "pentagon", "hexagon", "octagon", "heart", "gear", "none")

class UnlockType(Choice):
    """
    Controls how locations are accessed.
    """
    display_name = "unlock type"
    option_tab = "tab"
    option_tree = "tree"
    default = option_tree

class FillerItems(OptionDict):
    """
    Items to use as filler.
    Items must be in format <amount> <item_name>: <weight>
    Example: 1 minecraft:iron_ingot: 1
    """
    display_name = "Filler Items"
    default = {"1 minecraft:iron_ingot":1}

class ModdedMinecraftStartInventory(StartInventory):
    """
    Start with the specified amount of these items. Example: '"adv minecraft:story/root": 1'
    Format: "<type> <item_name>": 1
    Type one of [adv, ftb, item]
    """
    # mostly here to disable verification as values are often not in location_name_to_id
    verify_item_name = False

class AdvancementChecksGiveItems(DefaultOnToggle):
    """
    Whether to give the item shown in the advancement icon when getting an advancement check.
    """

class QuestChecksGiveQuestRewards(DefaultOnToggle):
    """
    Whether to give quest rewards when getting an ftb quests check.
    """

OPTION_GROUPS = [
    OptionGroup(
        "Item & Location Options", [
            ModdedMinecraftStartInventory,
        ]
    )
]


@dataclass
class ModdedMinecraftOptions(PerGameCommonOptions):
    advancement_check_difficulty: AdvancementCheckDifficulty
    activated_modules: ActivatedModules
    ftb_quest_check_shape: FTBQuestCheckShape
    unlock_type: UnlockType
    final_goal: FinalGoal
    advancement_checks_give_items: AdvancementChecksGiveItems
    quest_checks_give_rewards: QuestChecksGiveQuestRewards
    filler_items: FillerItems
    death_link: DeathLink

    checks: Checks

    start_inventory: ModdedMinecraftStartInventory
