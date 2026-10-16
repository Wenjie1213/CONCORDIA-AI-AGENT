"""Compile scenario-level Minecraft playback independent of saved run results.

Modes:
- none: show setup, normal tasks, and Morgan's scripted incident only.
- observe_only: additionally show Riley/observers visually observing the incident.
- default_response: use fixed scripted visible responses for demo playback.
- llm_response: call the existing Concordia LLM agents once, map their generated
  target/observer responses into mineflayer primitives, and save the generated
  response log inside the playback JSON.

The output is consumed by mineflayer_replay/replay_runner.js.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from experiments.non_verbal_minecraft.configs.scenario_registry import SCENARIOS
from experiments.non_verbal_minecraft.replay.compile_replay import (
    AGENTS,
    INITIAL_BLOCKS,
    MAP_SPEC,
    MARKERS,
    _cmd,
    _incident_timeline,
    _map_action_to_commands,
    _normal_task_timeline,
    _response_timeline_and_report,
)


OBSERVER_MODES = ("none", "observe_only", "default_response", "llm_response")

DEFAULT_OBSERVER_ACTIONS = {
    "Riley": (
        "Riley steps back to a clear safe area, turns to face Morgan and the "
        "affected build area, and holds position where the incident remains visible."
    ),
    "Casey": (
        "Casey moves to an open spot between Riley and Morgan, faces Morgan, "
        "then turns toward Riley to show visible support."
    ),
    "Taylor": (
        "Taylor moves to the observer line, watches Morgan and Riley, and "
        "holds position to document the visible sequence."
    ),
    "Jordan": (
        "Jordan moves beside Riley, looks at the affected block or path, and "
        "uses a visible hand signal before holding position."
    ),
}


def _scenario_modules_by_id() -> dict[str, Any]:
  modules: dict[str, Any] = {}
  for short_name, module in SCENARIOS.items():
    modules[short_name] = module
    scenario_id = getattr(module, "SCENARIO_ID", None)
    if scenario_id:
      modules[scenario_id] = module
  return modules


def _load_scenario(identifier: str) -> Any:
  modules = _scenario_modules_by_id()
  if identifier not in modules:
    available = sorted(k for k in modules if k.startswith("mc_"))
    raise ValueError(
        f"Unknown scenario {identifier!r}. Available scenario ids: "
        + ", ".join(available)
    )
  return modules[identifier]


def _scenario_log(module: Any) -> dict[str, Any]:
  background = getattr(module, "BACKGROUND_PLAYER_ACTIONS", {})
  return {
      "schema": "non_verbal_minecraft_scenario_source_v1",
      "scenario_id": getattr(module, "SCENARIO_ID", "unknown_scenario"),
      "scenario": getattr(module, "NAME", "Unknown scenario"),
      "scenario_description": getattr(module, "DESCRIPTION", ""),
      "stimulus": {
          "setup": getattr(module, "PREMISE", ""),
          "normal_cooperative_actions": background,
          "scripted_visible_incident": getattr(module, "SCRIPTED_VISIBLE_INCIDENT", ""),
          "minecraft_map": getattr(module, "MINECRAFT_MAP", {}),
      },
      "ground_truth": getattr(module, "GROUND_TRUTH", {}),
      "metadata": getattr(module, "SCENARIO_METADATA", {}),
  }


def _observation_timeline(start: int = 330) -> list[dict[str, Any]]:
  return [
      _cmd(start, "Riley", "look_at_agent", target="Morgan", phase="observation"),
      _cmd(start + 8, "Casey", "look_at_agent", target="Morgan", phase="observation"),
      _cmd(start + 16, "Taylor", "look_at_agent", target="Morgan", phase="observation"),
      _cmd(start + 24, "Jordan", "look_at_agent", target="Morgan", phase="observation"),
      _cmd(start + 38, "Casey", "look_at_agent", target="Riley", phase="observation"),
      _cmd(start + 46, "Taylor", "look_at_agent", target="Riley", phase="observation"),
      _cmd(start + 54, "Jordan", "look_at_agent", target="Riley", phase="observation"),
      _cmd(start + 70, "Riley", "stand", ticks=25, phase="observation"),
      _cmd(start + 76, "Casey", "stand", ticks=25, phase="observation"),
      _cmd(start + 82, "Taylor", "stand", ticks=25, phase="observation"),
      _cmd(start + 88, "Jordan", "stand", ticks=25, phase="observation"),
  ]


def _default_response_timeline(start: int = 430) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
  timeline: list[dict[str, Any]] = []
  reports: list[dict[str, Any]] = []
  for idx, (agent, action) in enumerate(DEFAULT_OBSERVER_ACTIONS.items()):
    commands, report = _map_action_to_commands(agent, action, start + idx * 70)
    for command in commands:
      command["phase"] = "scripted_default_response"
      command["source_action_excerpt"] = action
    timeline.extend(commands)
    reports.append(report)
  return timeline, reports


def _validate_api_key(api_key: str | None) -> None:
  if not api_key:
    return
  try:
    api_key.encode("ascii")
  except UnicodeEncodeError as exc:
    raise ValueError(
        "Invalid OpenAI API key: the key contains non-ASCII characters. "
        "Set OPENAI_API_KEY to the real key, not placeholder text such as '你的 API key'."
    ) from exc
  if "你的" in api_key or "API key" in api_key:
    raise ValueError(
        "Invalid OpenAI API key: it looks like placeholder text. "
        "Use PowerShell like: $env:OPENAI_API_KEY=\"sk-...\""
    )


def _condition_label(
    model_name: str,
    use_dummy_embedder: bool,
    include_relationship_memories: bool,
) -> str:
  model = str(model_name).replace("/", "-").replace("\\", "-")
  embedder = "dummyembed" if use_dummy_embedder else "realembed"
  relmem = "relmem" if include_relationship_memories else "no-relmem"
  return f"{model}_{embedder}_{relmem}"


def _run_llm_response_simulation(
    module: Any,
    *,
    api_type: str,
    model_name: str,
    api_key: str | None,
    disable_language_model: bool,
    use_dummy_embedder: bool,
    include_relationship_memories: bool,
) -> dict[str, Any]:
  """Generate Riley/observer responses using the existing Concordia agents."""
  from argparse import Namespace

  from experiments.non_verbal_minecraft import benchmark
  from experiments.non_verbal_minecraft import run as single_run
  from experiments.non_verbal_minecraft import simulation

  if not disable_language_model:
    _validate_api_key(api_key)

  model_args = Namespace(
      api_type=api_type,
      model_name=model_name,
      api_key=api_key,
      disable_language_model=disable_language_model,
      use_dummy_embedder=use_dummy_embedder,
      include_relationship_memories=include_relationship_memories,
  )
  model, embedder = single_run.setup_model(model_args)
  result = simulation.run_simulation(
      model=model,
      embedder=embedder,
      include_relationship_memories=include_relationship_memories,
      scenario=module,
  )
  log = result.structured_log
  log["run_id"] = f"viewer_llm_response_{_condition_label(model_name, use_dummy_embedder, include_relationship_memories)}"
  log["condition"] = _condition_label(
      model_name,
      use_dummy_embedder,
      include_relationship_memories,
  )
  log["use_dummy_embedder"] = use_dummy_embedder
  log["benchmark"] = benchmark.evaluate_log(log)
  return log


def compile_scenario_playback(
    scenario: str,
    observer_mode: str = "observe_only",
    *,
    api_type: str = "openai",
    model_name: str = "gpt-4o",
    api_key: str | None = None,
    disable_language_model: bool = False,
    use_dummy_embedder: bool = False,
    include_relationship_memories: bool = False,
) -> dict[str, Any]:
  module = _load_scenario(scenario)
  log = _scenario_log(module)

  timeline: list[dict[str, Any]] = []
  normal = _normal_task_timeline(log)
  for item in normal:
    item["phase"] = "normal_cooperative_activity"
  incident = _incident_timeline(log)
  for item in incident:
    item["phase"] = "scripted_non_verbal_incident"

  timeline.extend(normal)
  timeline.extend(incident)

  response_reports: list[dict[str, Any]] = []
  llm_response_log: dict[str, Any] | None = None

  if observer_mode == "none":
    pass
  elif observer_mode == "observe_only":
    timeline.extend(_observation_timeline())
  elif observer_mode == "default_response":
    timeline.extend(_observation_timeline())
    response_timeline, response_reports = _default_response_timeline()
    timeline.extend(response_timeline)
  elif observer_mode == "llm_response":
    timeline.extend(_observation_timeline())
    llm_response_log = _run_llm_response_simulation(
        module,
        api_type=api_type,
        model_name=model_name,
        api_key=api_key,
        disable_language_model=disable_language_model,
        use_dummy_embedder=use_dummy_embedder,
        include_relationship_memories=include_relationship_memories,
    )
    response_timeline, response_reports = _response_timeline_and_report(
        llm_response_log,
        start=430,
        include_target=True,
    )
    for command in response_timeline:
      command["phase"] = "llm_generated_response"
    timeline.extend(response_timeline)
  else:
    raise ValueError(f"observer_mode must be one of: {', '.join(OBSERVER_MODES)}")

  timeline = sorted(timeline, key=lambda item: item["t"])
  return {
      "schema": "non_verbal_minecraft_scenario_playback_v1",
      "playback_type": "scenario_level_experiment_visualization",
      "scenario_id": log["scenario_id"],
      "scenario": log["scenario"],
      "run_id": f"scenario_playback_{observer_mode}",
      "source_json": None,
      "observer_mode": observer_mode,
      "agents": AGENTS,
      "world": MAP_SPEC,
      "markers": MARKERS,
      "initial_blocks": INITIAL_BLOCKS,
      "stimulus": log["stimulus"],
      "ground_truth_for_researcher_only": log["ground_truth"],
      "metadata": log["metadata"],
      "source_actions": {
          "normal_cooperative_actions": log["stimulus"]["normal_cooperative_actions"],
          "scripted_visible_incident": log["stimulus"]["scripted_visible_incident"],
          "observer_mode": observer_mode,
          "default_observer_actions": DEFAULT_OBSERVER_ACTIONS if observer_mode == "default_response" else {},
          "llm_observer_actions": llm_response_log.get("observer_actions", {}) if llm_response_log else {},
          "llm_target_reaction": llm_response_log.get("target_reaction", "") if llm_response_log else "",
      },
      "visualization_note": (
          "This file visualizes the controlled scenario procedure. In llm_response "
          "mode, Riley and observer responses are generated once by the existing "
          "Concordia LLM agents, mapped to Minecraft primitives, and then executed "
          "by mineflayer. The viewer visualizes the resulting action trace."
      ),
      "llm_response_log": llm_response_log,
      "migration_report": {
          "summary": {
              "run_dependent": observer_mode == "llm_response",
              "llm_generated": observer_mode == "llm_response",
              "agents_mapped": len(response_reports),
              "observer_mode": observer_mode,
              "model_name": model_name if observer_mode == "llm_response" else None,
              "use_dummy_embedder": use_dummy_embedder if observer_mode == "llm_response" else None,
          },
          "per_agent": response_reports,
      },
      "timeline": timeline,
  }


def _default_output_path(scenario_id: str, observer_mode: str) -> str:
  return os.path.join(
      "experiments",
      "non_verbal_minecraft",
      "replay",
      "out",
      f"{scenario_id}_scenario_playback_{observer_mode}.json",
  )


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Compile a scenario-level playback JSON for prismarine-viewer visualization."
  )
  parser.add_argument(
      "scenario",
      help="Scenario id such as mc_physical_intimidation_v1, or short name such as physical_intimidation.",
  )
  parser.add_argument(
      "--observer_mode",
      choices=OBSERVER_MODES,
      default="observe_only",
      help="How much post-incident observer behavior to generate for visualization.",
  )
  parser.add_argument("--output", default=None, help="Output playback JSON path.")
  parser.add_argument("--api_type", default="openai")
  parser.add_argument("--model_name", default="gpt-4o")
  parser.add_argument("--api_key", default=os.environ.get("OPENAI_API_KEY"))
  parser.add_argument("--disable_language_model", action="store_true")
  parser.add_argument("--use_dummy_embedder", action="store_true")
  parser.add_argument("--include_relationship_memories", action="store_true")
  args = parser.parse_args()

  playback = compile_scenario_playback(
      args.scenario,
      args.observer_mode,
      api_type=args.api_type,
      model_name=args.model_name,
      api_key=args.api_key,
      disable_language_model=args.disable_language_model,
      use_dummy_embedder=args.use_dummy_embedder,
      include_relationship_memories=args.include_relationship_memories,
  )
  output = Path(args.output or _default_output_path(playback["scenario_id"], args.observer_mode))
  output.parent.mkdir(parents=True, exist_ok=True)
  with output.open("w", encoding="utf-8") as f:
    json.dump(playback, f, indent=2, ensure_ascii=False)

  print(f"Scenario playback written to {output}")
  print(f"Scenario: {playback['scenario_id']}")
  print(f"Observer mode: {args.observer_mode}")
  print(f"Timeline commands: {len(playback['timeline'])}")
  if args.observer_mode == "llm_response":
    summary = playback["llm_response_log"].get("benchmark", {}) if playback["llm_response_log"] else {}
    print("LLM-generated actions:")
    for name, action in playback["source_actions"].get("llm_observer_actions", {}).items():
      print(f"  {name}: {action}")
    target = playback["source_actions"].get("llm_target_reaction", "")
    print(f"  Riley: {target}")
    if summary:
      print(f"Recognition success rate: {summary.get('recognition_success_rate', 0):.2%}")


if __name__ == "__main__":
  main()

