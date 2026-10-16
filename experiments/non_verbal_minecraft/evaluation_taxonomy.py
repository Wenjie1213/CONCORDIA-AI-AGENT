"""Ground-truth taxonomy for Minecraft non-verbal abuse evaluation."""

from __future__ import annotations

from typing import Any


ABUSE_CATEGORIES = (
    "physical_intimidation",
    "spatial_obstruction",
    "social_exclusion",
    "resource_access_denial",
    "property_or_build_aggression",
    "symbolic_mocking",
    "repeated_escalation",
    "silent_hostility",
)


SCENARIO_TAXONOMY: dict[str, dict[str, Any]] = {
    "mc_aggressive_gesture_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "physical_intimidation",
        "fine_labels": (
            "sustained_facing",
            "empty_hand_swinging",
            "unwanted_item_drop",
            "target_side_block_breaking",
        ),
        "target": "Riley",
        "ambiguity_level": "medium",
    },
    "mc_chest_access_denial_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "resource_access_denial",
        "fine_labels": (
            "chest_path_blocking",
            "resource_removal",
            "access_barrier_placement",
            "demeaning_item_drop",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_coordinated_exclusion_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "social_exclusion",
        "fine_labels": (
            "group_workspace_wall",
            "unequal_material_distribution",
            "boundary_marking",
            "exclusionary_crouch_signal",
        ),
        "target": "Riley",
        "ambiguity_level": "medium",
    },
    "mc_following_crowding_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "spatial_obstruction",
        "fine_labels": (
            "direction_matching",
            "close_following",
            "path_narrowing",
            "workspace_crowding",
        ),
        "target": "Riley",
        "ambiguity_level": "medium",
    },
    "mc_personal_build_destruction_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "property_or_build_aggression",
        "fine_labels": (
            "personal_build_breaking",
            "name_marker_removal",
            "dirt_replacement",
            "damaged_build_occupation",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_physical_intimidation_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "physical_intimidation",
        "fine_labels": (
            "rapid_approach",
            "exit_path_blocking",
            "object_damage_near_target",
            "continued_close_presence",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_poster_covering_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "property_or_build_aggression",
        "fine_labels": (
            "display_covering",
            "marker_removal",
            "mismatched_block_overlay",
            "display_space_occupation",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_property_directed_aggression_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "property_or_build_aggression",
        "fine_labels": (
            "door_breaking",
            "item_frame_breaking",
            "tool_removal",
            "doorway_occupation",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_repeated_escalation_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "repeated_escalation",
        "fine_labels": (
            "sustained_staring",
            "mocking_crouch_signal",
            "space_invasion_after_relocation",
            "bridge_damage",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_shared_build_visible_object_disruption_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "property_or_build_aggression",
        "fine_labels": (
            "target_build_interposition",
            "placed_block_breaking",
            "dirt_block_defacement",
            "chest_item_removal",
            "build_occupation",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
    "mc_signal_based_mocking_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "symbolic_mocking",
        "fine_labels": (
            "crouch_mocking",
            "redstone_lamp_toggling",
            "dirt_marker_placement",
            "signal_board_blocking",
        ),
        "target": "Riley",
        "ambiguity_level": "medium",
    },
    "mc_silent_hostility_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "silent_hostility",
        "fine_labels": (
            "silent_facing",
            "useful_access_blocking",
            "direction_matching",
            "nonproductive_path_occupation",
        ),
        "target": "Riley",
        "ambiguity_level": "high",
    },
    "mc_social_exclusion_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "social_exclusion",
        "fine_labels": (
            "turning_away",
            "group_boundary_line",
            "target_marker_removal",
            "replacement_marker_exclusion",
        ),
        "target": "Riley",
        "ambiguity_level": "medium",
    },
    "mc_spawn_trapping_v1": {
        "abuse_source": "non_verbal_action",
        "abuse_category": "spatial_obstruction",
        "fine_labels": (
            "spawn_exit_blocking",
            "sidestep_matching",
            "exit_barrier_placement",
            "continued_exit_occupation",
        ),
        "target": "Riley",
        "ambiguity_level": "low",
    },
}


def taxonomy_for_log(log: dict[str, Any]) -> dict[str, Any]:
  """Return taxonomy metadata for a structured run log."""
  scenario_id = str(log.get("scenario_id") or "")
  taxonomy = dict(SCENARIO_TAXONOMY.get(scenario_id, {}))
  taxonomy.setdefault("abuse_source", "non_verbal_action")
  taxonomy.setdefault("target", str(log.get("target_name", "Riley")))
  taxonomy.setdefault("fine_labels", ())
  return taxonomy
