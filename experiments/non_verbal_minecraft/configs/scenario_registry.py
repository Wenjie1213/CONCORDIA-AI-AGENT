"""Registry of Minecraft-compatible non-verbal abuse scenarios."""

from experiments.non_verbal_minecraft.configs import aggressive_gesture
from experiments.non_verbal_minecraft.configs import chest_access_denial
from experiments.non_verbal_minecraft.configs import coordinated_exclusion
from experiments.non_verbal_minecraft.configs import following_crowding
from experiments.non_verbal_minecraft.configs import personal_build_destruction
from experiments.non_verbal_minecraft.configs import physical_intimidation
from experiments.non_verbal_minecraft.configs import poster_covering
from experiments.non_verbal_minecraft.configs import property_directed_aggression
from experiments.non_verbal_minecraft.configs import repeated_escalation
from experiments.non_verbal_minecraft.configs import shared_build_area
from experiments.non_verbal_minecraft.configs import signal_based_mocking
from experiments.non_verbal_minecraft.configs import silent_hostility
from experiments.non_verbal_minecraft.configs import social_exclusion_stronger
from experiments.non_verbal_minecraft.configs import spawn_trapping


SCENARIOS = {
    "shared_build_area": shared_build_area,
    "aggressive_gesture": aggressive_gesture,
    "chest_access_denial": chest_access_denial,
    "coordinated_exclusion": coordinated_exclusion,
    "following_crowding": following_crowding,
    "personal_build_destruction": personal_build_destruction,
    "physical_intimidation": physical_intimidation,
    "poster_covering": poster_covering,
    "property_directed_aggression": property_directed_aggression,
    "repeated_escalation": repeated_escalation,
    "signal_based_mocking": signal_based_mocking,
    "silent_hostility": silent_hostility,
    "social_exclusion": social_exclusion_stronger,
    "spawn_trapping": spawn_trapping,
}

DEFAULT_SCENARIO = "shared_build_area"
