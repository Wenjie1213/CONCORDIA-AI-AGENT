"""Compile the best transferable historical run for each scenario.

This script uses the strict scientific migration benchmark to choose the best
run per scenario, then converts each chosen Concordia JSON log into the replay
JSON consumed by mineflayer_replay/replay_runner.js.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from experiments.non_verbal_minecraft.replay.compile_replay import compile_replay


DEFAULT_BENCHMARK_CSV = os.path.join(
    "experiments",
    "non_verbal_minecraft",
    "replay",
    "scientific_migration_benchmark_20x_strict",
    "scientific_migration_run_rows.csv",
)

DEFAULT_OUTPUT_DIR = os.path.join(
    "experiments",
    "non_verbal_minecraft",
    "replay",
    "out",
    "best_transferable_runs",
)


def _as_float(value: Any, default: float = 0.0) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return default


def _as_bool(value: Any) -> bool:
  return str(value).strip().lower() == "true"


def _safe_name(value: str) -> str:
  return value.replace("/", "-").replace("\\", "-").replace(" ", "_")


def _load_rows(path: str) -> list[dict[str, str]]:
  with open(path, newline="", encoding="utf-8") as f:
    return list(csv.DictReader(f))


def _rank_key(row: dict[str, str]) -> tuple[float, float, float, float]:
  return (
      _as_float(row.get("scientific_transferability_score")),
      _as_float(row.get("mean_action_unit_coverage")),
      _as_float(row.get("mean_sequence_fidelity")),
      _as_float(row.get("parseability_rate")),
  )


def select_best_rows(
    rows: list[dict[str, str]],
    *,
    scenario: str | None = None,
    require_should_migrate: bool = True,
    min_score: float = 0.0,
) -> list[dict[str, str]]:
  filtered = []
  for row in rows:
    if scenario and row.get("scenario_id") != scenario:
      continue
    if _as_float(row.get("scientific_transferability_score")) < min_score:
      continue
    filtered.append(row)

  grouped: dict[str, list[dict[str, str]]] = {}
  for row in filtered:
    grouped.setdefault(row.get("scenario_id", "unknown_scenario"), []).append(row)

  best_rows: list[dict[str, str]] = []
  for scenario_id, scenario_rows in sorted(grouped.items()):
    candidates = [row for row in scenario_rows if _as_bool(row.get("should_migrate"))]
    if not candidates and not require_should_migrate:
      candidates = scenario_rows
    if not candidates:
      continue
    best_rows.append(max(candidates, key=_rank_key))
  return best_rows


def _compile_row(row: dict[str, str], output_dir: Path) -> dict[str, Any]:
  run_path = row["run_path"]
  with open(run_path, encoding="utf-8") as f:
    log = json.load(f)

  replay = compile_replay(log, run_path, include_target=True)
  scenario_id = row.get("scenario_id") or replay.get("scenario_id") or "unknown_scenario"
  run_id = row.get("run_id") or replay.get("run_id") or Path(run_path).stem
  replay["selection_metadata"] = {
      "selection_method": "best_strict_scientific_transferability_per_scenario",
      "scientific_transferability_score": _as_float(row.get("scientific_transferability_score")),
      "mean_action_unit_coverage": _as_float(row.get("mean_action_unit_coverage")),
      "mean_sequence_fidelity": _as_float(row.get("mean_sequence_fidelity")),
      "mean_spatial_grounding_rate": _as_float(row.get("mean_spatial_grounding_rate")),
      "migration_recommended": _as_bool(row.get("should_migrate")),
      "decision_reasons": row.get("decision_reasons", ""),
      "source_benchmark_row": row,
  }

  output_path = output_dir / f"{_safe_name(scenario_id)}_best_replay.json"
  output_path.parent.mkdir(parents=True, exist_ok=True)
  with output_path.open("w", encoding="utf-8") as f:
    json.dump(replay, f, indent=2, ensure_ascii=False)

  return {
      "scenario_id": scenario_id,
      "run_id": run_id,
      "run_path": run_path,
      "replay_path": str(output_path),
      "scientific_transferability_score": row.get("scientific_transferability_score", ""),
      "mean_action_unit_coverage": row.get("mean_action_unit_coverage", ""),
      "mean_sequence_fidelity": row.get("mean_sequence_fidelity", ""),
      "mean_spatial_grounding_rate": row.get("mean_spatial_grounding_rate", ""),
      "should_migrate": row.get("should_migrate", ""),
      "timeline_commands": len(replay.get("timeline", [])),
  }


def _write_manifest(output_dir: Path, manifest_rows: list[dict[str, Any]]) -> None:
  csv_path = output_dir / "best_replay_manifest.csv"
  json_path = output_dir / "best_replay_manifest.json"
  fields = [
      "scenario_id",
      "run_id",
      "run_path",
      "replay_path",
      "scientific_transferability_score",
      "mean_action_unit_coverage",
      "mean_sequence_fidelity",
      "mean_spatial_grounding_rate",
      "should_migrate",
      "timeline_commands",
  ]
  with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(manifest_rows)
  with json_path.open("w", encoding="utf-8") as f:
    json.dump({"runs": manifest_rows}, f, indent=2, ensure_ascii=False)


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Compile the best transferable run per scenario into replay JSON."
  )
  parser.add_argument("--benchmark_csv", default=DEFAULT_BENCHMARK_CSV)
  parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR)
  parser.add_argument("--scenario", default=None, help="Optional single scenario_id to compile.")
  parser.add_argument("--min_score", type=float, default=0.0)
  parser.add_argument(
      "--allow_not_recommended",
      action="store_true",
      help="If a scenario has no strict-gate passing run, allow the top-scoring run anyway.",
  )
  args = parser.parse_args()

  rows = _load_rows(args.benchmark_csv)
  best_rows = select_best_rows(
      rows,
      scenario=args.scenario,
      require_should_migrate=not args.allow_not_recommended,
      min_score=args.min_score,
  )
  if not best_rows:
    raise ValueError("No candidate runs matched the selection criteria.")

  output_dir = Path(args.output_dir)
  manifest_rows = [_compile_row(row, output_dir) for row in best_rows]
  _write_manifest(output_dir, manifest_rows)

  print(f"Compiled best replay files: {len(manifest_rows)}")
  print(f"Output dir: {output_dir}")
  for row in manifest_rows:
    print(
        f"{row['scenario_id']}: score={row['scientific_transferability_score']} "
        f"run={row['run_id']}"
    )


if __name__ == "__main__":
  main()
