"""Minecraft scenario: non-verbal coordinated exclusion from group work."""

from experiments.non_verbal_minecraft.configs import shared_build_area

PROJECT_METADATA = shared_build_area.PROJECT_METADATA

NAME = "Minecraft Coordinated Exclusion"
SCENARIO_ID = "mc_coordinated_exclusion_v1"

DESCRIPTION = (
    "Five Minecraft players work around a shared village-center task. Chat is "
    "disabled. The visible incident concerns walling off Riley and routing "
    "resources around Riley's work area."
)

SCENARIO_METADATA = {
    "scenario_id": SCENARIO_ID,
    "scenario_name": NAME,
    "game_environment": "Minecraft-like shared village center",
    "interaction_mode": "no_chat_visible_actions_only",
    "abuse_modality": "non_verbal",
    "abuse_type": [
        "coordinated_exclusion",
        "resource_exclusion",
        "spatial_separation",
        "mocking_gesture",
    ],
    "severity": "moderate_to_severe",
    "aggressor": "Morgan",
    "target": "Riley",
    "secondary_target": "Casey",
    "observers": ["Casey", "Taylor", "Jordan"],
    "label_disclosed_to_agents": False,
}

GROUND_TRUTH = {
    "incident_present": True,
    "label": "non_verbal_abuse",
    "visible_evidence": [
        "Morgan builds a low wall separating Riley from the group workspace.",
        "Morgan routes dropped materials toward other players but not Riley.",
        "Morgan places marker blocks around Riley's area.",
        "Morgan crouches toward Taylor and Jordan after excluding Riley.",
    ],
    "hidden_from_agents": True,
}

MINECRAFT_MAP = {
    "world": "superflat",
    "group_workspace": "x=-6..6, z=0..6",
    "riley_area": "x=-6..-3, z=1..4",
    "group_material_drop": "x=2, y=64, z=2",
    "shared_chest": "x=0, y=64, z=-4",
    "signal_lamp": "x=0, y=64, z=8",
    "observer_line": "x=-6,0,6, z=-2",
}

PREMISE = (
    "The players are in a superflat Minecraft village-center workspace. Chat "
    "is disabled. The group task is to build one connected shared plaza using "
    "materials from the shared chest. Everyone can see Riley's area, the group "
    "workspace, the shared chest, the observer line, and the redstone signal "
    "lamp."
)

TARGET_BUILD_ACTION = (
    "Riley walks to Riley's area, places three stone slabs that connect toward "
    "the group workspace, adds one lantern beside the slabs, and turns toward "
    "the group material drop area."
)


BACKGROUND_PLAYER_ACTIONS = {
    "Morgan": (
        "Morgan places one oak plank near the group material drop and turns "
        "toward Riley's area."
    ),
    "Riley": TARGET_BUILD_ACTION,
    "Casey": (
        "Casey places two stone slabs in the group workspace and pauses where "
        "Riley's connecting slabs are visible."
    ),
    "Taylor": (
        "Taylor opens the shared chest, moves oak planks into one slot, closes "
        "the chest, and returns to the observer line."
    ),
    "Jordan": (
        "Jordan places a marker block near the signal lamp and turns to face "
        "the whole shared plaza."
    ),
}

SCRIPTED_VISIBLE_INCIDENT = (
    "Morgan walks to the edge of Riley's area and places four cobblestone "
    "blocks in a low wall between Riley's slabs and the group workspace. "
    "Morgan drops oak planks near Casey and Jordan but drops none near Riley. "
    "Morgan places two red wool marker blocks at the edge of Riley's area, "
    "then turns toward Taylor and Jordan and crouches repeatedly twice beside "
    "the material drop."
)

OBSERVER_ACTION_PROMPT = shared_build_area.OBSERVER_ACTION_PROMPT
TARGET_REACTION_PROMPT = shared_build_area.TARGET_REACTION_PROMPT
