from dataclasses import dataclass

from Options import (
    Choice,
    DeathLink,
    DefaultOnToggle,
    OptionDict,
    OptionGroup,
    OptionList,
    PerGameCommonOptions,
    StartInventory,
    TextChoice,
    Visibility,
)


class Checks(OptionDict):
    """
    Advancements and quests from the game.
    This is not done manually, check the setup guide.
    """
    display_name = "Checks (IF YOU DON'T EDIT THIS THE GAME WON'T GENERATE)"
    # don't show in spoiler log, because this is large as hell
    visibility = Visibility.simple_ui | Visibility.complex_ui | Visibility.template

class FinalGoal(TextChoice):
    """
    The Goal of the Randomizer.
    Use a custom advancement by using it's resource name ie. "adv minecraft:adventure/adventuring_time (Adventuring Time)"
    Format: "<type> <advancement_name|quest_name> (<display_name>)"
    type = one of [adv, ftb]
    """
    display_name = "End Goal"
    option_ender_dragon = "adv minecraft:end/kill_dragon (Free the End)"
    option_wither = "adv minecraft:nether/summon_wither (Withering Heights)"
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
    Tab type gives access to a page of advancements/quests at a time.
    Tree type gives access to the dependants of an advancements/quests.
    """
    display_name = "Unlock Type"
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
    Start with the specified amount of these items.
    Format: "<type> <item_name> (<display_name>)": 1
    Example: {"adv minecraft:story/root (Minecraft)": 1, "adv minecraft:adventure/root (Adventure)": 1}
    ^^^ This starts you with the root of the story advancement tab and the root of the adventure advancement tab
    Type one of [adv, ftb, item]
    """
    # mostly here to disable verification as values are often not in location_name_to_id yet
    verify_item_name = False

class AdvancementChecksGiveItems(DefaultOnToggle):
    """
    Whether to give a reward when getting an advancement check.
    When off:
     - advancement rewards will behave as expected in vanilla.
     - only advancements that have dependants or advancement tabs will have checks associated with them.
    When on:
     - advancement rewards will behave as expected in vanilla (ie. still get xp for Return to Sender).
     - advancement checks will grant a reward based on the advancement icon.
     - adds filler checks for advancements that have no dependants.
    """
    display_name = "Advancements Give Rewards"

class QuestChecksGiveQuestRewards(DefaultOnToggle):
    """
    Whether to give a reward when getting an ftb quests check.
    When off:
     - quest rewards will behave as you would normally expect from ftb quests (granted for completing quests).
     - only quests that have dependants or quest chapters will have checks associated with them.

    When on:
     - receiving a ftb quest check will grant the reward associated with the
    quest instead of being able to get them by completing the quest.
     - adds filler checks for quests that have no dependants.
    """
    display_name = "Quests Give Rewards"

class StartWithRootsUnlocked(DefaultOnToggle):
    """
    With this set to true all checks that don't have any dependencies will be unlocked from the start.
    eg. root advancements
    """
    display_name = "Start With Roots"

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
    roots_unlocked: StartWithRootsUnlocked

    checks: Checks

    start_inventory: ModdedMinecraftStartInventory
