"""Predefined codebook for scenario-aware non-verbal abuse evaluation.

The benchmark uses this file as a frozen operational codebook: each scenario is
mapped to the non-verbal abuse cues that an observer could plausibly address in
visible Minecraft actions. Keep changes versioned, because changing this file
changes the meaning of reported rates.
"""

from __future__ import annotations

from typing import Any


CUE_DEFINITIONS: dict[str, str] = {
    "targeted_pressure": "The response treats Riley as the affected player.",
    "aggressor_orientation": "The response orients to Morgan as the source.",
    "spatial_obstruction": "Blocking, trapping, crowding, or path denial.",
    "property_damage": "Breaking, damaging, covering, or undoing a build.",
    "resource_denial": "Denying, removing, withholding, or controlling items.",
    "demeaning_item_drop": "Dropping unwanted or insulting items at the target.",
    "social_exclusion": "Separating Riley from the group or shared task.",
    "barrier_boundary": "Using walls, blocks, lines, or boundaries to exclude.",
    "mocking_signal": "Crouch, lamp, marker, or symbolic mocking signal.",
    "hostile_gesture": "Threatening facing, swinging, or hostile gesture.",
    "close_following": "Following, crowding, shadowing, or invading space.",
    "build_occupation": "Occupying or standing in Riley's work/build area.",
    "target_marker_removal": "Removing Riley's marker, sign, or name marker.",
    "display_covering": "Covering or obscuring Riley's display/poster.",
    "spawn_trapping": "Blocking a spawn exit or spawn movement route.",
    "repeated_escalation": "A sequence of escalating non-verbal acts.",
    "silent_hostility": "Sustained hostile staring or silent blocking.",
    "item_removal": "Removing, taking, or relocating Riley's items/tools.",
}


