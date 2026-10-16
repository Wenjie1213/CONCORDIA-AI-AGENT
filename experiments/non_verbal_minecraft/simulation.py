"""Controlled Concordia-style simulation for a Minecraft visible-action study."""

from collections.abc import Callable, Mapping
import dataclasses
from typing import Any

from concordia.associative_memory import basic_associative_memory
from concordia.prefabs.entity import basic as basic_entity
from concordia.typing import entity as entity_lib
import numpy as np

from experiments.non_verbal_minecraft.configs import shared_build_area
from experiments.non_verbal_minecraft import evaluation_taxonomy
from experiments.non_verbal_minecraft.personas import agents as agent_personas


VISIBLE_ACTION_SPEC = entity_lib.free_action_spec(
    call_to_action=shared_build_area.OBSERVER_ACTION_PROMPT,
    tag="minecraft_visible_action",
)

TARGET_REACTION_SPEC = entity_lib.free_action_spec(
    call_to_action=shared_build_area.TARGET_REACTION_PROMPT,
    tag="minecraft_visible_action",
)


def _visible_action_spec(scenario) -> entity_lib.ActionSpec:
  return entity_lib.free_action_spec(
      call_to_action=scenario.OBSERVER_ACTION_PROMPT,
      tag="minecraft_visible_action",
  )


def _target_reaction_spec(scenario) -> entity_lib.ActionSpec:
  return entity_lib.free_action_spec(
      call_to_action=scenario.TARGET_REACTION_PROMPT,
      tag="minecraft_visible_action",
  )


@dataclasses.dataclass(frozen=True)
class ExperimentResult:
  """Result bundle returned by run_simulation."""

  raw_log: list[Mapping[str, Any]]
  structured_log: dict[str, Any]


def _memory_bank(
    embedder: Callable[[str], np.ndarray],
) -> basic_associative_memory.AssociativeMemoryBank:
  return basic_associative_memory.AssociativeMemoryBank(
      sentence_embedder=embedder,
      allow_duplicates=True,
  )


def _make_agent(
    name: str,
    model,
    embedder,
    *,
    include_relationship_memories: bool = False,
):
  persona = agent_personas.AGENTS[name]
  memories = agent_personas.memories_for(
      name,
      include_relationship_memories=include_relationship_memories,
  )
  persona_memories = "\n".join(memories)
  goal = (
      f"Role: {persona['Role']}\n"
      f"Motivation: {persona['Motivation']}\n\n"
      f"Stable persona memories:\n{persona_memories}\n\n"
      "Important response constraint: all actions in this study must be "
      "visible Minecraft actions only. Do not use chat or spoken dialogue."
  )
  prefab = basic_entity.Entity(
      params={
          "name": name,
          "goal": goal,
          "randomize_choices": False,
          "prefix_entity_name": True,
      }
  )
  memory_bank = _memory_bank(embedder)
  for memory in memories:
    memory_bank.add(memory)
  return prefab.build(model=model, memory_bank=memory_bank)


def build_agents(
    model,
    embedder,
    *,
    include_relationship_memories: bool = False,
):
  """Build all five fixed agents."""
  return {
      name: _make_agent(
          name,
          model,
          embedder,
          include_relationship_memories=include_relationship_memories,
      )
      for name in agent_personas.AGENTS.keys()
  }


