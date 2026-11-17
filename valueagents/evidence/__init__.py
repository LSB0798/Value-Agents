# ./valueagents/evidence/__init__.py
"""Evidence Infrastructure — Phase 1 + Phase 3 W1 / W3a"""

from .schema import Claim, EvidenceBundle, EvidenceItem, Signal
from .graph import EvidenceGraph
from .frameworks import (
    MASTER_GROUPS,
    ALL_19_MASTERS,
    FRAMEWORK_QUESTIONS,
    FRAMEWORK_APPLICABLE_WHEN,
    FrameworkView,
    build_framework_views,
    summarize_framework_views,
)
from .risk_profile import (
    DimensionSignal,
    RiskProfile,
    build_risk_profile,
    summarize_risk_profile,
)

__all__ = [
    # Phase 1: schema
    "EvidenceItem",
    "Claim",
    "Signal",
    "EvidenceBundle",
    # Phase 1: graph
    "EvidenceGraph",
    # Phase 3 W1: frameworks
    "MASTER_GROUPS",
    "ALL_19_MASTERS",
    "FRAMEWORK_QUESTIONS",
    "FRAMEWORK_APPLICABLE_WHEN",
    "FrameworkView",
    "build_framework_views",
    "summarize_framework_views",
    # Phase 3 W3a: risk profile
    "DimensionSignal",
    "RiskProfile",
    "build_risk_profile",
    "summarize_risk_profile",
]