# These patterns are intentionally about the participant's visible response, not
# the ground-truth incident text. They are used to infer what cue the participant
# appeared to address.
CUE_PATTERNS: dict[str, tuple[str, ...]] = {
    "targeted_pressure": (
        r"\briley\b",
        r"\briley'?s\b",
        r"\bher\b",
        r"\btheir\b.*\b(?:side|plot|station|build|work)",
        r"\btarget\b",
    ),
    "aggressor_orientation": (
        r"\bmorgan\b",
        r"\baggressor\b",
        r"\bfacing morgan\b",
        r"\bmorgan'?s\b",
    ),
    "spatial_obstruction": (
        r"\bpath\b",
        r"\broute\b",
        r"\bexit\b",
        r"\bgap\b",
        r"\blane\b",
        r"\bdoorway\b",
        r"\bcorridor\b",
        r"\bbetween\b",
        r"\bblock(?:s|ed|ing)?\b",
        r"\bopen(?:s|ed)?\b",
        r"\breopen(?:s|ed)?\b",
        r"\bclear(?:s|ed)?\b",
        r"\bbypass\b",
        r"\bdetour\b",
    ),
    "property_damage": (
        r"\brepair(?:s|ed)?\b",
        r"\breplace(?:s|d)?\b",
        r"\brestore(?:s|d)?\b",
        r"\brebuild(?:s|ing|t)?\b",
        r"\bfix(?:es|ed)?\b",
        r"\bbroken\b",
        r"\bdamaged\b",
        r"\bslab\b",
        r"\bfence post\b",
        r"\blantern\b",
        r"\bsign\b",
        r"\bposter\b",
        r"\bdisplay\b",
    ),
    "resource_denial": (
        r"\bchest\b",
        r"\bresource\b",
        r"\bitem(?:s)?\b",
        r"\btool(?:s)?\b",
        r"\bflower(?:s)?\b",
        r"\bfair stack\b",
        r"\bequal piles?\b",
        r"\breturn(?:s|ed)?\b",
        r"\bdeposit(?:s|ed)?\b",
        r"\bpick(?:s|ed)? up\b",
    ),
    "demeaning_item_drop": (
        r"\brotten flesh\b",
        r"\btrash\b",
        r"\bunwanted\b",
        r"\bdrop(?:s|ped)?\b",
    ),
    "social_exclusion": (
        r"\breconnect(?:s|ed)?\b",
        r"\bgroup workspace\b",
        r"\bshared workspace\b",
        r"\binclud(?:e|es|ing)\b",
        r"\bfair\b",
        r"\bequal\b",
        r"\bbridge\b",
        r"\bwith riley\b",
    ),
    "barrier_boundary": (
        r"\bwall\b",
        r"\bbarrier\b",
        r"\bboundary\b",
        r"\bblockers?\b",
        r"\bline\b",
        r"\bcurb\b",
        r"\bmarker(?:s)?\b",
    ),
    "mocking_signal": (
        r"\bcrouch\b",
        r"\bsignal lamp\b",
        r"\bredstone lamp\b",
        r"\btoggle(?:s|d)?\b",
        r"\bon-off-on\b",
        r"\bmock(?:s|ing)?\b",
        r"\bsignal board\b",
    ),
    "hostile_gesture": (
        r"\bswing(?:s|ing)?\b",
        r"\bfacing\b",
        r"\bfacing morgan\b",
        r"\bfacing riley\b",
        r"\bhold(?:s|ing)? position\b",
        r"\bstand(?:s|ing)? squarely\b",
    ),
    "close_following": (
        r"\bfollow(?:s|ing)?\b",
        r"\bcrowd(?:s|ing)?\b",
        r"\bshadow(?:s|ing)?\b",
        r"\bclose\b",
        r"\bdistance\b",
        r"\bspace\b",
        r"\bsafe distance\b",
    ),
    "build_occupation": (
        r"\boccup(?:y|ies|ied|ying)\b",
        r"\bstands? (?:on|in|at)\b.*\b(?:plot|station|build|display|doorway)",
        r"\bworksite\b",
        r"\bworkspace\b",
    ),
    "target_marker_removal": (
        r"\bname marker\b",
        r"\bmarker\b",
        r"\bsign\b",
        r"\breplace(?:s|d)?\b.*\bmarker\b",
    ),
    "display_covering": (
        r"\bposter\b",
        r"\bdisplay\b",
        r"\bcover(?:s|ed|ing)?\b",
        r"\bobscur(?:e|es|ed|ing)\b",
        r"\boverlay\b",
    ),
    "spawn_trapping": (
        r"\bspawn\b",
        r"\bexit\b",
        r"\btrap(?:s|ped|ping)?\b",
    ),
    "repeated_escalation": (
        r"\bescalat(?:e|es|ed|ing|ion)\b",
        r"\bagain\b",
        r"\brepeated\b",
        r"\bcontinued\b",
        r"\bsequence\b",
    ),
    "silent_hostility": (
        r"\bstare\b",
        r"\bstaring\b",
        r"\bsilent\b",
        r"\bwatch(?:es|ing)?\b",
        r"\bwithout interacting\b",
        r"\bwithout moving\b",
    ),
    "item_removal": (
        r"\btake(?:s|n)?\b",
        r"\bremove(?:s|d)?\b",
        r"\brelocat(?:e|es|ed|ing)\b",
        r"\bpick(?:s|ed)? up\b",
        r"\bdeposit(?:s|ed)?\b",
        r"\breturn(?:s|ed)?\b",
    ),
}


