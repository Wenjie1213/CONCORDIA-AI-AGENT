"""Print observer interpretive traces from one experiment JSON log."""

import argparse
import json
import os
from typing import Any

from experiments.non_verbal_minecraft import benchmark


def _resolve_path(path: str) -> str:
  if os.path.exists(path):
    return path
  results_path = os.path.join(
      "experiments",
      "non_verbal_minecraft",
      "results",
      path,
  )
  if os.path.exists(results_path):
    return results_path
  raise FileNotFoundError(path)


def _component_state(agent_log: dict[str, Any], component_name: str) -> str:
  component = agent_log.get(component_name, {})
  return str(component.get("State") or component.get("Value") or "")


def _component_summary(agent_log: dict[str, Any], component_name: str) -> str:
  component = agent_log.get(component_name, {})
  return str(component.get("Summary") or "")


def _print_block(title: str, value: str) -> None:
  print(f"\n{title}:")
  if value.strip():
    print(value.strip())
  else:
    print("(empty)")


def explain(log: dict[str, Any]) -> None:
  evaluation = benchmark.evaluate_log(log)
  evaluation_by_agent = {
      row["agent"]: row for row in evaluation["per_agent"]
  }

  print(f"Scenario: {log.get('scenario')}")
  print(f"Scenario ID: {log.get('scenario_id')}")
  print(f"Label disclosed to agents: {log.get('label_disclosed_to_agents')}")
  print(
      "Relationship memories included: "
      f"{log.get('include_relationship_memories')}"
  )
  print("\nVisible incident:")
  print(log.get("stimulus", {}).get("scripted_visible_incident", ""))

  for entry in log.get("raw_log", []):
    if entry.get("phase") != "observer_visible_response":
      continue
    actor = entry.get("actor", "(unknown)")
    agent_log = entry.get("agent_log", {})
    row = evaluation_by_agent.get(actor, {})

    print("\n" + "=" * 72)
    print(f"Observer: {actor}")
    print(f"Benchmark category: {row.get('response_category')}")
    print(f"Recognition success: {row.get('recognition_success')}")
    active_dimensions = [
        dimension
        for dimension in benchmark.DIMENSIONS
        if row.get(dimension)
    ]
    print(f"Active benchmark dimensions: {active_dimensions}")

    _print_block(
        "SituationPerception.State",
        _component_state(agent_log, "SituationPerception"),
    )
    _print_block(
        "SelfPerception.State",
        _component_state(agent_log, "SelfPerception"),
    )
    _print_block(
        "PersonBySituation.State",
        _component_state(agent_log, "PersonBySituation"),
    )
    _print_block(
        "PersonBySituation.Summary",
        _component_summary(agent_log, "PersonBySituation"),
    )
    _print_block("Final visible action", str(entry.get("visible_action", "")))

  target_name = log.get("target_name")
  if target_name:
    for entry in log.get("raw_log", []):
      if entry.get("phase") == "target_visible_response":
        print("\n" + "=" * 72)
        print(f"Target response: {target_name}")
        _print_block("Final visible action", str(entry.get("visible_action", "")))
        break


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Explain observer interpretive traces from one JSON log."
  )
  parser.add_argument(
      "file",
      help=(
          "Path to a JSON log, or a filename inside "
          "experiments/non_verbal_minecraft/results."
      ),
  )
  args = parser.parse_args()

  path = _resolve_path(args.file)
  with open(path, encoding="utf-8") as f:
    explain(json.load(f))


if __name__ == "__main__":
  main()
