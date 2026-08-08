"""Mechanical writing-standards detectors (see standards/writing-standards.md)."""

from __future__ import annotations

from .registry import run_checks
from .types import RuleViolation, SkippedRule, StandardsCheckResult

__all__ = ["RuleViolation", "SkippedRule", "StandardsCheckResult", "run_checks"]