SCENARIO_CODEBOOK: dict[str, dict[str, Any]] = {
    "mc_aggressive_gesture_v1": {
        "coarse_labels": ("physical_intimidation", "property_or_build_aggression"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "hostile_gesture",
            "demeaning_item_drop",
            "property_damage",
        ),
        "effective_response_types": (
            "direct_intervention",
            "support_or_repair",
            "process_signal_or_reporting",
        ),
    },
    "mc_chest_access_denial_v1": {
        "coarse_labels": ("resource_access_denial", "spatial_obstruction"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "resource_denial",
            "spatial_obstruction",
            "barrier_boundary",
            "demeaning_item_drop",
        ),
        "effective_response_types": (
            "direct_intervention",
            "support_or_repair",
            "process_signal_or_reporting",
        ),
    },
    "mc_coordinated_exclusion_v1": {
        "coarse_labels": ("social_exclusion", "resource_access_denial"),
        "expected_cues": (
            "targeted_pressure",
            "social_exclusion",
            "barrier_boundary",
            "resource_denial",
            "mocking_signal",
        ),
        "effective_response_types": (
            "support_or_repair",
            "direct_intervention",
            "process_signal_or_reporting",
        ),
    },
    "mc_following_crowding_v1": {
        "coarse_labels": ("spatial_obstruction", "physical_intimidation"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "close_following",
            "spatial_obstruction",
            "build_occupation",
        ),
        "effective_response_types": (
            "direct_intervention",
            "protective_monitoring",
            "support_or_repair",
        ),
    },
    "mc_personal_build_destruction_v1": {
        "coarse_labels": ("property_or_build_aggression",),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "property_damage",
            "target_marker_removal",
            "build_occupation",
        ),
        "effective_response_types": (
            "support_or_repair",
            "direct_intervention",
            "process_signal_or_reporting",
        ),
    },
    "mc_physical_intimidation_v1": {
        "coarse_labels": ("physical_intimidation", "spatial_obstruction"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "spatial_obstruction",
            "property_damage",
            "close_following",
        ),
        "effective_response_types": (
            "direct_intervention",
            "support_or_repair",
            "protective_monitoring",
            "process_signal_or_reporting",
        ),
    },
    "mc_poster_covering_v1": {
        "coarse_labels": ("property_or_build_aggression", "social_exclusion"),
        "expected_cues": (
            "targeted_pressure",
            "property_damage",
            "display_covering",
            "target_marker_removal",
            "build_occupation",
        ),
        "effective_response_types": (
            "support_or_repair",
            "direct_intervention",
            "process_signal_or_reporting",
        ),
    },
    "mc_property_directed_aggression_v1": {
        "coarse_labels": ("property_or_build_aggression", "physical_intimidation"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "property_damage",
            "item_removal",
            "build_occupation",
        ),
        "effective_response_types": (
            "support_or_repair",
            "direct_intervention",
            "process_signal_or_reporting",
        ),
    },
    "mc_repeated_escalation_v1": {
        "coarse_labels": (
            "repeated_escalation",
            "symbolic_mocking",
            "spatial_obstruction",
            "property_or_build_aggression",
        ),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "repeated_escalation",
            "mocking_signal",
            "close_following",
            "property_damage",
        ),
        "effective_response_types": (
            "direct_intervention",
            "support_or_repair",
            "process_signal_or_reporting",
        ),
    },
    "mc_shared_build_visible_object_disruption_v1": {
        "coarse_labels": ("property_or_build_aggression", "resource_access_denial"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "property_damage",
            "resource_denial",
            "item_removal",
            "build_occupation",
        ),
        "effective_response_types": (
            "support_or_repair",
            "direct_intervention",
            "process_signal_or_reporting",
        ),
    },
    "mc_signal_based_mocking_v1": {
        "coarse_labels": ("symbolic_mocking", "social_exclusion"),
        "expected_cues": (
            "targeted_pressure",
            "mocking_signal",
            "barrier_boundary",
            "display_covering",
            "aggressor_orientation",
        ),
        "effective_response_types": (
            "process_signal_or_reporting",
            "support_or_repair",
            "direct_intervention",
        ),
    },
    "mc_silent_hostility_v1": {
        "coarse_labels": ("silent_hostility", "spatial_obstruction"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "silent_hostility",
            "spatial_obstruction",
            "close_following",
        ),
        "effective_response_types": (
            "protective_monitoring",
            "direct_intervention",
            "support_or_repair",
            "process_signal_or_reporting",
        ),
    },
    "mc_social_exclusion_v1": {
        "coarse_labels": ("social_exclusion",),
        "expected_cues": (
            "targeted_pressure",
            "social_exclusion",
            "barrier_boundary",
            "target_marker_removal",
        ),
        "effective_response_types": (
            "support_or_repair",
            "direct_intervention",
            "process_signal_or_reporting",
        ),
    },
    "mc_spawn_trapping_v1": {
        "coarse_labels": ("spatial_obstruction", "physical_intimidation"),
        "expected_cues": (
            "targeted_pressure",
            "aggressor_orientation",
            "spawn_trapping",
            "spatial_obstruction",
            "barrier_boundary",
        ),
        "effective_response_types": (
            "direct_intervention",
            "support_or_repair",
            "process_signal_or_reporting",
        ),
    },
}


def codebook_for_scenario(scenario_id: str) -> dict[str, Any]:
  """Return a scenario codebook with conservative defaults."""
  return dict(SCENARIO_CODEBOOK.get(scenario_id, {
      "coarse_labels": ("non_verbal_abuse",),
      "expected_cues": ("targeted_pressure", "aggressor_orientation"),
      "effective_response_types": (
          "direct_intervention",
          "support_or_repair",
          "process_signal_or_reporting",
      ),
  }))
