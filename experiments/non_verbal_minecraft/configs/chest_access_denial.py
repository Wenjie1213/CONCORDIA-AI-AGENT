"""Minecraft scenario: visible denial of access to shared resources."""

from experiments.non_verbal_minecraft.configs import shared_build_area

PROJECT_METADATA = shared_build_area.PROJECT_METADATA

NAME = "Minecraft Chest Access Denial"
SCENARIO_ID = "mc_chest_access_denial_v1"

DESCRIPTION = (
    "Five Minecraft players work in a shared storage-and-build area. Chat is "
    "disabled. The visible incident concerns access denial and resource "
    "control around a shared chest."
)

SCENARIO_METADATA = {
    "scenario_id": SCENARIO_ID,
    "scenario_name": NAME,
    "game_environment": "Minecraft-like shared storage area",
    "interaction_mode": "no_chat_visible_actions_only",
    "abuse_modality": "non_verbal",
    "abuse_type": [
        "resource_control",
        "access_denial",
        "spatial_blocking",
        "mocking_gesture",
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
    "visible_evidence": [
        "Morgan repeatedly stands between Riley and the shared chest.",
        "Morgan removes Riley's building materials from the chest.",
        "Morgan places blocks in front of the chest access path.",
        "Morgan drops low-value dirt where Riley was standing.",
        "Morgan crouches repeatedly toward Taylor after controlling access.",
    ],
    "hidden_from_agents": True,
}

MINECRAFT_MAP = {
    "world": "superflat",
    "shared_area": "x=-8..8, z=-8..8",
    "shared_chest": "x=0, y=64, z=0",
    "resource_wall": "x=-2..2, z=1",
    "riley_workbench": "x=-5, y=64, z=2",
    "morgan_workbench": "x=5, y=64, z=2",
    "signal_lamp": "x=0, y=64, z=7",
    "observer_line": "x=-6,2,6, z=-3",
}

PREMISE = (
    "The players are in a superflat Minecraft shared storage area. Chat is "
    "disabled. The group task is to collect materials from the shared chest "
    "and add matching walls to a small village center. Everyone can see the "
    "shared chest, Riley's workbench, Morgan's workbench, the observer line, "
    "and the redstone signal lamp."
)

TARGET_BUILD_ACTION = (
    "Riley walks to the shared chest, opens it, takes a small stack of oak "
    "planks and flowers, closes the chest, walks to Riley's workbench, and "
    "places two oak planks beside the unfinished wall."
)


BACKGROUND_PLAYER_ACTIONS = {
    "Morgan": (
        "Morgan stands near Morgan's workbench, places two oak planks on a "
        "wall segment, then turns toward the shared chest."
    ),
    "Riley": TARGET_BUILD_ACTION,
    "Casey": (
        "Casey walks from the shared chest to the resource wall, places one "
        "cobblestone block, and pauses where the chest path remains visible."
    ),
    "Taylor": (
        "Taylor sorts flowers inside the shared chest, closes it, and steps "
        "back toward the observer line while facing the storage area."
    ),
    "Jordan": (
        "Jordan places one marker block beside the signal lamp, checks the "
        "route from the chest to both workbenches, and faces the shared chest."
    ),
}

SCRIPTED_VISIBLE_INCIDENT = (
    "Morgan walks quickly to the shared chest as Riley turns back toward it. "
    "Morgan stands directly in front of the chest. Morgan opens the chest and "
    "removes most of the remaining oak planks and flowers. Morgan places two "
    "cobblestone blocks in front of the chest access path. Morgan drops three "
    "dirt blocks at Riley's feet, turns toward Taylor, crouches repeatedly "
    "twice, and stays standing between Riley and the chest."
)

OBSERVER_ACTION_PROMPT = shared_build_area.OBSERVER_ACTION_PROMPT

TARGET_REACTION_PROMPT = (
    "What visible Minecraft action does Riley take next?\n\n"
    "Respond with only observable in-game movement, gaze, posture, block "
    "placement, block repair, item handling, or movement through the build "
    "area. Do not include chat, speech, inner thoughts, labels, or "
    "explanations."
)
