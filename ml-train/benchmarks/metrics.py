"""
Benchmark metrics for the agentic-bot evaluation (spec Step 8.3).

The one metric that matters here is **recall at a fixed human false-positive
rate**, NOT F1 — because blocking real humans is the expensive error and a
threshold-free F1 hides it (strategy doc §B.6). Everything in this module is
built around: "pick the risk threshold that yields the target human FPR on the
human set, then report what fraction of each bot persona is blocked at exactly
that threshold."

All functions are pure (no DB, no network) so they're unit-testable and can't
race the data-generation batches.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion.

    Used on the human FPR because with ~41 humans a naive p ± 1.96·sqrt(p(1-p)/n)
    is badly wrong near 0 (it can go negative and understates uncertainty). The
    spec (§8.3) explicitly requires reporting this so the small-N caveat is
    quantified rather than hand-waved.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def threshold_at_human_fpr(human_scores: list[float], target_fpr: float) -> float:
    """Risk threshold (block if score >= threshold) that yields at most
    `target_fpr` false positives on the human set.

    Returns the LOWEST threshold whose human FPR is <= target — i.e. the most
    sensitive operating point that still respects the FPR budget, so bot recall
    is maximised subject to the human constraint. With few humans the achievable
    FPRs are quantised (steps of 1/n), so the realised FPR is also returned by
    evaluate_persona for honesty.
    """
    if not human_scores:
        return 50.0  # no humans to calibrate against; fall back to the product default
    n = len(human_scores)
    ordered = sorted(set(human_scores)) + [max(human_scores) + 1e-6]
    best = ordered[-1]
    for thr in ordered:
        fp = sum(1 for s in human_scores if s >= thr)
        if fp / n <= target_fpr:
            best = thr
            break
    return float(best)


def realised_human_fpr(human_scores: list[float], threshold: float) -> float:
    if not human_scores:
        return 0.0
    fp = sum(1 for s in human_scores if s >= threshold)
    return fp / len(human_scores)


@dataclass
class PersonaResult:
    persona: str
    n: int
    blocked: int
    recall: float
    median_risk: float
    recall_ci: tuple[float, float] = (0.0, 1.0)


@dataclass
class BenchmarkRow:
    detector: str
    threshold: float
    target_fpr: float
    realised_fpr: float
    realised_fpr_ci: tuple[float, float]
    n_humans: int
    personas: list[PersonaResult] = field(default_factory=list)


def evaluate_persona(persona: str, bot_scores: list[float], threshold: float) -> PersonaResult:
    n = len(bot_scores)
    blocked = sum(1 for s in bot_scores if s >= threshold)
    recall = blocked / n if n else 0.0
    lo, hi = wilson_interval(blocked, n)
    median = sorted(bot_scores)[n // 2] if n else 0.0
    return PersonaResult(persona, n, blocked, recall, float(median), (lo, hi))


def build_row(detector: str, human_scores: list[float],
              persona_scores: dict[str, list[float]], target_fpr: float) -> BenchmarkRow:
    """Score one detector: calibrate its threshold to the human FPR, then
    evaluate every bot persona at that single threshold."""
    threshold = threshold_at_human_fpr(human_scores, target_fpr)
    realised = realised_human_fpr(human_scores, threshold)
    n_h = len(human_scores)
    fp = round(realised * n_h)
    row = BenchmarkRow(
        detector=detector,
        threshold=threshold,
        target_fpr=target_fpr,
        realised_fpr=realised,
        realised_fpr_ci=wilson_interval(fp, n_h),
        n_humans=n_h,
    )
    for persona, scores in persona_scores.items():
        row.personas.append(evaluate_persona(persona, scores, threshold))
    return row


def rows_to_markdown(rows: list[BenchmarkRow], persona_order: Optional[list[str]] = None) -> str:
    """Render the spec §8.5 comparison table. One row per detector, one column
    per persona (recall %), plus the realised human FPR with its Wilson CI."""
    if not rows:
        return "_No benchmark rows._\n"
    if persona_order is None:
        persona_order = [p.persona for p in rows[0].personas]

    header = "| Detector | " + " | ".join(persona_order) + " | Human FPR (95% CI) |"
    sep = "|" + "---|" * (len(persona_order) + 2)
    lines = [header, sep]
    for row in rows:
        by_name = {p.persona: p for p in row.personas}
        cells = []
        for name in persona_order:
            p = by_name.get(name)
            if p is None:
                cells.append("—")
            else:
                cells.append(f"{p.recall * 100:.0f}% ({p.n})")
        lo, hi = row.realised_fpr_ci
        fpr_cell = f"{row.realised_fpr * 100:.1f}% [{lo * 100:.1f}–{hi * 100:.1f}], n={row.n_humans}"
        lines.append(f"| **{row.detector}** | " + " | ".join(cells) + f" | {fpr_cell} |")
    lines.append("")
    lines.append(f"_Recall = % of persona blocked at the risk threshold giving "
                 f"≤{rows[0].target_fpr * 100:.1f}% human FPR. Parenthetical = persona sample size. "
                 f"Human-FPR CI is Wilson 95%; small n means wide intervals — see caveats._")
    return "\n".join(lines)
