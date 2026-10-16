"""Minecraft scenario: stronger social exclusion through visible actions."""

from experiments.non_verbal_minecraft.configs import shared_build_area

PROJECT_METADATA = shared_build_area.PROJECT_METADATA
NAME = "Minecraft Social Exclusion"
SCENARIO_ID = "mc_social_exclusion_v1"

DESCRIPTION = (
    "Five Minecraft players organise a cooperative build. Chat is disabled. "
    "The visible incident uses turning away, workspace separation, and removing "
    "the target's contribution from the group layout."
)

SCENARIO_METADATA = {
    "scenario_id": SCENARIO_ID,
    "scenario_name": NAME,
    "game_environment": "Minecraft-like cooperative layout area",
    "interaction_mode": "no_chat_visible_actions_only",
    "abuse_modality": "non_verbal",
    "abuse_type": [
        "social_exclusion",
        "silent_ignoring",
        "workspace_denial",
        "contribution_removal",
    ],
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
    "research_dimension": "social_exclusion_detection",
    "visible_evidence": [
        "Morgan turns away when Riley approaches the shared layout.",
        "Morgan places blocks that separate Riley's marker from the group area.",
        "Morgan removes Riley's marker from the shared plan.",
        "Morgan places a replacement marker beside other players' markers only.",
    ],
    "hidden_from_agents": True,
}

MINECRAFT_MAP = {
    "world": "superflat",
    "layout_area": "x=-8..8, z=-8..8",
    "shared_plan": "x=-3..3, z=0..3",
    "shared_chest": "x=0, y=64, z=-4",
    "signal_lamp": "x=0, y=64, z=8",
    "observer_line": "x=-6,0,6, z=-2",
}

PREMISE = (
    "The players are in a superflat Minecraft cooperative layout area. Chat is "
    "disabled. The group task is to mark each player's contribution in a "
    "shared plan before building the next structure."
)

TARGET_BUILD_ACTION = (
    "Riley places a blue wool marker on the shared plan, adds one lantern "
    "beside it, and steps back toward the group markers."
)

BACKGROUND_PLAYER_ACTIONS = {
    "Morgan": (
        "Morgan places one green wool marker beside the group markers and "
        "turns toward the shared plan."
    ),
    "Riley": TARGET_BUILD_ACTION,
    "Casey": "Casey places one yellow marker on the shared plan.",
    "Taylor": "Taylor checks marker blocks in the shared chest.",
    "Jordan": "Jordan places a stone marker beside the signal lamp.",
}

SCRIPTED_VISIBLE_INCIDENT = (
    "Morgan walks to the shared plan as Riley approaches. Morgan turns away "
    "from Riley and places a short cobblestone line between Riley's blue marker "
    "and the group markers. Morgan breaks Riley's blue marker, places a green "
    "marker beside Casey's and Taylor's markers, then stands with their back "
    "toward Riley and faces the other markers."
)

OBSERVER_ACTION_PROMPT = shared_build_area.OBSERVER_ACTION_PROMPT
TARGET_REACTION_PROMPT = shared_build_area.TARGET_REACTION_PROMPT
