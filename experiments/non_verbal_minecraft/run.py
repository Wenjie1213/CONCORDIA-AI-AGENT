"""Run the Minecraft non-verbal action response experiment.

Usage:
  python -m experiments.non_verbal_minecraft.run --disable_language_model

  python -m experiments.non_verbal_minecraft.run \
    --api_type=openai \
    --model_name=gpt-4o \
    --api_key YOUR_KEY
"""

import argparse
import datetime
import json
import os
from typing import Any

from concordia.contrib.language_models import language_model_setup
from concordia.language_model import no_language_model
import numpy as np

from experiments.non_verbal_minecraft import benchmark
from experiments.non_verbal_minecraft.configs import scenario_registry
from experiments.non_verbal_minecraft import simulation

def _condition_label(args) -> str:
  model = str(args.model_name).replace("/", "-").replace("\\", "-")
  embedder = "dummyembed" if args.use_dummy_embedder else "realembed"
  relmem = "relmem" if args.include_relationship_memories else "no-relmem"
  return f"{model}_{embedder}_{relmem}"

def setup_model(args):
  if args.disable_language_model:
    print("Language model disabled; using NoLanguageModel for smoke testing.")
    return no_language_model.NoLanguageModel(), lambda _: np.ones(3)

  if not args.api_key:
    raise ValueError("--api_key is required unless --disable_language_model is set.")

  model = language_model_setup(
      api_type=args.api_type,
      model_name=args.model_name,
      api_key=args.api_key,
      disable_language_model=False,
  )

  if args.use_dummy_embedder:
    embedder = lambda _: np.ones(384)
  else:
    import sentence_transformers

    st_model = sentence_transformers.SentenceTransformer(
        "sentence-transformers/all-mpnet-base-v2"
    )
    embedder = lambda x: st_model.encode(x, show_progress_bar=False)

  return model, embedder


def _save_json(data: dict[str, Any], output_dir: str, condition: str) -> str:
  timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  scenario_id = data.get("scenario_id", "scenario")
  scenario_dir = os.path.join(output_dir, scenario_id)
  os.makedirs(scenario_dir, exist_ok=True)
  path = os.path.join(
      scenario_dir,
      f"minecraft_non_verbal_{scenario_id}_{condition}_{timestamp}.json",
  )
  with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
  return path


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Run a controlled Minecraft non-verbal action experiment."
  )
  parser.add_argument("--api_type", default="openai")
  parser.add_argument("--model_name", default="gpt-4o")
  parser.add_argument("--api_key", default=None)
  parser.add_argument(
      "--disable_language_model",
      action="store_true",
      help="Use a mock model for smoke testing.",
  )
  parser.add_argument(
      "--use_dummy_embedder",
      action="store_true",
      help="Avoid downloading sentence-transformers by using a dummy embedder.",
  )
  parser.add_argument(
      "--include_relationship_memories",
      action="store_true",
      help="Include fixed prior relationship memories as an experimental condition.",
  )
  parser.add_argument(
      "--scenario",
      default=scenario_registry.DEFAULT_SCENARIO,
      choices=sorted(scenario_registry.SCENARIOS.keys()),
      help="Scenario to run.",
  )
  parser.add_argument(
      "--output_dir",
      default=os.path.join("experiments", "non_verbal_minecraft", "results"),
  )
  args = parser.parse_args()

  model, embedder = setup_model(args)
  scenario = scenario_registry.SCENARIOS[args.scenario]
  result = simulation.run_simulation(
      model=model,
      embedder=embedder,
      include_relationship_memories=args.include_relationship_memories,
      scenario=scenario,
  )
  condition = _condition_label(args)
  result.structured_log["condition"] = condition
  result.structured_log["use_dummy_embedder"] = args.use_dummy_embedder
  result.structured_log["benchmark"] = benchmark.evaluate_log(
      result.structured_log
  )
  output_path = _save_json(result.structured_log, args.output_dir, condition)

  print("Experiment finished.")
  print(f"JSON structured log written to {output_path}")
  print("\nObserver visible actions:")
  for name, action in result.structured_log["observer_actions"].items():
    print(f"  {name}: {action}")
  run_benchmark = result.structured_log["benchmark"]
  print(
      "\nRecognition success rate: "
      f"{run_benchmark['recognition_success_rate']:.2%} "
      f"({run_benchmark['recognition_success_count']}/"
      f"{run_benchmark['observer_count']})"
  )
  print(f"Category counts: {run_benchmark['category_counts']}")


if __name__ == "__main__":
  main()

