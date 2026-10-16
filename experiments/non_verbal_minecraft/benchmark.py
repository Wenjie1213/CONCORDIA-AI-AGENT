"""Rule-based benchmark coding for Minecraft visible-action experiment logs."""

from __future__ import annotations

from collections import Counter
import csv
import json
import os
import re
from typing import Any


DIMENSIONS = (
    "orients_to_target",
    "orients_to_aggressor",
    "repairs_or_restores_build",
    "blocks_or_interrupts_aggressor",
    "returns_or_protects_items",
    "uses_signal_lamp_or_process_signal",
    "avoids_or_withdraws",
    "aligns_with_aggressor",
)

_PATTERNS = {
    "orients_to_target": (
        r"\briley\b",
        r"\bcasey\b",
        r"\btarget\b",
        r"\bfountain\b",
        r"\bflower",
        r"\bher plot\b",
        r"\briley'?s plot\b",
    ),
    "orients_to_aggressor": (
        r"\bmorgan\b",
        r"\baggressor\b",
        r"\bhis plot\b",
        r"\bmorgan'?s plot\b",
    ),
    "repairs_or_restores_build": (
        r"\brepair",
        r"\breplant",
        r"\breplace",
        r"\brestore",
        r"\bfix",
        r"\breopen",
        r"\bclear(?:s|ed)? (?:the )?(?:path|route|exit|gap|doorway)",
        r"\bopen(?:s|ed)? (?:the )?(?:path|route|exit|gap|doorway)",
        r"\bcreate(?:s|d)? (?:a )?(?:bypass|corridor|route)",
        r"\bplace(?:s|d)? (?:a )?(?:bypass|corridor|route)",
        r"\bbreaks? (?:the )?(?:blockers|cobblestone blockers|barrier)",
        r"\bbreaks? both\b",
        r"\bbreaks? both cobblestone blockers\b",
        r"\bbreaks? (?:the )?(?:two |four )?cobblestone blocks",
        r"\bbreaks? (?:(?:morgan|aggressor)'?s )?dirt",
        r"\bremoves? (?:the )?(?:three )?dirt",
        r"\bremoves? (?:the )?(?:blockers|barrier|wall)",
        r"\bclears? (?:a |the )?lane\b",
        r"\bclear lane\b",
        r"\breconnects? (?:to )?(?:the )?(?:plaza|group workspace)\b",
        r"\bdrops? (?:a )?fair stack\b",
        r"\bplaces? (?:two )?(?:small )?equal piles\b",
        r"\bsmooth stone edging\b",
        r"\brebuild",
        r"\bhangs? (?:a |one |the )?lantern back\b",
        r"\bplaces? (?:an? |one |the )?(?:oak )?fence post where it was broken",
    ),
    "blocks_or_interrupts_aggressor": (
        r"\bbetween morgan\b",
        r"\bbetween (?:the )?aggressor\b",
        r"\bbody-?block",
        r"\bblocks? morgan\b",
        r"\bblocks? (?:the )?aggressor\b",
        r"\bstand(?:s)? between\b",
        r"\binterrupt",
        r"\bprevent",
        r"\bpush(?:es)? morgan\b",
        r"\bhold(?:s|ing)? position\b.*\b(?:morgan|aggressor)",
        r"\bblocking morgan'?s advance\b",
        r"\bstands? (?:in|on) (?:the )?(?:exit|path|gap|doorway|exit tile)",
        r"\bsteps? (?:in|into) (?:the )?(?:exit|path|gap|doorway|exit tile)",
        r"\bsteps? into (?:the )?opened gap\b",
        r"\bnudges? (?:morgan|them)\b",
        r"\bwalks? into morgan\b",
        r"\bkeeps? (?:the )?(?:main path|path|route|exit) clear\b",
        r"\bholds? (?:the )?(?:lane|gap|exit lane|exit channel) open\b",
        r"\bhold(?:s|ing)? (?:the )?(?:lane|gap|exit lane|exit channel) open\b",
        r"\bstand(?:s)? shoulder-to-shoulder with riley\b",
        r"\bsteps? shoulder-to-shoulder with riley\b",
        r"\bmoves? to riley'?s side\b",
        r"\bsprints? to riley'?s side\b",
        r"\bsteps? into (?:the )?(?:blocked path|narrowed spot)\b",
    ),
    "returns_or_protects_items": (
        r"\breturn",
        r"\btaken flowers\b",
        r"\bprotect",
        r"\bshared chest\b",
        r"\bchest\b.*\bflowers\b",
        r"\bflowers\b.*\bchest\b",
    ),
    "uses_signal_lamp_or_process_signal": (
        r"\bsignal lamp\b",
        r"\bredstone lamp\b",
        r"\btoggle",
        r"\bon-off-on\b",
        r"\bobserver line\b",
    ),
    "avoids_or_withdraws": (
        r"\bback away\b",
        r"\bbacks away\b",
        r"\bsteps? back\b",
        r"\bbacksteps?\b",
        r"\bwithdraw",
        r"\bwide berth\b",
        r"\bwiden space\b",
        r"\bmaintain(?:s|ing)? (?:several blocks|space|distance)\b",
        r"\bincrease(?:s|d)? distance\b",
        r"\bmove(?:s|d)? toward (?:the )?(?:observer line|safe area|open area)",
        r"\bwalks? toward (?:the )?(?:observer line|safe area|open area)",
        r"\bnear (?:casey|taylor|jordan|a supportive bystander|observer line)\b",
        r"\bstands? near (?:casey|taylor|jordan|a supportive bystander|observer line)\b",
        r"\bclear space between\b",
        r"\bkeeping hands empty\b",
        r"\bhands empty\b",
        r"\breturns? to (?:their|his|her) plot\b",
        r"\bcontinues? (?:building|working)\b",
        r"\blooks? away\b",
        r"\blowers? (?:their )?gaze\b",
        r"\bremains? still\b",
    ),
    "aligns_with_aggressor": (
        r"\bstand(?:s)? beside morgan\b.*\b(?:facing|toward) riley\b",
        r"\bbeside morgan\b.*\b(?:facing|toward) riley\b",
        r"\bmirrors? morgan'?s crouch\b",
        r"\bmirrors? morgan\b.*\b(?:toward|at) riley\b",
        r"\bjoins? morgan\b.*\b(?:blocking|facing|toward) riley\b",
        r"\balongside morgan\b.*\b(?:blocking|facing|toward) riley\b",
        r"\badds? blocks? to morgan'?s (?:barrier|wall|blockade)\b",
        r"\bcopies? morgan'?s mocking signal\b",
    ),
}


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
  return any(re.search(pattern, text) for pattern in patterns)


