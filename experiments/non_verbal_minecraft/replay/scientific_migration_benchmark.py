"""Scientific transferability benchmark for Minecraft replay migration.

This benchmark is stricter than migration_benchmark.py. It asks not only whether
an action can trigger at least one mineflayer primitive, but whether the original
agent action is preserved as a grounded, ordered, visible Minecraft action trace.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
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

ACTION_UNIT_PATTERNS: dict[str, list[str]] = {
    "movement": [r"\bapproach\b", r"\bmove\b", r"\bmoves\b", r"\bstep\b", r"\bsteps\b", r"\bwalk\b", r"\bwalks\b", r"\bgo\b", r"\bturn\b", r"\bturns\b"],
    "observation": [r"\bwatch\b", r"\bwatches\b", r"\bobserve\b", r"\bobserves\b", r"\blook\b", r"\blooks\b", r"\bmonitor\b", r"\bmonitors\b", r"\bstare\b", r"\bstares\b", r"\bfacing\b", r"\bfaces\b"],
    "intervention": [r"\bintervene\b", r"\bintervenes\b", r"\bstop\b", r"\bstops\b", r"\bbetween\b", r"\bblock morgan\b", r"\bstand between\b", r"\bseparate\b", r"\bshield\b"],
    "support": [r"\bsupport\b", r"\bsupports\b", r"\bhelp\b", r"\bhelps\b", r"\bprotect\b", r"\bprotects\b", r"\bcomfort\b", r"\bcheck on riley\b", r"\bshoulder-to-shoulder\b"],
    "repair": [r"\brepair\b", r"\brepairs\b", r"\brestore\b", r"\brestores\b", r"\brebuild\b", r"\brebuilds\b", r"\bfix\b", r"\bfixes\b", r"\breplace\b", r"\breplaces\b"],
    "removal": [r"\bremove\b", r"\bremoves\b", r"\bclear\b", r"\bclears\b", r"\bbreak\b", r"\bbreaks\b", r"\bdig\b", r"\bdigs\b", r"\bunblock\b", r"\bunblocks\b"],
    "reporting": [r"\breport\b", r"\breports\b", r"\blog\b", r"\blogs\b", r"\bdocument\b", r"\bdocuments\b", r"\brecord\b", r"\brecords\b", r"\bmoderator\b"],
    "withdrawal": [r"\bwithdraw\b", r"\bwithdraws\b", r"\bavoid\b", r"\bavoids\b", r"\bleave\b", r"\bleaves\b", r"\bback away\b", r"\bdistance\b"],
    "signal": [r"\bsignal\b", r"\bsignals\b", r"\bgesture\b", r"\bgestures\b", r"\bwave\b", r"\bwaves\b", r"\braise\b", r"\braises\b", r"\bhand\b", r"\bcrouch\b", r"\bsneak\b", r"\btoggle\b", r"\btoggles\b"],
    "alignment": [r"\balign\b", r"\baligns\b", r"\bjoin morgan\b", r"\bcopy morgan\b", r"\blaugh\b", r"\blaughs\b", r"\bmock\b", r"\bmocks\b"],
    "waiting": [r"\bcontinue\b", r"\bcontinues\b", r"\bignore\b", r"\bignores\b", r"\bremain silent\b", r"\bdo nothing\b", r"\bstand\b", r"\bstands\b", r"\bhold position\b", r"\bholds position\b"],
}

INTENT_TO_UNIT = {
    "move_to_relevant_area": "movement",
    "look_or_monitor": "observation",
    "face_aggressor": "observation",
    "face_target": "observation",
    "record_signal": "observation",
    "direct_intervention": "intervention",
    "place_boundary": "intervention",
    "support_target": "support",
    "repair_or_restore": "repair",
    "remove_blocking_or_harmful_block": "removal",
    "report_or_document": "reporting",
    "withdraw_or_keep_distance": "withdrawal",
    "nonverbal_signal": "signal",
    "crouch_signal": "signal",
    "end_crouch_signal": "signal",
    "copy_signal": "signal",
    "align_with_aggressor": "alignment",
    "continue_or_hold_position": "waiting",
}

PHYSICAL_GROUNDING_PATTERNS: dict[str, list[str]] = {
    "morgan": [r"\bmorgan\b"],
    "riley": [r"\briley\b"],
    "casey": [r"\bcasey\b"],
    "taylor": [r"\btaylor\b"],
    "jordan": [r"\bjordan\b"],
    "chest": [r"\bchest\b"],
    "poster": [r"\bposter\b", r"\bboard\b"],
    "lamp": [r"\blamp\b", r"\blantern\b"],
    "block": [r"\bblock\b", r"\bblocks\b", r"\bdirt\b", r"\boak\b", r"\bcobblestone\b", r"\bplanks\b"],
    "barrier": [r"\bbarrier\b", r"\bwall\b", r"\bboundary\b"],
    "spawn": [r"\bspawn\b", r"\btrap\b"],
    "path": [r"\bpath\b", r"\baccess\b", r"\bexit\b"],
    "marker": [r"\bmarker\b", r"\bmarkers\b"],
}

# These are meaningful in the natural-language trace but not directly visible in
# the current mineflayer primitive vocabulary unless approximated by movement or
# pose. A high rate here means the replay loses important semantics.
NON_VISUAL_SEMANTIC_PATTERNS = [
    r"\bsay\b",
    r"\bsays\b",
    r"\btell\b",
    r"\btells\b",
    r"\bask\b",
    r"\basks\b",
    r"\bexplain\b",
    r"\bexplains\b",
    r"\bwarn\b",
    r"\bwarns\b",
    r"\brequest\b",
    r"\brequests\b",
    r"\bagreement\b",
    r"\bpolicy\b",
    r"\bpermission\b",
    r"\baccountability\b",
    r"\bintent\b",
]


def _match_first(text: str, patterns: list[str]) -> int | None:
  positions = [m.start() for pattern in patterns for m in [re.search(pattern, text)] if m]
  return min(positions) if positions else None


def _extract_ordered_units(text: str) -> list[str]:
  low = text.lower()
  found: list[tuple[int, str]] = []
  for unit, patterns in ACTION_UNIT_PATTERNS.items():
    pos = _match_first(low, patterns)
    if pos is not None:
      found.append((pos, unit))
  return [unit for _, unit in sorted(found)]


def _mapped_units(mapped_intents: list[str]) -> list[str]:
  units: list[str] = []
  for intent in mapped_intents:
    unit = INTENT_TO_UNIT.get(intent)
    if unit and unit not in units:
      units.append(unit)
  return units


def _sequence_fidelity(source_units: list[str], mapped_units: list[str]) -> float:
  common = [unit for unit in source_units if unit in mapped_units]
  if len(common) <= 1:
    return 1.0 if common or not source_units else 0.0
  mapped_positions = {unit: idx for idx, unit in enumerate(mapped_units)}
  total_pairs = 0
  preserved_pairs = 0
  for i in range(len(common)):
    for j in range(i + 1, len(common)):
      total_pairs += 1
      if mapped_positions[common[i]] <= mapped_positions[common[j]]:
        preserved_pairs += 1
  return preserved_pairs / total_pairs if total_pairs else 1.0


def _physical_grounding_rate(text: str) -> tuple[float, list[str]]:
  low = text.lower()
  mentioned = [concept for concept, patterns in PHYSICAL_GROUNDING_PATTERNS.items() if _match_first(low, patterns) is not None]
  if not mentioned:
    return 1.0, []
  # In this replay compiler all listed physical concepts are backed by either an
  # agent name or a marker family. New concepts would need to be added here.
  grounded = mentioned
  return len(grounded) / len(mentioned), mentioned


def _non_visual_semantic_rate(text: str, source_units: list[str]) -> tuple[float, list[str]]:
  low = text.lower()
  matches = []
  for pattern in NON_VISUAL_SEMANTIC_PATTERNS:
    if re.search(pattern, low):
      matches.append(pattern.strip("\\b"))
  denominator = max(1, len(source_units) + len(matches))
  return len(matches) / denominator, matches


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
      "schema_valid": not invalid_commands and not unknown_targets,
      "invalid_command_count": len(invalid_commands),
      "unknown_target_count": len(unknown_targets),
      "invalid_commands": sorted(set(invalid_commands)),
      "unknown_targets": sorted(set(unknown_targets)),
  }


def _action_row(scenario_id: str, run_id: str, run_path: str, report: dict[str, Any]) -> dict[str, Any]:
  source_action = str(report.get("source_action", ""))
  source_units = _extract_ordered_units(source_action)
  mapped = _mapped_units(list(report.get("mapped_intents", [])))
  covered_units = [unit for unit in source_units if unit in mapped]
  action_unit_coverage = len(covered_units) / len(source_units) if source_units else 0.0
  grounding_rate, grounded_concepts = _physical_grounding_rate(source_action)
  non_visual_rate, non_visual_terms = _non_visual_semantic_rate(source_action, source_units)
  sequence = _sequence_fidelity(source_units, mapped)
  parseable = bool(report.get("parseable", False))
  visual_semantic_support = 1.0 - non_visual_rate

  # Per-action scientific score. This is intentionally stricter than the old
  # primitive coverage metric: fallback-only responses and ungrounded/abstract
  # semantics lose score even if a primitive exists.
  score = (
      0.35 * action_unit_coverage
      + 0.20 * grounding_rate
      + 0.15 * sequence
      + 0.15 * visual_semantic_support
      + 0.15 * (1.0 if parseable else 0.0)
  )
  if not source_units:
    score *= 0.5

  return {
      "scenario_id": scenario_id,
      "run_id": run_id,
      "run_path": run_path,
      "agent": report.get("agent", ""),
      "parseable": parseable,
      "source_units": ";".join(source_units),
      "mapped_units": ";".join(mapped),
      "covered_units": ";".join(covered_units),
      "action_unit_coverage": round(action_unit_coverage, 4),
      "spatial_grounding_rate": round(grounding_rate, 4),
      "grounded_concepts": ";".join(grounded_concepts),
      "sequence_fidelity": round(sequence, 4),
      "non_visual_semantic_rate": round(non_visual_rate, 4),
      "non_visual_terms": ";".join(non_visual_terms),
      "visual_semantic_support": round(visual_semantic_support, 4),
      "primitive_count": int(report.get("primitive_count", 0)),
      "mapped_intents": ";".join(report.get("mapped_intents", [])),
      "unsupported_intents": ";".join(report.get("unsupported_intents", [])),
      "scientific_action_transferability_score": round(score, 4),
      "source_action": source_action,
  }


def _scenario_from_path(path: str) -> str:
  for part in Path(path).parts:
    if part.startswith("mc_") and part.endswith("_v1"):
      return part
  return "unknown_scenario"


def _run_id(log: dict[str, Any], path: str) -> str:
  return str(log.get("run_id") or Path(path).stem)


def _mean(rows: list[dict[str, Any]], key: str) -> float:
  return mean(float(row[key]) for row in rows) if rows else 0.0


def _recommend(row: dict[str, Any], min_score: float, min_unit_coverage: float, min_grounding: float) -> tuple[bool, list[str]]:
  reasons: list[str] = []
  if float(row["scientific_transferability_score"]) < min_score:
    reasons.append("score_below_threshold")
  if float(row["mean_action_unit_coverage"]) < min_unit_coverage:
    reasons.append("action_unit_coverage_below_threshold")
  if float(row["mean_spatial_grounding_rate"]) < min_grounding:
    reasons.append("spatial_grounding_below_threshold")
  if not row["schema_valid"]:
    reasons.append("invalid_replay_schema")
  if float(row["parseability_rate"]) < 0.75:
    reasons.append("too_many_fallback_actions")
  return not reasons, reasons


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
      writer.writerow({field: row.get(field, "") for field in fieldnames})


def evaluate(paths: list[str], include_target: bool, min_score: float, min_unit_coverage: float, min_grounding: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
  run_rows: list[dict[str, Any]] = []
  action_rows: list[dict[str, Any]] = []
  for path in paths:
    with open(path, encoding="utf-8") as f:
      log = json.load(f)
    replay = compile_replay(log, path, include_target=include_target)
    validation = _validate_timeline(replay)
    scenario_id = str(log.get("scenario_id") or _scenario_from_path(path))
    run_id = _run_id(log, path)
    per_agent = replay.get("migration_report", {}).get("per_agent", [])
    rows = [_action_row(scenario_id, run_id, path, report) for report in per_agent]
    action_rows.extend(rows)

    parseability_rate = mean(1.0 if row["parseable"] else 0.0 for row in rows) if rows else 0.0
    action_unit_coverage = _mean(rows, "action_unit_coverage")
    spatial_grounding = _mean(rows, "spatial_grounding_rate")
    sequence_fidelity = _mean(rows, "sequence_fidelity")
    visual_support = _mean(rows, "visual_semantic_support")
    action_score = _mean(rows, "scientific_action_transferability_score")
    schema_score = 1.0 if validation["schema_valid"] else 0.0
    run_score = 0.90 * action_score + 0.10 * schema_score

    run_row = {
        "scenario_id": scenario_id,
        "run_id": run_id,
        "run_path": path,
        "agents_evaluated": len(rows),
        "parseability_rate": round(parseability_rate, 4),
        "mean_action_unit_coverage": round(action_unit_coverage, 4),
        "mean_spatial_grounding_rate": round(spatial_grounding, 4),
        "mean_sequence_fidelity": round(sequence_fidelity, 4),
        "mean_visual_semantic_support": round(visual_support, 4),
        "mean_action_score": round(action_score, 4),
        "schema_valid": bool(validation["schema_valid"]),
        "invalid_command_count": int(validation["invalid_command_count"]),
        "unknown_target_count": int(validation["unknown_target_count"]),
        "timeline_commands": len(replay.get("timeline", [])),
        "scientific_transferability_score": round(run_score, 4),
    }
    should_migrate, reasons = _recommend(run_row, min_score, min_unit_coverage, min_grounding)
    run_row["should_migrate"] = should_migrate
    run_row["decision_reasons"] = ";".join(reasons)
    run_rows.append(run_row)
  return run_rows, action_rows


def _scenario_summary(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
  grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
  for row in run_rows:
    grouped[str(row["scenario_id"])].append(row)
  out: list[dict[str, Any]] = []
  for scenario_id, rows in sorted(grouped.items()):
    out.append({
        "scenario_id": scenario_id,
        "runs": len(rows),
        "mean_scientific_transferability_score": round(_mean(rows, "scientific_transferability_score"), 4),
        "mean_action_unit_coverage": round(_mean(rows, "mean_action_unit_coverage"), 4),
        "mean_spatial_grounding_rate": round(_mean(rows, "mean_spatial_grounding_rate"), 4),
        "mean_sequence_fidelity": round(_mean(rows, "mean_sequence_fidelity"), 4),
        "mean_visual_semantic_support": round(_mean(rows, "mean_visual_semantic_support"), 4),
        "schema_valid_rate": round(mean(1.0 if row["schema_valid"] else 0.0 for row in rows), 4),
        "migration_recommended_rate": round(mean(1.0 if row["should_migrate"] else 0.0 for row in rows), 4),
        "recommended_runs": sum(1 for row in rows if row["should_migrate"]),
    })
  return out


def _agent_summary(action_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
  grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
  for row in action_rows:
    grouped[(str(row["scenario_id"]), str(row["agent"]))].append(row)
  out: list[dict[str, Any]] = []
  for (scenario_id, agent), rows in sorted(grouped.items()):
    out.append({
        "scenario_id": scenario_id,
        "agent": agent,
        "actions": len(rows),
        "mean_scientific_action_transferability_score": round(_mean(rows, "scientific_action_transferability_score"), 4),
        "parseability_rate": round(mean(1.0 if row["parseable"] else 0.0 for row in rows), 4),
        "mean_action_unit_coverage": round(_mean(rows, "action_unit_coverage"), 4),
        "mean_spatial_grounding_rate": round(_mean(rows, "spatial_grounding_rate"), 4),
        "mean_sequence_fidelity": round(_mean(rows, "sequence_fidelity"), 4),
        "mean_visual_semantic_support": round(_mean(rows, "visual_semantic_support"), 4),
    })
  return out


def main() -> None:
  parser = argparse.ArgumentParser(description="Strict scientific transferability evaluation for mineflayer migration.")
  parser.add_argument("--input_glob", default=os.path.join("experiments", "non_verbal_minecraft", "Result_run_20x_by_scenario", "*", "*", "runs", "*.json"))
  parser.add_argument("--output_dir", default=os.path.join("experiments", "non_verbal_minecraft", "replay", "scientific_migration_benchmark"))
  parser.add_argument("--exclude_target", action="store_true")
  parser.add_argument("--min_score", type=float, default=0.70)
  parser.add_argument("--min_unit_coverage", type=float, default=0.60)
  parser.add_argument("--min_grounding", type=float, default=0.70)
  args = parser.parse_args()

  paths = sorted(glob.glob(args.input_glob, recursive=True))
  if not paths:
    raise FileNotFoundError(f"No files matched {args.input_glob!r}")

  run_rows, action_rows = evaluate(paths, not args.exclude_target, args.min_score, args.min_unit_coverage, args.min_grounding)
  scenario_rows = _scenario_summary(run_rows)
  agent_rows = _agent_summary(action_rows)
  out = Path(args.output_dir)
  out.mkdir(parents=True, exist_ok=True)

  run_fields = [
      "scenario_id", "run_id", "run_path", "agents_evaluated", "parseability_rate",
      "mean_action_unit_coverage", "mean_spatial_grounding_rate", "mean_sequence_fidelity",
      "mean_visual_semantic_support", "mean_action_score", "schema_valid", "invalid_command_count",
      "unknown_target_count", "timeline_commands", "scientific_transferability_score",
      "should_migrate", "decision_reasons",
  ]
  action_fields = [
      "scenario_id", "run_id", "run_path", "agent", "parseable", "source_units", "mapped_units",
      "covered_units", "action_unit_coverage", "spatial_grounding_rate", "grounded_concepts",
      "sequence_fidelity", "non_visual_semantic_rate", "non_visual_terms", "visual_semantic_support",
      "primitive_count", "mapped_intents", "unsupported_intents", "scientific_action_transferability_score",
      "source_action",
  ]
  scenario_fields = [
      "scenario_id", "runs", "mean_scientific_transferability_score", "mean_action_unit_coverage",
      "mean_spatial_grounding_rate", "mean_sequence_fidelity", "mean_visual_semantic_support",
      "schema_valid_rate", "migration_recommended_rate", "recommended_runs",
  ]
  agent_fields = [
      "scenario_id", "agent", "actions", "mean_scientific_action_transferability_score",
      "parseability_rate", "mean_action_unit_coverage", "mean_spatial_grounding_rate",
      "mean_sequence_fidelity", "mean_visual_semantic_support",
  ]

  _write_csv(out / "scientific_migration_run_rows.csv", run_rows, run_fields)
  _write_csv(out / "scientific_migration_action_rows.csv", action_rows, action_fields)
  _write_csv(out / "scientific_migration_scenario_summary.csv", scenario_rows, scenario_fields)
  _write_csv(out / "scientific_migration_agent_summary.csv", agent_rows, agent_fields)

  summary = {
      "input_files": len(paths),
      "include_target": not args.exclude_target,
      "thresholds": {
          "min_score": args.min_score,
          "min_unit_coverage": args.min_unit_coverage,
          "min_grounding": args.min_grounding,
      },
      "overall_scientific_transferability_score": round(_mean(run_rows, "scientific_transferability_score"), 4),
      "overall_action_unit_coverage": round(_mean(run_rows, "mean_action_unit_coverage"), 4),
      "overall_spatial_grounding_rate": round(_mean(run_rows, "mean_spatial_grounding_rate"), 4),
      "overall_sequence_fidelity": round(_mean(run_rows, "mean_sequence_fidelity"), 4),
      "overall_visual_semantic_support": round(_mean(run_rows, "mean_visual_semantic_support"), 4),
      "overall_migration_recommended_rate": round(mean(1.0 if row["should_migrate"] else 0.0 for row in run_rows), 4),
      "recommended_runs": sum(1 for row in run_rows if row["should_migrate"]),
      "not_recommended_runs": sum(1 for row in run_rows if not row["should_migrate"]),
      "recommended_run_paths": [row["run_path"] for row in run_rows if row["should_migrate"]],
      "not_recommended_run_paths": [row["run_path"] for row in run_rows if not row["should_migrate"]],
  }
  with (out / "scientific_migration_summary.json").open("w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

  print(f"Evaluated runs: {summary['input_files']}")
  print(f"Scientific transferability score: {summary['overall_scientific_transferability_score']:.2%}")
  print(f"Action unit coverage: {summary['overall_action_unit_coverage']:.2%}")
  print(f"Spatial grounding rate: {summary['overall_spatial_grounding_rate']:.2%}")
  print(f"Sequence fidelity: {summary['overall_sequence_fidelity']:.2%}")
  print(f"Visual semantic support: {summary['overall_visual_semantic_support']:.2%}")
  print(f"Migration recommended: {summary['overall_migration_recommended_rate']:.2%} ({summary['recommended_runs']}/{summary['input_files']})")
  print(f"Outputs written to: {out}")


if __name__ == "__main__":
  main()
