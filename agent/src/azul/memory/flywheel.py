"""Flywheel stubs: curator + eval harness. Deliberately not implemented in Jalon 0.

These come online only after we have real outcomes to learn from, graded by the
real reply rate (anti-drift-to-slop). Kept here so the module boundary exists.
"""

from __future__ import annotations

from azul.errors import AzulError


def run_curator(*_args: object, **_kwargs: object) -> None:
    """Promote recurring winning touches into procedural `skills`. (Later.)"""
    raise AzulError("Curator is a later milestone — needs real outcome data first")


def evaluate_skill(*_args: object, **_kwargs: object) -> float:
    """Score a candidate skill against held-out outcomes. (Later.)"""
    raise AzulError("Eval harness is a later milestone — needs real outcome data first")
