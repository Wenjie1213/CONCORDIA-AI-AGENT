"""Evaluate whether Concordia action logs are transferable to mineflayer replay.

This benchmark is a pre-migration gate. It does not start Minecraft. It compiles
runs in memory with the same mapper used by compile_replay.py, validates the
resulting primitive timeline, and reports whether each run/scenario is worth
sending to mineflayer/prismarine-viewer.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from experiments.non_verbal_minecraft.replay.compile_replay import compile_replay


SUPPORTED_COMMANDS = {
    "goto",
    "sprint_goto",
    "look_at_agent",
    "look_at_block",
    "swing_arm",
    "emote_signal",
    "sneak",
    "jump",
    "back_away",
    "turn_away",
    "stand",
    "place_block",
    "dig_block",
    "place_marker",
}


def _scenario_from_path(path: str) -> str:
  parts = Path(path).parts
  for part in parts:
    if part.startswith("mc_") and part.endswith("_v1"):
      return part
  return "unknown_scenario"


def _run_id(log: dict[str, Any], path: str) -> str:
  return str(log.get("run_id") or Path(path).stem)


def _read_json(path: str) -> dict[str, Any]:
  with open(path, encoding="utf-8") as f:
    return json.load(f)


def _validate_timeline(replay: dict[str, Any]) -> dict[str, Any]:
  markers = set(replay.get("markers", {}).keys())
  agents = set(replay.get("agents", {}).keys())
  invalid_commands: list[str] = []
  unknown_targets: list[str] = []

  for item in replay.get("timeline", []):
    cmd = item.get("cmd")
    if cmd not in SUPPORTED_COMMANDS:
      invalid_commands.append(str(cmd))
    target = item.get("target")
    if not isinstance(target, str):
      continue
    if cmd == "look_at_agent":
      if target not in agents:
        unknown_targets.append(target)
    elif target not in markers:
      unknown_targets.append(target)

  return {
      "invalid_command_count": len(invalid_commands),
      "unknown_target_count": len(unknown_targets),
      "invalid_commands": sorted(set(invalid_commands)),
      "unknown_targets": sorted(set(unknown_targets)),
      "schema_valid": not invalid_commands and not unknown_targets,
  }


def _threshold_decision(
    summary: dict[str, Any],
    validation: dict[str, Any],
    min_parseability: float,
    min_coverage: float,
    max_unsupported_intent_rate: float,
) -> tuple[bool, list[str]]:
  reasons: list[str] = []
  agents_mapped = max(1, int(summary.get("agents_mapped", 0)))
  unsupported_rate = float(summary.get("unsupported_intent_count", 0)) / agents_mapped

  if float(summary.get("parseability_rate", 0.0)) < min_parseability:
    reasons.append("parseability_below_threshold")
  if float(summary.get("mean_primitive_coverage", 0.0)) < min_coverage:
    reasons.append("primitive_coverage_below_threshold")
  if unsupported_rate > max_unsupported_intent_rate:
    reasons.append("unsupported_intent_rate_above_threshold")
  if not validation.get("schema_valid", False):
    reasons.append("invalid_replay_schema")
  if int(summary.get("total_primitives", 0)) <= 0:
    reasons.append("no_primitives_generated")

  return not reasons, reasons


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
      writer.writerow({key: row.get(key, "") for key in fieldnames})


def _summarize_group(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
  grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
  for row in rows:
    grouped[str(row[group_key])].append(row)

  summary_rows: list[dict[str, Any]] = []
  for group, group_rows in sorted(grouped.items()):
    summary_rows.append({
        group_key: group,
        "runs": len(group_rows),
        "mean_parseability_rate": round(mean(float(r["parseability_rate"]) for r in group_rows), 4),
        "mean_primitive_coverage": round(mean(float(r["mean_primitive_coverage"]) for r in group_rows), 4),
        "mean_unsupported_intent_rate": round(mean(float(r["unsupported_intent_rate"]) for r in group_rows), 4),
        "mean_total_primitives": round(mean(float(r["total_primitives"]) for r in group_rows), 3),
        "schema_valid_rate": round(mean(1.0 if r["schema_valid"] else 0.0 for r in group_rows), 4),
        "migration_recommended_rate": round(mean(1.0 if r["should_migrate"] else 0.0 for r in group_rows), 4),
        "recommended_runs": sum(1 for r in group_rows if r["should_migrate"]),
    })
  return summary_rows


def _summarize_agent_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
  grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
  for row in rows:
    grouped[(str(row["scenario_id"]), str(row["agent"]))].append(row)

  summary_rows: list[dict[str, Any]] = []
  for (scenario_id, agent), group_rows in sorted(grouped.items()):
    summary_rows.append({
        "scenario_id": scenario_id,
        "agent": agent,
        "actions": len(group_rows),
        "parseability_rate": round(mean(1.0 if r["parseable"] else 0.0 for r in group_rows), 4),
        "mean_primitive_coverage": round(mean(float(r["primitive_coverage"]) for r in group_rows), 4),
        "mean_primitive_count": round(mean(float(r["primitive_count"]) for r in group_rows), 3),
        "unsupported_action_rate": round(mean(1.0 if r["unsupported_intents"] else 0.0 for r in group_rows), 4),
    })
  return summary_rows


def evaluate_files(
    paths: list[str],
    include_target: bool,
    min_parseability: float,
    min_coverage: float,
    max_unsupported_intent_rate: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
  run_rows: list[dict[str, Any]] = []
  agent_rows: list[dict[str, Any]] = []

  for path in paths:
    log = _read_json(path)
    replay = compile_replay(log, path, include_target=include_target)
    summary = replay["migration_report"]["summary"]
    validation = _validate_timeline(replay)
    should_migrate, reasons = _threshold_decision(
        summary,
        validation,
        min_parseability,
        min_coverage,
        max_unsupported_intent_rate,
    )
    scenario_id = str(log.get("scenario_id") or _scenario_from_path(path))
    run_id = _run_id(log, path)
    agents_mapped = max(1, int(summary.get("agents_mapped", 0)))
    unsupported_rate = float(summary.get("unsupported_intent_count", 0)) / agents_mapped

    run_rows.append({
        "scenario_id": scenario_id,
        "run_id": run_id,
        "run_path": path,
        "agents_mapped": int(summary.get("agents_mapped", 0)),
        "parseability_rate": float(summary.get("parseability_rate", 0.0)),
        "mean_primitive_coverage": float(summary.get("mean_primitive_coverage", 0.0)),
        "total_primitives": int(summary.get("total_primitives", 0)),
        "unsupported_intent_count": int(summary.get("unsupported_intent_count", 0)),
        "unsupported_intent_rate": round(unsupported_rate, 4),
        "timeline_commands": len(replay.get("timeline", [])),
        "schema_valid": bool(validation["schema_valid"]),
        "invalid_command_count": int(validation["invalid_command_count"]),
        "unknown_target_count": int(validation["unknown_target_count"]),
        "should_migrate": bool(should_migrate),
        "decision_reasons": ";".join(reasons),
    })

    for item in replay["migration_report"]["per_agent"]:
      agent_rows.append({
          "scenario_id": scenario_id,
          "run_id": run_id,
          "run_path": path,
          "agent": item.get("agent", ""),
          "parseable": bool(item.get("parseable", False)),
          "primitive_coverage": float(item.get("primitive_coverage", 0.0)),
          "primitive_count": int(item.get("primitive_count", 0)),
          "mapped_intents": ";".join(item.get("mapped_intents", [])),
          "unsupported_intents": ";".join(item.get("unsupported_intents", [])),
          "source_action": item.get("source_action", ""),
      })

  return run_rows, agent_rows


def main() -> None:
  parser = argparse.ArgumentParser(description="Evaluate action transferability before mineflayer replay migration.")
  parser.add_argument(
      "--input_glob",
      default=os.path.join("experiments", "non_verbal_minecraft", "Result_run_20x_by_scenario", "*", "*", "runs", "*.json"),
      help="Glob for Concordia run JSON files.",
  )
  parser.add_argument(
      "--output_dir",
      default=os.path.join("experiments", "non_verbal_minecraft", "replay", "migration_benchmark"),
      help="Directory for migration benchmark CSV/JSON outputs.",
  )
  parser.add_argument("--exclude_target", action="store_true", help="Exclude Riley target reactions from transferability scoring.")
  parser.add_argument("--min_parseability", type=float, default=0.80, help="Minimum run parseability rate required for migration recommendation.")
  parser.add_argument("--min_coverage", type=float, default=0.60, help="Minimum mean primitive coverage required for migration recommendation.")
  parser.add_argument("--max_unsupported_intent_rate", type=float, default=0.20, help="Maximum unsupported intent count per mapped agent.")
  args = parser.parse_args()

  paths = sorted(glob.glob(args.input_glob, recursive=True))
  if not paths:
    raise FileNotFoundError(f"No input JSON files matched {args.input_glob!r}")

  run_rows, agent_rows = evaluate_files(
      paths,
      include_target=not args.exclude_target,
      min_parseability=args.min_parseability,
      min_coverage=args.min_coverage,
      max_unsupported_intent_rate=args.max_unsupported_intent_rate,
  )

  out = Path(args.output_dir)
  out.mkdir(parents=True, exist_ok=True)

  run_fields = [
      "scenario_id",
      "run_id",
      "run_path",
      "agents_mapped",
      "parseability_rate",
      "mean_primitive_coverage",
      "total_primitives",
      "unsupported_intent_count",
      "unsupported_intent_rate",
      "timeline_commands",
      "schema_valid",
      "invalid_command_count",
      "unknown_target_count",
      "should_migrate",
      "decision_reasons",
  ]
  agent_fields = [
      "scenario_id",
      "run_id",
      "run_path",
      "agent",
      "parseable",
      "primitive_coverage",
      "primitive_count",
      "mapped_intents",
      "unsupported_intents",
      "source_action",
  ]
  scenario_fields = [
      "scenario_id",
      "runs",
      "mean_parseability_rate",
      "mean_primitive_coverage",
      "mean_unsupported_intent_rate",
      "mean_total_primitives",
      "schema_valid_rate",
      "migration_recommended_rate",
      "recommended_runs",
  ]
  agent_summary_fields = [
      "scenario_id",
      "agent",
      "actions",
      "parseability_rate",
      "mean_primitive_coverage",
      "mean_primitive_count",
      "unsupported_action_rate",
  ]

  scenario_rows = _summarize_group(run_rows, "scenario_id")
  agent_summary_rows = _summarize_agent_rows(agent_rows)
  overall = {
      "input_files": len(paths),
      "include_target": not args.exclude_target,
      "thresholds": {
          "min_parseability": args.min_parseability,
          "min_coverage": args.min_coverage,
          "max_unsupported_intent_rate": args.max_unsupported_intent_rate,
      },
      "overall_parseability_rate": round(mean(float(r["parseability_rate"]) for r in run_rows), 4),
      "overall_primitive_coverage": round(mean(float(r["mean_primitive_coverage"]) for r in run_rows), 4),
      "overall_schema_valid_rate": round(mean(1.0 if r["schema_valid"] else 0.0 for r in run_rows), 4),
      "overall_migration_recommended_rate": round(mean(1.0 if r["should_migrate"] else 0.0 for r in run_rows), 4),
      "recommended_runs": sum(1 for r in run_rows if r["should_migrate"]),
      "not_recommended_runs": sum(1 for r in run_rows if not r["should_migrate"]),
  }

  _write_csv(out / "migration_run_rows.csv", run_rows, run_fields)
  _write_csv(out / "migration_agent_rows.csv", agent_rows, agent_fields)
  _write_csv(out / "migration_scenario_summary.csv", scenario_rows, scenario_fields)
  _write_csv(out / "migration_agent_summary.csv", agent_summary_rows, agent_summary_fields)

  manifest = {
      "overall": overall,
      "recommended_run_paths": [r["run_path"] for r in run_rows if r["should_migrate"]],
      "not_recommended_run_paths": [r["run_path"] for r in run_rows if not r["should_migrate"]],
  }
  with (out / "migration_summary.json").open("w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

  print(f"Evaluated runs: {overall['input_files']}")
  print(f"Overall parseability rate: {overall['overall_parseability_rate']:.2%}")
  print(f"Overall primitive coverage: {overall['overall_primitive_coverage']:.2%}")
  print(f"Migration recommended: {overall['overall_migration_recommended_rate']:.2%} ({overall['recommended_runs']}/{overall['input_files']})")
  print(f"Outputs written to: {out}")


if __name__ == "__main__":
  main()
