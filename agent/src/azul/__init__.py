"""Azul — autonomous deep-research SDR agent.

Jalon 0: a thin slice that takes ~25 prospects through
source -> research -> write -> human approval -> send -> outcome -> report,
and emits a real reply rate. Built on clean module boundaries and a
flywheel-ready, multi-tenant schema so later milestones slot in without a
rewrite. External engines (research, writer, channel) sit behind interfaces
and are swappable.
"""

__version__ = "0.0.1"
