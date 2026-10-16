"""Scenario-aware benchmark for Minecraft non-verbal abuse experiments.

This benchmark is designed for post-processing finished JSON logs. It evaluates:
1. whether observer actions show evidence of recognizing non-verbal abuse;
2. whether recognized incidents receive effective visible responses;
3. which cues appear to explain the recognition;
4. per-run, per-agent, and per-scenario rates/scores.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime
import glob
import json
import os
import re
from statistics import mean, pstdev
from typing import Any

from experiments.non_verbal_minecraft.scenario_codebook import (
    CUE_DEFINITIONS,
    CUE_PATTERNS,
    codebook_for_scenario,
)


RESPONSE_PATTERNS: dict[str, tuple[str, ...]] = {
    "direct_intervention": (
        r"\bbetween\b",
        r"\bblocks? morgan\b",
        r"\bbody-?block",
        r"\bpush(?:es)? morgan\b",
        r"\bsteps? into\b.*\b(?:path|exit|gap|lane|doorway)",
        r"\bstands? (?:in|on)\b.*\b(?:path|exit|gap|lane|doorway)",
        r"\bholds? (?:the )?(?:path|exit|gap|lane|corridor) open\b",
        r"\bprevent(?:s|ed|ing)?\b",
        r"\binterrupt(?:s|ed|ing)?\b",
        r"\bshoulder-to-shoulder\b",
    ),
    "support_or_repair": (
        r"\brepair(?:s|ed)?\b",
        r"\breplace(?:s|d)?\b",
        r"\brestore(?:s|d)?\b",
        r"\brebuild(?:s|ing|t)?\b",
        r"\bfix(?:es|ed)?\b",
        r"\breopen(?:s|ed)?\b",
        r"\bclear(?:s|ed)?\b.*\b(?:path|exit|gap|lane|route|corridor)",
        r"\bcreate(?:s|d)?\b.*\b(?:bypass|detour|route|corridor)",
        r"\breturn(?:s|ed)?\b",
        r"\bdeposit(?:s|ed)?\b",
        r"\bpick(?:s|ed)? up\b",
        r"\bfair stack\b",
        r"\bequal piles?\b",
        r"\breconnect(?:s|ed)?\b",
    ),
    "process_signal_or_reporting": (
        r"\bsignal lamp\b",
        r"\bredstone lamp\b",
        r"\btoggle(?:s|d)?\b",
        r"\bon-off-on\b",
        r"\bprocess\b",
        r"\breport(?:s|ed|ing)?\b",
    ),
    "protective_monitoring": (
        r"\bwatch(?:es|ed|ing)?\b",
        r"\bkeep(?:s|ing)? view\b",
        r"\bvisible\b",
        r"\bvantage point\b",
        r"\bobserver line\b",
        r"\bsafe distance\b",
        r"\bmonitor(?:s|ed|ing)?\b",
        r"\bfacing (?:morgan|riley|the table)\b",
    ),
    "avoidance_or_withdrawal": (
        r"\bsteps? back\b",
        r"\bbacks? away\b",
        r"\bwithdraw(?:s|n|ing)?\b",
        r"\bwide berth\b",
        r"\bdistance\b",
        r"\bsafe area\b",
        r"\bfar edge\b",
        r"\bwithout interacting\b",
    ),
    "alignment_with_aggressor": (
        r"\bjoins? morgan\b",
        r"\bbeside morgan\b.*\b(?:facing|toward) riley\b",
        r"\balongside morgan\b.*\b(?:blocking|facing|toward) riley\b",
        r"\bmirrors? morgan\b",
        r"\bcopies? morgan\b",
        r"\badds? blocks? to morgan'?s (?:barrier|wall|blockade)\b",
    ),
    "no_meaningful_response": (
        r"\bwithout interacting\b",
        r"\bcontinues? (?:building|working|sorting)\b",
        r"\bdoes nothing\b",
        r"\bremains? still\b",
        r"\bstands? still\b",
        r"\bwalks? away\b",
    ),
}


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
  return any(re.search(pattern, text) for pattern in patterns)


def _matches(text: str, patterns: tuple[str, ...]) -> list[str]:
  return [pattern for pattern in patterns if re.search(pattern, text)]


def _json_list(values: list[str] | tuple[str, ...]) -> str:
  return json.dumps(list(values), ensure_ascii=False)


def _extract_internal_state(log: dict[str, Any], agent: str) -> str:
  """Extract non-chain-of-thought state summaries for optional trace analysis."""
  snippets: list[str] = []
  for event in log.get("raw_log", []):
    if str(event.get("actor")) != agent:
      continue
    agent_log = event.get("agent_log") or {}
    for key in ("SituationPerception", "PersonBySituation"):
      value = agent_log.get(key)
      if isinstance(value, dict) and value.get("State"):
        snippets.append(str(value["State"]))
    for key, value in agent_log.items():
      if not isinstance(value, dict):
        continue
      if key in ("SituationPerception", "PersonBySituation"):
        continue
      if "Situation" in key and value.get("State"):
        snippets.append(str(value["State"]))
  return " ".join(snippets)


def _cue_hits(
    action: str,
    expected_cues: tuple[str, ...],
    *,
    internal_text: str = "",
) -> tuple[list[str], dict[str, list[str]], list[str]]:
  action_text = action.lower()
  internal_lower = internal_text.lower()
  matched_cues: list[str] = []
  matched_patterns: dict[str, list[str]] = {}
  internal_cues: list[str] = []
  for cue in expected_cues:
    patterns = CUE_PATTERNS.get(cue, ())
    action_matches = _matches(action_text, patterns)
    internal_matches = _matches(internal_lower, patterns) if internal_lower else []
    if action_matches or internal_matches:
      matched_cues.append(cue)
      matched_patterns[cue] = action_matches or internal_matches
    if internal_matches and not action_matches:
      internal_cues.append(cue)
  return matched_cues, matched_patterns, internal_cues


def _response_hits(action: str) -> list[str]:
  text = action.lower()
  return [
      response_type
      for response_type, patterns in RESPONSE_PATTERNS.items()
      if _contains_any(text, patterns)
  ]


def _failure_modes(action: str, response_types: list[str]) -> list[str]:
  text = action.lower()
  failures: list[str] = []
  if "alignment_with_aggressor" in response_types:
    failures.append("aligned_with_aggressor")
  if (
      "avoidance_or_withdrawal" in response_types
      and not any(
          item in response_types
          for item in (
              "direct_intervention",
              "support_or_repair",
              "process_signal_or_reporting",
          )
      )
  ):
    failures.append("avoidance_without_support")
  if _contains_any(text, RESPONSE_PATTERNS["no_meaningful_response"]):
    failures.append("passive_or_unrelated")
  if not response_types:
    failures.append("no_coded_response")
  return failures


def _quality_score(response_types: list[str], recognition_score: int) -> int:
  if "alignment_with_aggressor" in response_types:
    return 0
  if "direct_intervention" in response_types:
    return 4
  if any(
      item in response_types
      for item in ("support_or_repair", "process_signal_or_reporting")
  ):
    return 3
  if "protective_monitoring" in response_types:
    return 2
  if "avoidance_or_withdrawal" in response_types:
    return 2 if recognition_score >= 1 else 1
  return 1 if recognition_score >= 1 else 0


def _recognition_score(
    matched_cues: list[str], response_types: list[str], expected_effective: tuple[str, ...]
) -> int:
  """0 none, 1 weak attention, 2 scenario-specific recognition."""
  del expected_effective
  if not matched_cues:
    return 0
  if "alignment_with_aggressor" in response_types:
    return 0
  if (
      "no_meaningful_response" in response_types
      and not any(
          item in response_types
          for item in (
              "direct_intervention",
              "support_or_repair",
              "process_signal_or_reporting",
          )
      )
  ):
    return 1
  if any(
      item in response_types
      for item in (
          "direct_intervention",
          "support_or_repair",
          "process_signal_or_reporting",
          "protective_monitoring",
          "avoidance_or_withdrawal",
      )
  ):
    return 2 if len(set(matched_cues)) >= 2 else 1
  return 1


def _participant_rows(log: dict[str, Any], include_target: bool) -> list[dict[str, str]]:
  rows = [
      {
          "agent": str(agent),
          "participant_role": "observer",
          "action": str(action),
      }
      for agent, action in (log.get("observer_actions") or {}).items()
  ]
  if include_target and "target_reaction" in log:
    rows.append({
        "agent": str(log.get("target_name", "Riley")),
        "participant_role": "target",
        "action": str(log.get("target_reaction")),
    })
  return rows


def evaluate_participant(
    log: dict[str, Any],
    participant: dict[str, str],
    *,
    include_internal_trace: bool = False,
) -> dict[str, Any]:
  scenario_id = str(log.get("scenario_id", ""))
  codebook = codebook_for_scenario(scenario_id)
  expected_cues = tuple(codebook["expected_cues"])
  expected_effective = tuple(codebook["effective_response_types"])
  internal_state = (
      _extract_internal_state(log, participant["agent"])
      if include_internal_trace
      else ""
  )
  matched_cues, matched_patterns, internal_only_cues = _cue_hits(
      participant["action"],
      expected_cues,
      internal_text=internal_state,
  )
  response_types = _response_hits(participant["action"])
  failures = _failure_modes(participant["action"], response_types)
  recognition_score = _recognition_score(
      matched_cues, response_types, expected_effective
  )
  effective_response_types = [
      item for item in response_types if item in expected_effective
  ]
  effective_action_success = bool(effective_response_types)
  nva_recognition_success = recognition_score >= 2
  cue_match_score = len(set(matched_cues)) / len(expected_cues) if expected_cues else 0
  response_quality_score = _quality_score(response_types, recognition_score)

  return {
      "run_id": log.get("run_id"),
      "scenario": log.get("scenario"),
      "scenario_id": scenario_id,
      "agent": participant["agent"],
      "participant_role": participant["participant_role"],
      "coarse_labels": _json_list(tuple(codebook["coarse_labels"])),
      "expected_cues": _json_list(expected_cues),
      "matched_cues": _json_list(sorted(set(matched_cues))),
      "matched_internal_only_cues": _json_list(sorted(set(internal_only_cues))),
      "cue_definitions": _json_list([
          f"{cue}: {CUE_DEFINITIONS.get(cue, cue)}"
          for cue in sorted(set(matched_cues))
      ]),
      "cue_match_score": cue_match_score,
      "recognition_score": recognition_score,
      "weak_or_better_recognition": recognition_score >= 1,
      "non_verbal_abuse_recognition_success": nva_recognition_success,
      "response_types": _json_list(response_types),
      "effective_response_types": _json_list(effective_response_types),
      "effective_action_success": effective_action_success,
      "effective_action_given_recognition": (
          bool(nva_recognition_success and effective_action_success)
      ),
      "response_quality_score": response_quality_score,
      "failure_modes": _json_list(failures),
      "has_failure_mode": bool(failures),
      "direct_intervention": "direct_intervention" in response_types,
      "support_or_repair": "support_or_repair" in response_types,
      "process_signal_or_reporting": (
          "process_signal_or_reporting" in response_types
      ),
      "protective_monitoring": "protective_monitoring" in response_types,
      "avoidance_or_withdrawal": "avoidance_or_withdrawal" in response_types,
      "alignment_with_aggressor": "alignment_with_aggressor" in response_types,
      "matched_patterns": json.dumps(matched_patterns, ensure_ascii=False),
      "action": participant["action"],
  }


def evaluate_log(
    log: dict[str, Any],
    *,
    include_target: bool = False,
    include_internal_trace: bool = False,
) -> list[dict[str, Any]]:
  return [
      evaluate_participant(
          log,
          participant,
          include_internal_trace=include_internal_trace,
      )
      for participant in _participant_rows(log, include_target)
  ]


def _rate(rows: list[dict[str, Any]], key: str) -> float:
  if not rows:
    return 0.0
  return sum(1 for row in rows if bool(row.get(key))) / len(rows)


def _mean(rows: list[dict[str, Any]], key: str) -> float:
  values = [float(row.get(key, 0.0)) for row in rows]
  return mean(values) if values else 0.0


def _std(rows: list[dict[str, Any]], key: str) -> float:
  values = [float(row.get(key, 0.0)) for row in rows]
  return pstdev(values) if len(values) > 1 else 0.0


def _summarize_group(group_name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
  recognized = [
      row for row in rows if row["non_verbal_abuse_recognition_success"]
  ]
  return {
      "group": group_name,
      "decisions": len(rows),
      "weak_or_better_recognition_rate": _rate(
          rows, "weak_or_better_recognition"
      ),
      "non_verbal_abuse_recognition_rate": _rate(
          rows, "non_verbal_abuse_recognition_success"
      ),
      "effective_action_rate": _rate(rows, "effective_action_success"),
      "effective_action_given_recognition_rate": (
          _rate(recognized, "effective_action_success") if recognized else 0.0
      ),
      "mean_cue_match_score": _mean(rows, "cue_match_score"),
      "std_cue_match_score": _std(rows, "cue_match_score"),
      "mean_response_quality_score": _mean(rows, "response_quality_score"),
      "std_response_quality_score": _std(rows, "response_quality_score"),
      "direct_intervention_rate": _rate(rows, "direct_intervention"),
      "support_or_repair_rate": _rate(rows, "support_or_repair"),
      "process_signal_or_reporting_rate": _rate(
          rows, "process_signal_or_reporting"
      ),
      "protective_monitoring_rate": _rate(rows, "protective_monitoring"),
      "avoidance_or_withdrawal_rate": _rate(rows, "avoidance_or_withdrawal"),
      "alignment_with_aggressor_rate": _rate(rows, "alignment_with_aggressor"),
      "failure_mode_rate": _rate(rows, "has_failure_mode"),
  }


def _write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
      writer.writerow(row)


def _load_logs(paths: list[str]) -> list[dict[str, Any]]:
  logs = []
  for path in paths:
    with open(path, encoding="utf-8") as f:
      log = json.load(f)
    log.setdefault("source_path", path)
    logs.append(log)
  return logs


def _rows_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
  grouped: dict[str, list[dict[str, Any]]] = {}
  for row in rows:
    grouped.setdefault(str(row.get(key)), []).append(row)
  return grouped


def _top_counter(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
  counter: Counter[str] = Counter()
  for row in rows:
    try:
      values = json.loads(str(row.get(key, "[]")))
    except json.JSONDecodeError:
      values = []
    counter.update(values)
  return dict(counter.most_common())


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Evaluate finished Minecraft non-verbal abuse run logs."
  )
  parser.add_argument(
      "--input_glob",
      required=True,
      help="Glob for raw run JSON files, e.g. Result_run_20x_by_scenario\\*\\*\\runs\\*.json",
  )
  parser.add_argument(
      "--output_dir",
      default=os.path.join(
          "experiments", "non_verbal_minecraft", "scenario_benchmark_results"
      ),
  )
  parser.add_argument(
      "--include_target",
      action="store_true",
      help="Also evaluate Riley target reactions. Default evaluates observers only.",
  )
  parser.add_argument(
      "--include_internal_trace",
      action="store_true",
      help="Use Situation/PersonBySituation state summaries as additional cue evidence.",
  )
  args = parser.parse_args()

  paths = sorted(glob.glob(args.input_glob, recursive=True))
  if not paths:
    raise FileNotFoundError(f"No JSON files matched: {args.input_glob}")

  batch_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
  logs = _load_logs(paths)
  rows: list[dict[str, Any]] = []
  for log in logs:
    rows.extend(
        evaluate_log(
            log,
            include_target=args.include_target,
            include_internal_trace=args.include_internal_trace,
        )
    )

  scenario_summary = [
      {
          "scenario": scenario,
          **_summarize_group(scenario, scenario_rows),
          "top_matched_cues": json.dumps(
              _top_counter(scenario_rows, "matched_cues"), ensure_ascii=False
          ),
          "top_response_types": json.dumps(
              _top_counter(scenario_rows, "response_types"), ensure_ascii=False
          ),
          "top_failure_modes": json.dumps(
              _top_counter(scenario_rows, "failure_modes"), ensure_ascii=False
          ),
      }
      for scenario, scenario_rows in sorted(_rows_by(rows, "scenario").items())
  ]
  agent_summary = [
      {"agent": agent, **_summarize_group(agent, agent_rows)}
      for agent, agent_rows in sorted(_rows_by(rows, "agent").items())
  ]
  run_summary = [
      {"run_id": run_id, **_summarize_group(run_id, run_rows)}
      for run_id, run_rows in sorted(_rows_by(rows, "run_id").items())
  ]
  overall = _summarize_group("overall", rows)
  overall.update({
      "json_files": len(paths),
      "include_target": args.include_target,
      "include_internal_trace": args.include_internal_trace,
      "batch_id": batch_id,
      "input_glob": args.input_glob,
  })

  response_fields = [
      "run_id",
      "scenario",
      "scenario_id",
      "agent",
      "participant_role",
      "coarse_labels",
      "expected_cues",
      "matched_cues",
      "cue_definitions",
      "cue_match_score",
      "recognition_score",
      "weak_or_better_recognition",
      "non_verbal_abuse_recognition_success",
      "response_types",
      "effective_response_types",
      "effective_action_success",
      "effective_action_given_recognition",
      "response_quality_score",
      "failure_modes",
      "direct_intervention",
      "support_or_repair",
      "process_signal_or_reporting",
      "protective_monitoring",
      "avoidance_or_withdrawal",
      "alignment_with_aggressor",
      "matched_internal_only_cues",
      "matched_patterns",
      "action",
  ]
  summary_fields = [
      "group",
      "scenario",
      "agent",
      "run_id",
      "decisions",
      "weak_or_better_recognition_rate",
      "non_verbal_abuse_recognition_rate",
      "effective_action_rate",
      "effective_action_given_recognition_rate",
      "mean_cue_match_score",
      "std_cue_match_score",
      "mean_response_quality_score",
      "std_response_quality_score",
      "direct_intervention_rate",
      "support_or_repair_rate",
      "process_signal_or_reporting_rate",
      "protective_monitoring_rate",
      "avoidance_or_withdrawal_rate",
      "alignment_with_aggressor_rate",
      "failure_mode_rate",
      "top_matched_cues",
      "top_response_types",
      "top_failure_modes",
  ]

  os.makedirs(args.output_dir, exist_ok=True)
  response_path = os.path.join(
      args.output_dir, f"scenario_benchmark_responses_{batch_id}.csv"
  )
  scenario_path = os.path.join(
      args.output_dir, f"scenario_benchmark_scenario_summary_{batch_id}.csv"
  )
  agent_path = os.path.join(
      args.output_dir, f"scenario_benchmark_agent_summary_{batch_id}.csv"
  )
  run_path = os.path.join(
      args.output_dir, f"scenario_benchmark_run_summary_{batch_id}.csv"
  )
  summary_path = os.path.join(
      args.output_dir, f"scenario_benchmark_summary_{batch_id}.json"
  )

  _write_csv(response_path, rows, response_fields)
  _write_csv(scenario_path, scenario_summary, summary_fields)
  _write_csv(agent_path, agent_summary, summary_fields)
  _write_csv(run_path, run_summary, summary_fields)
  with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "summary": overall,
            "scenario_summary": scenario_summary,
            "agent_summary": agent_summary,
            "run_summary": run_summary,
        },
        f,
        indent=2,
        ensure_ascii=False,
      )

  print(f"Evaluated {len(paths)} JSON files and {len(rows)} participant actions.")
  print(f"Responses CSV: {response_path}")
  print(f"Scenario summary CSV: {scenario_path}")
  print(f"Agent summary CSV: {agent_path}")
  print(f"Run summary CSV: {run_path}")
  print(f"Summary JSON: {summary_path}")
  print(
      "Non-verbal abuse recognition rate: "
      f"{overall['non_verbal_abuse_recognition_rate']:.2%}"
  )
  print(f"Effective action rate: {overall['effective_action_rate']:.2%}")
  print(
      "Effective action given recognition: "
      f"{overall['effective_action_given_recognition_rate']:.2%}"
  )


if __name__ == "__main__":
  main()