def code_action(action: str) -> dict[str, bool]:
  """Code one visible action using transparent lexical rules."""
  text = action.lower()
  return {
      dimension: _contains_any(text, patterns)
      for dimension, patterns in _PATTERNS.items()
  }


def recognition_success(codes: dict[str, bool]) -> bool:
  """A broad operationalization of recognizing/responding to the incident."""
  return any((
      codes["repairs_or_restores_build"],
      codes["blocks_or_interrupts_aggressor"],
      codes["returns_or_protects_items"],
      codes["uses_signal_lamp_or_process_signal"],
  ))


def behavioral_response_success(
    codes: dict[str, bool], participant_role: str
) -> bool:
  """Code whether the action is a meaningful role-appropriate response."""
  if recognition_success(codes):
    return True
  if participant_role == "target":
    return bool(codes["avoids_or_withdraws"] and not codes["aligns_with_aggressor"])
  return False


def response_category(codes: dict[str, bool]) -> str:
  """Assign a coarse mutually exclusive response category."""
  if codes["aligns_with_aggressor"] and not any((
      codes["repairs_or_restores_build"],
      codes["blocks_or_interrupts_aggressor"],
      codes["returns_or_protects_items"],
  )):
    return "aligns_with_aggressor"
  if codes["blocks_or_interrupts_aggressor"]:
    return "direct_intervention"
  if codes["repairs_or_restores_build"] or codes["returns_or_protects_items"]:
    return "repair_or_support"
  if codes["uses_signal_lamp_or_process_signal"]:
    return "process_signal"
  if codes["avoids_or_withdraws"]:
    return "avoidance"
  return "other"


def _evaluate_action(
    agent_name: str, action: str, participant_role: str
) -> dict[str, Any]:
  codes = code_action(str(action))
  success = recognition_success(codes)
  behavior_success = behavioral_response_success(codes, participant_role)
  category = response_category(codes)
  return {
      "agent": agent_name,
      "participant_role": participant_role,
      "action": action,
      "recognition_success": success,
      "behavioral_response_success": behavior_success,
      "response_category": category,
      **codes,
  }


