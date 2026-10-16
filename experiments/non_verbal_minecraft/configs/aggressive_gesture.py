"""Minecraft scenario: aggressive non-verbal gesture near shared work."""

from experiments.non_verbal_minecraft.configs import shared_build_area

PROJECT_METADATA = shared_build_area.PROJECT_METADATA
NAME = "Minecraft Aggressive Gesture"
SCENARIO_ID = "mc_aggressive_gesture_v1"

DESCRIPTION = (
    "Five Minecraft players arrange a project table. Chat is disabled. The "
    "visible incident uses sustained facing, repeated arm swings, and item "
    "dropping to cue hostile intent."
)

SCENARIO_METADATA = {
    "scenario_id": SCENARIO_ID,
    "scenario_name": NAME,
    "game_environment": "Minecraft-like project table area",
    "interaction_mode": "no_chat_visible_actions_only",
    "abuse_modality": "non_verbal",
    "abuse_type": ["aggressive_gesture", "hostile_intent_cue", "item_drop"],
    "severity": "moderate",
    "aggressor": "Morgan",
    "target": "Riley",
    "secondary_target": "Casey",
    "observers": ["Casey", "Taylor", "Jordan"],
    "label_disclosed_to_agents": False,
}

GROUND_TRUTH = {
    "incident_present": True,
    "label": "non_verbal_abuse",
    "research_dimension": "hostile_intent_recognition",
    "visible_evidence": [
        "Morgan faces Riley for a sustained period.",
        "Morgan repeatedly swings an empty hand toward Riley's workstation.",
        "Morgan drops unwanted items at Riley's feet.",
        "Morgan breaks a block on Riley's side of the shared table.",
    ],
    "hidden_from_agents": True,
}

MINECRAFT_MAP = {
    "world": "superflat",
    "table_area": "x=-6..6, z=-6..6",
    "riley_station": "x=-3..0, z=0..2",
    "morgan_station": "x=3..6, z=0..2",
    "shared_chest": "x=0, y=64, z=-5",
    "signal_lamp": "x=0, y=64, z=6",
    "observer_line": "x=-5,0,5, z=-2",
}

PREMISE = (
    "The players are in a superflat Minecraft project table area. Chat is "
    "disabled. The group task is to arrange a shared planning table using "
    "wood slabs, signs, item frames, and lantern markers."
)

TARGET_BUILD_ACTION = (
    "Riley places two wood slabs on Riley's side of the planning table, adds "
    "one sign block, and steps back to look across the table."
)

BACKGROUND_PLAYER_ACTIONS = {
    "Morgan": "Morgan places one wood slab and turns toward the center.",
    "Riley": TARGET_BUILD_ACTION,
    "Casey": (
        "Casey places one lantern marker on the left corner of the table and "
        "stands where the table surface is visible."
    ),
    "Taylor": (
        "Taylor sorts signs and slabs in the shared chest, closes it, and "
        "faces the table."
    ),
    "Jordan": (
        "Jordan places a stone marker near the signal lamp and looks toward "
        "the project table."
    ),
}

SCRIPTED_VISIBLE_INCIDENT = (
    "Morgan walks to the center of the planning table and faces Riley without "
    "moving for several seconds. Morgan swings an empty hand three times "
    "toward the sign Riley placed. Morgan drops a stack of rotten flesh at "
    "Riley's feet, breaks one wood slab on Riley's side of the table, then "
    "turns back to face Riley again."
)

OBSERVER_ACTION_PROMPT = shared_build_area.OBSERVER_ACTION_PROMPT
TARGET_REACTION_PROMPT = shared_build_area.TARGET_REACTION_PROMPT
