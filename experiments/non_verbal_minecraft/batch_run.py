"""Run many Minecraft non-verbal action experiment trials and benchmark them.

Usage:
  python -m experiments.non_verbal_minecraft.batch_run \
    --num_runs=20 \
    --api_type=openai \
    --model_name=gpt-4o \
    --api_key $env:OPENAI_API_KEY
"""

import argparse
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


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Run repeated Minecraft non-verbal action trials."
  )
  parser.add_argument("--num_runs", type=int, default=10)
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
      "--scenario",
      default=scenario_registry.DEFAULT_SCENARIO,
      choices=sorted(scenario_registry.SCENARIOS.keys()),
      help="Scenario to run for every trial in this batch.",
  )
  parser.add_argument(
      "--output_dir",
      default=os.path.join(
          "experiments", "non_verbal_minecraft", "batch_results"
      ),
  )
  args = parser.parse_args()

  if args.num_runs < 1:
    raise ValueError("--num_runs must be at least 1.")

  model, embedder = single_run.setup_model(args)
  scenario = scenario_registry.SCENARIOS[args.scenario]
  batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  condition = _condition_label(args)
  batch_dir = os.path.join(
      args.output_dir,
      scenario.SCENARIO_ID,
      f"batch_{args.scenario}_{condition}_{batch_id}",
  )
  run_dir = os.path.join(batch_dir, "runs")
  evaluations = []

  print(f"Starting batch {batch_id} with {args.num_runs} runs.")
  for index in range(1, args.num_runs + 1):
    run_id = f"{batch_id}_{condition}_{index:03d}"
    print(f"[{index}/{args.num_runs}] running {run_id}...")
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
    evaluations.append(evaluation)
    _save_json(log, os.path.join(run_dir, f"{run_id}.json"))

  summary = benchmark.aggregate_evaluations(evaluations)
  summary["batch_id"] = batch_id
  summary["condition"] = condition
  summary["model_name"] = args.model_name
  summary["api_type"] = args.api_type
  summary["use_dummy_embedder"] = args.use_dummy_embedder
  summary["num_runs"] = args.num_runs
  summary["include_relationship_memories"] = args.include_relationship_memories
  summary["scenario"] = args.scenario
  summary["scenario_id"] = scenario.SCENARIO_ID
  summary_path = os.path.join(batch_dir, "summary.json")
  csv_path = os.path.join(batch_dir, "observer_responses.csv")
  _save_json({"summary": summary, "evaluations": evaluations}, summary_path)
  benchmark.write_csv_rows(evaluations, csv_path)

  print("Batch finished.")
  print(f"Summary written to {summary_path}")
  print(f"Observer CSV written to {csv_path}")
  print(
      "Recognition success rate: "
      f"{summary['recognition_success_rate']:.2%} "
      f"({summary['recognition_success_count']}/"
      f"{summary['observer_decisions']})"
  )
  print(f"Category counts: {summary['category_counts']}")


if __name__ == "__main__":
  main()

