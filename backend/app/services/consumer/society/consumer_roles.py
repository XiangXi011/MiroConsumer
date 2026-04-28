"""Unified consumer role enum for Phase 6G+."""

from enum import Enum


class ConsumerRole(str, Enum):
    Advocate = "advocate"
    Skeptic = "skeptic"
    Misreader = "misreader"
    Amplifier = "amplifier"
    Lurker = "lurker"
    PriceSensitive = "price_sensitive"
    TrustRepairable = "trust_repairable"
    Blocker = "blocker"


__all__ = ["ConsumerRole"]