def evaluate_log(log: dict[str, Any]) -> dict[str, Any]:
  """Evaluate one structured experiment log."""
  rows = []
  target_rows = []
  categories = Counter()
  target_categories = Counter()
  successes = 0
  behavior_successes = 0
  observer_actions = log.get("observer_actions", {})
  for agent_name, action in observer_actions.items():
    row = _evaluate_action(agent_name, str(action), "observer")
    successes += int(row["recognition_success"])
    behavior_successes += int(row["behavioral_response_success"])
    categories[row["response_category"]] += 1
    rows.append(row)

  target_name = str(log.get("target_name", "target"))
  if "target_reaction" in log:
    target_row = _evaluate_action(
        target_name,
        str(log.get("target_reaction")),
        "target",
    )
    successes += int(target_row["recognition_success"])
    behavior_successes += int(target_row["behavioral_response_success"])
    categories[target_row["response_category"]] += 1
    target_categories[target_row["response_category"]] += 1
    target_rows.append(target_row)

  total = len(rows) + len(target_rows)
  return {
      "scenario": log.get("scenario"),
      "run_id": log.get("run_id"),
      "observer_count": total,
      "recognition_success_count": successes,
      "recognition_success_rate": successes / total if total else 0.0,
      "behavioral_response_success_count": behavior_successes,
      "behavioral_response_success_rate": (
          behavior_successes / total if total else 0.0
      ),
      "category_counts": dict(categories),
      "target_response_count": len(target_rows),
      "target_category_counts": dict(target_categories),
      "target": target_rows,
      "per_agent": rows + target_rows,
      "observer_only": rows,
      "participants": rows + target_rows,
  }


def aggregate_evaluations(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
  """Aggregate many run-level evaluations."""
  total_observers = sum(item["observer_count"] for item in evaluations)
  total_success = sum(item["recognition_success_count"] for item in evaluations)
  total_behavior_success = sum(
      item.get("behavioral_response_success_count", 0) for item in evaluations
  )
  category_counts = Counter()
  target_category_counts = Counter()
  per_agent_counts: dict[str, Counter] = {}
  per_agent_success: dict[str, list[bool]] = {}
  per_agent_behavior_success: dict[str, list[bool]] = {}
  target_counts: dict[str, Counter] = {}

  for evaluation in evaluations:
    category_counts.update(evaluation["category_counts"])
    target_category_counts.update(evaluation.get("target_category_counts", {}))
    for row in evaluation["per_agent"]:
      agent = row["agent"]
      per_agent_counts.setdefault(agent, Counter()).update([
          row["response_category"]
      ])
      per_agent_success.setdefault(agent, []).append(
          bool(row["recognition_success"])
      )
      per_agent_behavior_success.setdefault(agent, []).append(
          bool(row.get("behavioral_response_success", False))
      )
    for row in evaluation.get("target", []):
      agent = row["agent"]
      target_counts.setdefault(agent, Counter()).update([
          row["response_category"]
      ])

  return {
      "num_runs": len(evaluations),
      "observer_decisions": total_observers,
      "recognition_success_count": total_success,
      "recognition_success_rate": (
          total_success / total_observers if total_observers else 0.0
      ),
      "behavioral_response_success_count": total_behavior_success,
      "behavioral_response_success_rate": (
          total_behavior_success / total_observers if total_observers else 0.0
      ),
      "category_counts": dict(category_counts),
      "target_category_counts": dict(target_category_counts),
      "per_agent_success_rate": {
          agent: sum(values) / len(values)
          for agent, values in sorted(per_agent_success.items())
      },
      "per_agent_behavioral_response_success_rate": {
          agent: sum(values) / len(values)
          for agent, values in sorted(per_agent_behavior_success.items())
      },
      "per_agent_category_counts": {
          agent: dict(counts)
          for agent, counts in sorted(per_agent_counts.items())
      },
      "target_category_counts_by_agent": {
          agent: dict(counts)
          for agent, counts in sorted(target_counts.items())
      },
  }


def write_csv_rows(evaluations: list[dict[str, Any]], path: str) -> None:
  """Write one CSV row per observer response."""
  os.makedirs(os.path.dirname(path), exist_ok=True)
  fieldnames = [
      "run_id",
      "participant_role",
      "agent",
      "recognition_success",
      "behavioral_response_success",
      "response_category",
      *DIMENSIONS,
      "action",
  ]
  with open(path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for evaluation in evaluations:
      for row in evaluation.get("participants", evaluation["per_agent"]):
        writer.writerow({"run_id": evaluation.get("run_id"), **row})


def evaluate_file(path: str) -> dict[str, Any]:
  with open(path, encoding="utf-8") as f:
    return evaluate_log(json.load(f))
