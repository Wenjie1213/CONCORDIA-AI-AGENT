"""Run all registered Minecraft non-verbal abuse scenarios once or repeatedly.

Usage:
  python -m experiments.non_verbal_minecraft.run_all \
    --num_runs=5 \
    --api_type=openai \
    --model_name=gpt-4o \
    --api_key $env:OPENAI_API_KEY
"""

import argparse
from collections import Counter
import csv
import datetime
import json
import os
from typing import Any

from experiments.non_verbal_minecraft import benchmark
from experiments.non_verbal_minecraft.configs import scenario_registry
from experiments.non_verbal_minecraft import run as single_run
from experiments.non_verbal_minecraft import simulation

def _condition_label(args) -> str:
  model = str(args.model_name).replace("/", "-").replace("\\", "-")
  embedder = "dummyembed" if args.use_dummy_embedder else "realembed"
  relmem = "relmem" if args.include_relationship_memories else "no-relmem"
  return f"{model}_{embedder}_{relmem}"

def _save_json(data: dict[str, Any], path: str) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _aggregate_all(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
  total_observers = sum(item["observer_count"] for item in evaluations)
  total_success = sum(item["recognition_success_count"] for item in evaluations)
  category_counts = Counter()
  scenario_success: dict[str, list[float]] = {}
  for evaluation in evaluations:
    category_counts.update(evaluation["category_counts"])
    scenario = str(evaluation.get("scenario"))
    scenario_success.setdefault(scenario, []).append(
        evaluation["recognition_success_rate"]
    )
  return {
      "observer_decisions": total_observers,
      "recognition_success_count": total_success,
      "recognition_success_rate": (
          total_success / total_observers if total_observers else 0.0
      ),
      "category_counts": dict(category_counts),
      "scenario_mean_success_rate": {
          scenario: sum(values) / len(values)
          for scenario, values in sorted(scenario_success.items())
      },
  }


def _write_scenario_summary_csv(
    evaluations: list[dict[str, Any]], path: str
) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  scenario_evaluations: dict[str, list[dict[str, Any]]] = {}
  for evaluation in evaluations:
    scenario = str(evaluation.get("scenario"))
    scenario_evaluations.setdefault(scenario, []).append(evaluation)

  fieldnames = [
      "scenario",
      "num_runs",
      "observer_decisions",
      "recognition_success_count",
      "recognition_success_rate",
      "direct_intervention",
      "repair_or_support",
      "process_signal",
      "avoidance",
      "aligns_with_aggressor",
      "other",
      "target_direct_intervention",
      "target_repair_or_support",
      "target_process_signal",
      "target_avoidance",
      "target_aligns_with_aggressor",
      "target_other",
  ]
  with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for scenario, scenario_items in sorted(scenario_evaluations.items()):
      summary = benchmark.aggregate_evaluations(scenario_items)
      category_counts = summary["category_counts"]
      target_category_counts = summary["target_category_counts"]
      writer.writerow({
          "scenario": scenario,
          "num_runs": len(scenario_items),
          "observer_decisions": summary["observer_decisions"],
          "recognition_success_count": summary["recognition_success_count"],
          "recognition_success_rate": summary["recognition_success_rate"],
          "direct_intervention": category_counts.get("direct_intervention", 0),
          "repair_or_support": category_counts.get("repair_or_support", 0),
          "process_signal": category_counts.get("process_signal", 0),
          "avoidance": category_counts.get("avoidance", 0),
          "aligns_with_aggressor": category_counts.get(
              "aligns_with_aggressor", 0
          ),
          "other": category_counts.get("other", 0),
          "target_direct_intervention": target_category_counts.get(
              "direct_intervention", 0
          ),
          "target_repair_or_support": target_category_counts.get(
              "repair_or_support", 0
          ),
          "target_process_signal": target_category_counts.get(
              "process_signal", 0
          ),
          "target_avoidance": target_category_counts.get("avoidance", 0),
          "target_aligns_with_aggressor": target_category_counts.get(
              "aligns_with_aggressor", 0
          ),
          "target_other": target_category_counts.get("other", 0),
      })


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Run all Minecraft non-verbal action scenarios."
  )
  parser.add_argument("--num_runs", type=int, default=1)
  parser.add_argument("--api_type", default="openai")
  parser.add_argument("--model_name", default="gpt-4o")
  parser.add_argument("--api_key", default=None)
  parser.add_argument("--disable_language_model", action="store_true")
  parser.add_argument("--use_dummy_embedder", action="store_true")
  parser.add_argument(
      "--include_relationship_memories",
      action="store_true",
      help="Include fixed prior relationship memories as an experimental condition.",
  )
  parser.add_argument(
      "--output_dir",
      default=os.path.join("experiments", "non_verbal_minecraft", "results"),
  )
  args = parser.parse_args()

  if args.num_runs < 1:
    raise ValueError("--num_runs must be at least 1.")

  model, embedder = single_run.setup_model(args)
  batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  condition = _condition_label(args)
  all_evaluations = []

  scenario_names = sorted(scenario_registry.SCENARIOS.keys())
  print(
      f"Running {len(scenario_names)} scenarios x {args.num_runs} run(s) "
      f"for batch {batch_id}."
  )

  for scenario_name in scenario_names:
    scenario = scenario_registry.SCENARIOS[scenario_name]
    scenario_dir = os.path.join(args.output_dir, scenario.SCENARIO_ID)
    print(f"\nScenario: {scenario_name} ({scenario.SCENARIO_ID})")
    for index in range(1, args.num_runs + 1):
      run_id = f"{batch_id}_{condition}_{scenario_name}_{index:03d}"
      print(f"  [{index}/{args.num_runs}] {run_id}")
      result = simulation.run_simulation(
          model=model,
          embedder=embedder,
          include_relationship_memories=args.include_relationship_memories,
          scenario=scenario,
      )
      log = result.structured_log
      log["run_id"] = run_id
      evaluation = benchmark.evaluate_log(log)
      log["benchmark"] = evaluation
      all_evaluations.append(evaluation)

      path = os.path.join(
          scenario_dir,
          f"minecraft_non_verbal_{scenario.SCENARIO_ID}_{condition}_{batch_id}_{index:03d}.json",
      )
      _save_json(log, path)

  summary = _aggregate_all(all_evaluations)
  summary["batch_id"] = batch_id
  summary["condition"] = condition
  summary["num_runs_per_scenario"] = args.num_runs
  summary["scenario_count"] = len(scenario_names)
  summary["scenarios"] = scenario_names
  summary["model_name"] = args.model_name
  summary["api_type"] = args.api_type
  summary["use_dummy_embedder"] = args.use_dummy_embedder
  summary["include_relationship_memories"] = args.include_relationship_memories

  summary_path = os.path.join(
      args.output_dir,
      f"all_scenarios_summary_{condition}_{batch_id}.json",
  )
  observer_csv_path = os.path.join(
      args.output_dir,
      f"all_scenarios_observer_responses_{condition}_{batch_id}.csv",
  )
  scenario_csv_path = os.path.join(
      args.output_dir,
      f"all_scenarios_scenario_summary_{condition}_{batch_id}.csv",
  )
  _save_json({"summary": summary, "evaluations": all_evaluations}, summary_path)
  benchmark.write_csv_rows(all_evaluations, observer_csv_path)
  _write_scenario_summary_csv(all_evaluations, scenario_csv_path)

  print("\nAll scenarios finished.")
  print(f"Summary written to {summary_path}")
  print(f"Observer CSV written to {observer_csv_path}")
  print(f"Scenario summary CSV written to {scenario_csv_path}")
  print(
      "Overall recognition success rate: "
      f"{summary['recognition_success_rate']:.2%} "
      f"({summary['recognition_success_count']}/"
      f"{summary['observer_decisions']})"
  )


if __name__ == "__main__":
  main()

