"""Compile Concordia run JSON files into mineflayer replay traces.

The Concordia experiment logs are natural-language traces. This compiler maps
those traces into a small Minecraft action vocabulary consumed by
mineflayer_replay/replay_runner.js:

  goto, look_at_agent, look_at_block, swing_arm, sneak, stand, place_block,
  dig_block

The mapping is deliberately deterministic and auditable. It records a migration
report with mapped intents, unsupported intents, and primitive coverage.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import Any


def _pos(x: int, y: int = 64, z: int = 0) -> dict[str, int]:
  return {"x": x, "y": y, "z": z}


MAP_SPEC = {
    "minecraft_version": "1.20.1",
    "world_type": "flat",
    "origin": _pos(0, 64, 0),
    "bounds": {
        "min": {"x": -22, "y": 63, "z": -18},
        "max": {"x": 22, "y": 72, "z": 18},
    },
    "viewer": {"agent": "Casey", "port": 3000, "firstPerson": False, "viewDistance": 7},
}


AGENTS = {
    "Morgan": {"role": "scripted_actor", "spawn": _pos(8, 64, 1), "look_at": _pos(0, 64, 1)},
    "Riley": {"role": "target", "spawn": _pos(-3, 64, 1), "look_at": _pos(3, 64, 1)},
    "Casey": {"role": "observer", "spawn": _pos(-7, 64, -5), "look_at": _pos(0, 64, 1)},
    "Taylor": {"role": "observer", "spawn": _pos(0, 64, -6), "look_at": _pos(0, 64, 1)},
    "Jordan": {"role": "observer", "spawn": _pos(7, 64, -5), "look_at": _pos(0, 64, 1)},
}


MARKERS = {
    "group_center": _pos(0, 64, 0),
    "riley_work_area": _pos(-4, 64, 2),
    "riley_safe_area": _pos(-8, 64, 4),
    "riley_spawn": _pos(-3, 64, 1),
    "riley_exit": _pos(-2, 64, 1),
    "morgan_work_area": _pos(5, 64, 2),
    "shared_chest": _pos(0, 64, 4),
    "chest_front": _pos(0, 64, 3),
    "poster_wall": _pos(-5, 65, 5),
    "poster_cover": _pos(-5, 65, 4),
    "barrier_left": _pos(-2, 64, 0),
    "barrier_mid": _pos(-1, 64, 0),
    "barrier_right": _pos(0, 64, 0),
    "morgan_near_riley": _pos(-2, 64, 2),
    "morgan_blocking_exit": _pos(-2, 64, 1),
    "observer_intercept": _pos(-1, 64, 2),
    "observer_support": _pos(-5, 64, 2),
    "observer_report": _pos(3, 64, -6),
    "observer_withdraw": _pos(9, 64, -8),
    "mocking_signal_spot": _pos(1, 64, 2),
    "damaged_block_a": _pos(-4, 64, 3),
    "damaged_block_b": _pos(-3, 64, 3),
    "damaged_block_c": _pos(-4, 65, 3),
    "replacement_block": _pos(-4, 64, 3),
    "spawn_trap_a": _pos(-4, 64, 1),
    "spawn_trap_b": _pos(-2, 64, 1),
    "spawn_trap_c": _pos(-3, 64, 0),
    "spawn_trap_d": _pos(-3, 64, 2),
}


INITIAL_BLOCKS = [
    {"marker": "shared_chest", "block": "chest"},
    {"marker": "poster_wall", "block": "oak_planks"},
    {"marker": "damaged_block_a", "block": "oak_planks"},
    {"marker": "damaged_block_b", "block": "oak_planks"},
    {"marker": "damaged_block_c", "block": "lantern"},
    {"marker": "morgan_work_area", "block": "stone"},
]


def _cmd(t: int, agent: str, cmd: str, **kwargs: Any) -> dict[str, Any]:
  item = {"t": t, "agent": agent, "cmd": cmd}
  item.update(kwargs)
  return item


def _scenario_key(log: dict[str, Any]) -> str:
  return str(log.get("scenario_id") or log.get("scenario") or "").lower()


def _normal_task_timeline(log: dict[str, Any], start: int = 20) -> list[dict[str, Any]]:
  actions = log.get("stimulus", {}).get("normal_cooperative_actions", {})
  if not isinstance(actions, dict):
    actions = {}
  task_targets = {
      "Morgan": "morgan_work_area",
      "Riley": "riley_work_area",
      "Casey": "shared_chest",
      "Taylor": "group_center",
      "Jordan": "poster_wall",
  }
  timeline: list[dict[str, Any]] = []
  for idx, agent in enumerate(["Morgan", "Riley", "Casey", "Taylor", "Jordan"]):
    target = task_targets[agent]
    t = start + idx * 10
    timeline.extend([
        _cmd(t, agent, "goto", target=target, range=2),
        _cmd(t + 4, agent, "look_at_block", target=target),
        _cmd(t + 8, agent, "swing_arm", repeat=1, source_text=actions.get(agent, "")),
    ])
  return timeline


def _incident_timeline(log: dict[str, Any], start: int = 140) -> list[dict[str, Any]]:
  key = _scenario_key(log)
  t = start
  if "chest_access_denial" in key:
    return [
        _cmd(t, "Morgan", "sprint_goto", target="shared_chest", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 14, "Morgan", "place_block", target="chest_front", block="cobblestone"),
        _cmd(t + 28, "Morgan", "stand", ticks=30),
        _cmd(t + 48, "Morgan", "emote_signal", target_agent="Riley", repeat=5, jump=True),
    ]
  if "coordinated_exclusion" in key:
    return [
        _cmd(t, "Morgan", "goto", target="barrier_mid", range=1),
        _cmd(t + 8, "Morgan", "place_block", target="barrier_left", block="oak_planks"),
        _cmd(t + 18, "Morgan", "place_block", target="barrier_mid", block="oak_planks"),
        _cmd(t + 28, "Morgan", "place_block", target="barrier_right", block="oak_planks"),
        _cmd(t + 40, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 52, "Morgan", "goto", target="group_center", range=1),
    ]
  if "following_crowding" in key:
    return [
        _cmd(t, "Morgan", "sprint_goto", target="morgan_near_riley", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 18, "Morgan", "goto", target="riley_work_area", range=1),
        _cmd(t + 30, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 44, "Morgan", "goto", target="riley_exit", range=1),
    ]
  if "personal_build_destruction" in key:
    return [
        _cmd(t, "Morgan", "goto", target="damaged_block_a", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 15, "Morgan", "dig_block", target="damaged_block_a"),
        _cmd(t + 26, "Morgan", "dig_block", target="damaged_block_b"),
        _cmd(t + 38, "Morgan", "swing_arm", repeat=2),
    ]
  if "physical_intimidation" in key:
    return [
        _cmd(t, "Morgan", "sprint_goto", target="morgan_near_riley", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 18, "Morgan", "emote_signal", target_agent="Riley", repeat=6, jump=True),
        _cmd(t + 30, "Morgan", "dig_block", target="damaged_block_c"),
        _cmd(t + 44, "Morgan", "goto", target="morgan_blocking_exit", range=0),
        _cmd(t + 58, "Morgan", "stand", ticks=25),
    ]
  if "poster_covering" in key:
    return [
        _cmd(t, "Morgan", "goto", target="poster_wall", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 16, "Morgan", "place_block", target="poster_cover", block="black_wool"),
        _cmd(t + 30, "Morgan", "swing_arm", repeat=1),
    ]
  if "property_directed_aggression" in key:
    return [
        _cmd(t, "Morgan", "goto", target="damaged_block_a", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 14, "Morgan", "emote_signal", target_agent="Riley", repeat=6, jump=True),
        _cmd(t + 28, "Morgan", "dig_block", target="damaged_block_a"),
        _cmd(t + 40, "Morgan", "dig_block", target="damaged_block_b"),
    ]
  if "repeated_escalation" in key:
    return [
        _cmd(t, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 12, "Morgan", "swing_arm", repeat=1),
        _cmd(t + 26, "Morgan", "goto", target="morgan_near_riley", range=1),
        _cmd(t + 42, "Morgan", "goto", target="morgan_blocking_exit", range=0),
        _cmd(t + 58, "Morgan", "dig_block", target="damaged_block_c"),
        _cmd(t + 72, "Morgan", "emote_signal", target_agent="Riley", repeat=6, jump=True),
    ]
  if "signal_based_mocking" in key:
    return [
        _cmd(t, "Morgan", "goto", target="mocking_signal_spot", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 16, "Morgan", "sneak", state=True, pulse=True, repeat=3),
        _cmd(t + 28, "Morgan", "jump", repeat=1),
        _cmd(t + 38, "Morgan", "emote_signal", target_agent="Riley", repeat=5),
        _cmd(t + 52, "Morgan", "look_at_agent", target="Riley"),
    ]
  if "silent_hostility" in key:
    return [
        _cmd(t, "Morgan", "sprint_goto", target="morgan_near_riley", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
        _cmd(t + 18, "Morgan", "stand", ticks=60),
        _cmd(t + 48, "Morgan", "look_at_agent", target="Riley"),
    ]
  if "social_exclusion" in key:
    return [
        _cmd(t, "Morgan", "goto", target="group_center", range=1),
        _cmd(t + 8, "Morgan", "look_at_agent", target="Casey"),
        _cmd(t + 20, "Morgan", "place_block", target="barrier_mid", block="oak_planks"),
        _cmd(t + 32, "Morgan", "look_at_agent", target="Taylor"),
        _cmd(t + 44, "Morgan", "stand", ticks=30),
    ]
  if "spawn_trapping" in key:
    return [
        _cmd(t, "Morgan", "goto", target="riley_spawn", range=1),
        _cmd(t + 8, "Morgan", "place_block", target="spawn_trap_a", block="cobblestone"),
        _cmd(t + 18, "Morgan", "place_block", target="spawn_trap_b", block="cobblestone"),
        _cmd(t + 28, "Morgan", "place_block", target="spawn_trap_c", block="cobblestone"),
        _cmd(t + 38, "Morgan", "place_block", target="spawn_trap_d", block="cobblestone"),
        _cmd(t + 52, "Morgan", "look_at_agent", target="Riley"),
    ]
  return [
      _cmd(t, "Morgan", "sprint_goto", target="morgan_near_riley", range=1),
      _cmd(t + 8, "Morgan", "look_at_agent", target="Riley"),
      _cmd(t + 16, "Morgan", "swing_arm", repeat=2),
      _cmd(t + 28, "Morgan", "dig_block", target="damaged_block_a"),
      _cmd(t + 42, "Morgan", "stand", ticks=25),
  ]


def _target_for_action(agent: str, text: str) -> str:
  low = text.lower()
  if "morgan" in low or "between" in low or "intercept" in low or "block" in low:
    return "observer_intercept"
  if "riley" in low or "support" in low or "check" in low or "safe" in low:
    return "observer_support"
  if "report" in low or "moderator" in low or "log" in low:
    return "observer_report"
  if "distance" in low or "withdraw" in low or "avoid" in low:
    return "observer_withdraw"
  return {"Casey": "observer_intercept", "Taylor": "group_center", "Jordan": "observer_support", "Riley": "riley_safe_area"}.get(agent, "group_center")


def _block_for_action(text: str) -> str:
  low = text.lower()
  if "poster" in low or "cover" in low:
    return "poster_cover"
  if "chest" in low:
    return "chest_front"
  if "spawn" in low or "trap" in low:
    return "spawn_trap_a"
  if "barrier" in low or "wall" in low or "block" in low:
    return "barrier_mid"
  return "damaged_block_a"


def _repair_block_for_action(text: str) -> str:
  low = text.lower()
  if "poster" in low or "cover" in low:
    return "poster_cover"
  if "chest" in low:
    return "chest_front"
  if "spawn" in low or "trap" in low:
    return "spawn_trap_a"
  return "replacement_block"


def _map_action_to_commands(agent: str, action: str, start: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
  low = str(action or "").lower()
  commands: list[dict[str, Any]] = []
  mapped: list[str] = []
  unsupported: list[str] = []

  def add(intent: str, cmd: dict[str, Any]) -> None:
    mapped.append(intent)
    commands.append(cmd)

  if any(k in low for k in ["approach", "move", "step", "go ", "walk"]):
    add("move_to_relevant_area", _cmd(start, agent, "sprint_goto", target=_target_for_action(agent, low), range=1))
  if any(k in low for k in ["watch", "observe", "look", "monitor", "stare"]):
    add("look_or_monitor", _cmd(start + 6, agent, "look_at_agent", target="Morgan"))
  if any(k in low for k in ["intervene", "between", "stop", "block morgan", "stand between"]):
    add("direct_intervention", _cmd(start + 10, agent, "sprint_goto", target="observer_intercept", range=0))
    add("face_aggressor", _cmd(start + 16, agent, "look_at_agent", target="Morgan"))
    add("visible_stop_signal", _cmd(start + 22, agent, "emote_signal", target_agent="Morgan", repeat=5, jump=True))
  if any(k in low for k in ["support riley", "check on riley", "help riley", "protect riley", "comfort"]):
    add("support_target", _cmd(start + 20, agent, "sprint_goto", target="observer_support", range=1))
    add("face_target", _cmd(start + 26, agent, "look_at_agent", target="Riley"))
    add("support_marker", _cmd(start + 32, agent, "place_marker", target="observer_support", block="white_wool"))
  if any(k in low for k in ["repair", "restore", "replace", "rebuild", "fix"]):
    add("repair_or_restore", _cmd(start + 30, agent, "place_block", target=_repair_block_for_action(low), block="oak_planks"))
  if any(k in low for k in ["remove", "clear", "break", "dig", "unblock"]):
    add("remove_blocking_or_harmful_block", _cmd(start + 34, agent, "dig_block", target=_block_for_action(low)))
  if any(k in low for k in ["barrier", "boundary", "shield", "separate"]):
    add("place_boundary", _cmd(start + 38, agent, "place_block", target="barrier_mid", block="glass"))
    add("boundary_signal", _cmd(start + 44, agent, "emote_signal", target_agent="Morgan", repeat=3))
  if any(k in low for k in ["signal", "gesture", "wave", "raise", "hand"]):
    add("nonverbal_signal", _cmd(start + 42, agent, "emote_signal", target_agent="Morgan", repeat=4, jump=True))
  if any(k in low for k in ["crouch", "sneak"]):
    add("crouch_signal", _cmd(start + 46, agent, "sneak", state=True, pulse=True, repeat=3))
    add("end_crouch_signal", _cmd(start + 58, agent, "jump", repeat=1))
  if any(k in low for k in ["distance", "withdraw", "avoid", "back away", "leave"]):
    add("withdraw_or_keep_distance", _cmd(start + 50, agent, "back_away", target_agent="Morgan", duration_ms=1100))
    add("move_to_safe_distance", _cmd(start + 58, agent, "sprint_goto", target="observer_withdraw", range=1))
  if any(k in low for k in ["report", "log", "moderator", "document", "record"]):
    add("report_or_document", _cmd(start + 54, agent, "sprint_goto", target="observer_report", range=1))
    add("record_signal", _cmd(start + 60, agent, "look_at_agent", target="Morgan"))
  if any(k in low for k in ["continue", "ignore", "remain silent", "silent", "do nothing", "keeps working"]):
    add("continue_or_hold_position", _cmd(start + 64, agent, "turn_away"))
    add("hold_position", _cmd(start + 70, agent, "stand", ticks=30))
  if any(k in low for k in ["align", "join morgan", "copy morgan", "laugh", "mock"]):
    add("align_with_aggressor", _cmd(start + 68, agent, "sprint_goto", target="mocking_signal_spot", range=1))
    add("copy_signal", _cmd(start + 74, agent, "emote_signal", target_agent="Morgan", repeat=4))

  if not commands:
    commands.append(_cmd(start, agent, "look_at_agent", target="Morgan"))
    commands.append(_cmd(start + 8, agent, "stand", ticks=35))
    unsupported.append("no_supported_action_phrase_detected")

  estimated_intents = 1 + sum(token in low for token in ["intervene", "support", "repair", "remove", "report", "withdraw", "watch", "signal", "ignore"])
  primitive_coverage = min(1.0, len(mapped) / max(1, estimated_intents))
  return commands, {
      "agent": agent,
      "source_action": str(action or ""),
      "mapped_intents": mapped,
      "unsupported_intents": unsupported,
      "primitive_count": len(commands),
      "parseable": bool(mapped),
      "primitive_coverage": round(primitive_coverage, 3),
  }


def _response_timeline_and_report(log: dict[str, Any], start: int = 390, include_target: bool = True) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
  actions = log.get("observer_actions", {})
  if not isinstance(actions, dict):
    actions = {}
  ordered: list[tuple[str, str]] = []
  if include_target:
    ordered.append(("Riley", str(log.get("target_reaction") or "")))
  for agent in ["Casey", "Taylor", "Jordan"]:
    ordered.append((agent, str(actions.get(agent) or "")))

  timeline: list[dict[str, Any]] = []
  reports: list[dict[str, Any]] = []
  for idx, (agent, action) in enumerate(ordered):
    commands, report = _map_action_to_commands(agent, action, start + idx * 80)
    for cmd in commands:
      cmd["source_action_excerpt"] = action[:180]
    timeline.extend(commands)
    reports.append(report)
  return timeline, reports


def _migration_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
  if not reports:
    return {"agents_mapped": 0, "parseability_rate": 0.0, "mean_primitive_coverage": 0.0, "total_primitives": 0, "unsupported_intent_count": 0}
  return {
      "agents_mapped": len(reports),
      "parseability_rate": round(sum(1 for row in reports if row["parseable"]) / len(reports), 4),
      "mean_primitive_coverage": round(sum(row["primitive_coverage"] for row in reports) / len(reports), 4),
      "total_primitives": sum(row["primitive_count"] for row in reports),
      "unsupported_intent_count": sum(len(row["unsupported_intents"]) for row in reports),
  }


def compile_replay(log: dict[str, Any], source_path: str, include_target: bool = True) -> dict[str, Any]:
  timeline: list[dict[str, Any]] = []
  timeline.extend(_normal_task_timeline(log))
  timeline.extend(_incident_timeline(log))
  response_timeline, reports = _response_timeline_and_report(log, include_target=include_target)
  timeline.extend(response_timeline)
  timeline = sorted(timeline, key=lambda item: item["t"])
  return {
      "schema": "non_verbal_minecraft_replay_v2",
      "source_json": source_path,
      "scenario_id": log.get("scenario_id"),
      "scenario": log.get("scenario"),
      "run_id": log.get("run_id"),
      "agents": AGENTS,
      "world": MAP_SPEC,
      "markers": MARKERS,
      "initial_blocks": INITIAL_BLOCKS,
      "stimulus": log.get("stimulus", {}),
      "source_actions": {
          "normal_cooperative_actions": log.get("stimulus", {}).get("normal_cooperative_actions", {}),
          "scripted_visible_incident": log.get("stimulus", {}).get("scripted_visible_incident"),
          "observer_actions": log.get("observer_actions", {}),
          "target_reaction": log.get("target_reaction", ""),
      },
      "migration_report": {"summary": _migration_summary(reports), "per_agent": reports},
      "timeline": timeline,
  }


def _find_default_run(result_dir: str, scenario_id: str | None) -> str:
  patterns = [os.path.join(result_dir, "**", "*.json")]
  candidates: list[str] = []
  for pattern in patterns:
    for path in glob.glob(pattern, recursive=True):
      normalized = path.replace("\\", "/")
      if "/llm_judge" in normalized or "/scenario_benchmark" in normalized:
        continue
      if scenario_id and scenario_id not in normalized:
        continue
      candidates.append(path)
  if not candidates:
    raise FileNotFoundError(f"No run JSON found under {result_dir!r} for scenario {scenario_id!r}.")
  return sorted(candidates)[0]


def _default_output_path(log: dict[str, Any], source_path: str) -> str:
  scenario_id = log.get("scenario_id") or "unknown_scenario"
  run_id = log.get("run_id") or Path(source_path).stem
  return os.path.join("experiments", "non_verbal_minecraft", "replay", "out", f"{scenario_id}_{run_id}_replay.json")


def main() -> None:
  parser = argparse.ArgumentParser(description="Compile one non-verbal Minecraft run into replay JSON.")
  parser.add_argument("--input", default=None, help="Path to a single run JSON.")
  parser.add_argument("--scenario_id", default=None, help="Scenario id folder to use when --input is omitted.")
  parser.add_argument("--result_dir", default=os.path.join("experiments", "non_verbal_minecraft", "Result_run_20x_by_scenario"), help="Root containing scenario folders, used when --input is omitted.")
  parser.add_argument("--output", default=None, help="Output replay JSON path. Defaults to replay/out/<scenario>_<run>_replay.json.")
  parser.add_argument("--exclude_target", action="store_true", help="Exclude Riley's target reaction from replay response mapping.")
  args = parser.parse_args()

  input_path = args.input or _find_default_run(args.result_dir, args.scenario_id)
  with open(input_path, encoding="utf-8") as f:
    log = json.load(f)

  replay = compile_replay(log, input_path, include_target=not args.exclude_target)
  output_path = Path(args.output or _default_output_path(log, input_path))
  output_path.parent.mkdir(parents=True, exist_ok=True)
  with output_path.open("w", encoding="utf-8") as f:
    json.dump(replay, f, indent=2, ensure_ascii=False)

  summary = replay["migration_report"]["summary"]
  print(f"Replay trace written to {output_path}")
  print(f"Source run: {input_path}")
  print(f"Timeline commands: {len(replay['timeline'])}")
  print(f"Parseability rate: {summary['parseability_rate']:.2%}")
  print(f"Mean primitive coverage: {summary['mean_primitive_coverage']:.2%}")


if __name__ == "__main__":
  main()
