# Modded Minecraft

## TODO
use seperate dictionaries for item_name_to_id and location_name_to_id
1. simply don't add filler to location_name_to_id
    - is this needed?
- python

check and validate input from options
- python

create more options/dynamic options for filler items
- python

add proper documentation
- python
- java
- archipealgo setup/game_info markdowns

custom death event/message?
- java

Create webworld

## Ideas
use a range for difficulty, so that only goals and challenges count etc.
- python

gameplay modes
- Unlock each and every advancement
- Everything starts unlocked
1) tab
2) tree
3) single

Integration
1. Better Questing
2. FTB Quests
3. Hardcore Questing
4. Advancement display? (show result from checks)
5. Odyssey quests?



## Bugs/Unintended/Not Wanted
player doesn't start with checks available -> solutions:
1. have roots always be open
2. have option for roots to be open (default available)
3. explicitly mention as warning and prepare error message.
    - python

sometimes prevents entering into world. retrying allows access.
try catch around Identifier.validate()

better details for connection errors eg. incorrect name

recipes from certain mods show up, consider excluding advancements with `:recipes/` inside

send message to player only when giving item after connecting

kill other players in world on deathlink

fucks up if starting item not in location_name_to_item