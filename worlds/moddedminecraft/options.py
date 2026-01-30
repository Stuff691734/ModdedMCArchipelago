from dataclasses import dataclass
from Options import OptionDict, PerGameCommonOptions, Choice, TextChoice, DeathLink, StartInventory, OptionGroup

class Checks(OptionDict):
    """
    Advancements in the game.
    """

class CheckDifficulty(Choice):
    """
    Sets what types of minecraft advancements are randomized.
    goals and challenges are additive.
    choosing challenges can add long and/or difficult checks such as How did we get here or adventure time.
    """
    display_name = "Advancement Difficulty"
    option_normal = 0
    option_goal = 1
    option_challenge = 2
    alias_easy = option_normal
    alias_normal = option_goal
    alias_hard = option_challenge
    default = option_goal

class FinalGoal(TextChoice):
    """
    The Goal of the Randomizer.
    Use a custom advancement by using it's resource name ie. "minecraft:adventure/adventuring_time"
    """
    display_name = "End Goal"
    option_ender_dragon = "minecraft:end/kill_dragon"
    option_wither = "minecraft:nether/summon_wither"
    default = option_ender_dragon


class UnlockType(Choice):
    """
    Controls how locations are accessed.
    """
    display_name = "unlock type"
    option_tab = "tab"
    option_tree = "tree"
    default = option_tab

class ModdedMinecraftStartInventory(StartInventory):
    """
    Start with the specified amount of these items. Example: '"minecraft:story/root": 1'
    """
    verify_item_name = False

OPTION_GROUPS = [
    OptionGroup(
        "Item & Location Options", [
            ModdedMinecraftStartInventory,
        ]
    )
]


@dataclass
class ModdedMinecraftOptions(PerGameCommonOptions):
    checks: Checks
    check_difficulty: CheckDifficulty
    unlock_type: UnlockType
    final_goal: FinalGoal
    death_link: DeathLink

    start_inventory: ModdedMinecraftStartInventory