def run_simulation(
    model,
    embedder,
    *,
    include_relationship_memories: bool = False,
    scenario=shared_build_area,
) -> ExperimentResult:
  """Run one controlled Minecraft visible-action incident.

  Morgan's visible incident is scripted so the experimental stimulus is stable.
  Riley and the observers receive only visible Minecraft action
  descriptions, without interpretive labels.
  """
  agents = build_agents(
      model,
      embedder,
      include_relationship_memories=include_relationship_memories,
  )
  raw_log: list[Mapping[str, Any]] = []

  def observe_all(observation: str, recipients: tuple[str, ...]) -> None:
    for name in recipients:
      agents[name].observe(observation)

  setup_observation = (
      f"Scenario: {scenario.PREMISE}\n"
      f"Map layout: {scenario.MINECRAFT_MAP}"
  )
  observe_all(setup_observation, tuple(agents.keys()))
  raw_log.append({
      "step": 1,
      "phase": "spatial_setup",
      "observation": setup_observation,
  })

  normal_actions = getattr(
      scenario,
      "BACKGROUND_PLAYER_ACTIONS",
      {agent_personas.TARGET_NAME: scenario.TARGET_BUILD_ACTION},
  )
  normal_actions_observation = "\n".join(
      f"{name}: {action}" for name, action in normal_actions.items()
  )
  observe_all(normal_actions_observation, tuple(agents.keys()))
  raw_log.append({
      "step": 2,
      "phase": "normal_cooperative_actions",
      "visible_actions": normal_actions,
  })

  target_action = normal_actions.get(
      agent_personas.TARGET_NAME,
      scenario.TARGET_BUILD_ACTION,
  )

  incident = scenario.SCRIPTED_VISIBLE_INCIDENT
  observe_all(incident, tuple(agents.keys()))
  raw_log.append({
      "step": 3,
      "phase": "scripted_visible_incident",
      "actor": agent_personas.SCRIPTED_ACTOR_NAME,
      "visible_action": incident,
      "label_disclosed_to_agents": False,
  })

  observer_actions = {}
  for observer_name in agent_personas.OBSERVER_NAMES:
    action = agents[observer_name].act(_visible_action_spec(scenario))
    observer_actions[observer_name] = action
    raw_log.append({
        "step": 4,
        "phase": "observer_visible_response",
        "actor": observer_name,
        "visible_action": action,
        "agent_log": agents[observer_name].get_last_log(),
    })

  target_reaction = agents[agent_personas.TARGET_NAME].act(
      _target_reaction_spec(scenario)
  )
  raw_log.append({
      "step": 5,
      "phase": "target_visible_response",
      "actor": agent_personas.TARGET_NAME,
      "visible_action": target_reaction,
      "agent_log": agents[agent_personas.TARGET_NAME].get_last_log(),
  })

  structured_log = {
      "project_metadata": scenario.PROJECT_METADATA,
      "scenario_metadata": scenario.SCENARIO_METADATA,
      "ground_truth": scenario.GROUND_TRUTH,
      "evaluation_taxonomy": dict(
          evaluation_taxonomy.SCENARIO_TAXONOMY.get(scenario.SCENARIO_ID, {})
      ),
      "scenario": scenario.NAME,
      "scenario_id": scenario.SCENARIO_ID,
      "description": scenario.DESCRIPTION,
      "agent_names": list(agents.keys()),
      "persona_schema": [
          "Name",
          "Role",
          "Age",
          "Gender",
          "Background",
          "Traits",
          "Motivation",
          "Interaction Style",
          "Skillset",
      ],
      "include_relationship_memories": include_relationship_memories,
      "observer_names": list(agent_personas.OBSERVER_NAMES),
      "target_name": agent_personas.TARGET_NAME,
      "secondary_target_name": agent_personas.SECONDARY_TARGET_NAME,
      "scripted_actor_name": agent_personas.SCRIPTED_ACTOR_NAME,
      "label_disclosed_to_agents": False,
      "minecraft_map": scenario.MINECRAFT_MAP,
      "stimulus": {
          "setup": setup_observation,
          "normal_cooperative_actions": normal_actions,
          "target_action": target_action,
          "scripted_visible_incident": incident,
      },
      "observer_actions": observer_actions,
      "target_reaction": target_reaction,
      "coding_dimensions": [
          "orients_to_target",
          "orients_to_aggressor",
          "repairs_or_restores_build",
          "blocks_or_interrupts_aggressor",
          "returns_or_protects_items",
          "uses_signal_lamp_or_process_signal",
          "avoids_or_withdraws",
          "aligns_with_aggressor",
      ],
      "raw_log": raw_log,
  }

  return ExperimentResult(raw_log=raw_log, structured_log=structured_log)


