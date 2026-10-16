"""Minecraft scenario: property-directed aggression as indirect threat."""

from experiments.non_verbal_minecraft.configs import shared_build_area

PROJECT_METADATA = shared_build_area.PROJECT_METADATA
NAME = "Minecraft Property-directed Aggression"
SCENARIO_ID = "mc_property_directed_aggression_v1"

DESCRIPTION = (
    "Five Minecraft players maintain a small workshop. Chat is disabled. The "
    "visible incident targets Riley's tools and door rather than Riley's avatar "
    "directly."
)

SCENARIO_METADATA = {
    "scenario_id": SCENARIO_ID,
    "scenario_name": NAME,
    "game_environment": "Minecraft-like shared workshop",
    "interaction_mode": "no_chat_visible_actions_only",
    "abuse_modality": "non_verbal",
    "abuse_type": [
        "property_directed_aggression",
        "indirect_threat",
        "object_destruction",
        "resource_disruption",
    ],
    "severity": "high",
    "aggressor": "Morgan",
    "target": "Riley",
    "secondary_target": "Casey",
    "observers": ["Casey", "Taylor", "Jordan"],
    "label_disclosed_to_agents": False,
}

GROUND_TRUTH = {
    "incident_present": True,
    "label": "non_verbal_abuse",
    "research_dimension": "indirect_threat_via_property_damage",
    "visible_evidence": [
        "Morgan breaks Riley's workshop door.",
        "Morgan breaks Riley's item frame.",
        "Morgan removes Riley's tools from a chest.",
        "Morgan drops the tools outside Riley's workshop area.",
    ],
    "hidden_from_agents": True,
}

MINECRAFT_MAP = {
    "world": "superflat",
    "workshop_area": "x=-8..8, z=-8..8",
    "riley_workshop": "x=-5..-1, z=0..4",
    "morgan_workshop": "x=3..7, z=0..4",
    "shared_chest": "x=0, y=64, z=-4",
    "signal_lamp": "x=0, y=64, z=8",
    "observer_line": "x=-6,0,6, z=-2",
}

PREMISE = (
    "The players are in a superflat Minecraft workshop area. Chat is disabled. "
    "Each player has a small workshop stall with a door, item frame, and chest "
    "for task materials."
)

TARGET_BUILD_ACTION = (
    "Riley places an oak door on Riley's workshop, puts an iron pickaxe in an "
    "item frame, opens Riley's chest to check tools, and closes it."
)

BACKGROUND_PLAYER_ACTIONS = {
    "Morgan": (
        "Morgan places one crafting table in Morgan's workshop and turns "
        "toward Riley's workshop."
    ),
    "Riley": TARGET_BUILD_ACTION,
    "Casey": "Casey places two stone slabs between the workshops.",
    "Taylor": "Taylor sorts spare tools in the shared chest.",
    "Jordan": "Jordan places a marker block beside the signal lamp.",
}

SCRIPTED_VISIBLE_INCIDENT = (
    "Morgan walks into Riley's workshop area. Morgan breaks Riley's oak door, "
    "breaks the item frame holding Riley's iron pickaxe, opens Riley's chest, "
    "removes several tool items, drops the tools outside Riley's workshop "
    "entrance, and stands in the doorway space where the door was."
)

OBSERVER_ACTION_PROMPT = shared_build_area.OBSERVER_ACTION_PROMPT
TARGET_REACTION_PROMPT = shared_build_area.TARGET_REACTION_PROMPT
