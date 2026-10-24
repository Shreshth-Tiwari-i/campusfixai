"""Deterministic rule-based triage system for CampusFix AI.

Evaluates complaint title and description against documented keyword rules
to suggest Category and Priority with transparent explanations.
No AI or cloud models are used.
"""

import re
from typing import NamedTuple, Optional

RULE_BASED_SOURCE = "Rule-based suggestion"
DEFAULT_STATUS = "Reported"
DEFAULT_TRIAGE_SOURCE = "Not triaged"

ALLOWED_CATEGORIES = [
    "Electrical",
    "Plumbing",
    "Network",
    "AV/Equipment",
    "Other",
]

ALLOWED_PRIORITIES = [
    "High",
    "Medium",
    "Low",
]


class TriageResult(NamedTuple):
    """Result of rule-based complaint triage."""

    category: str
    priority: str
    reason: str
    source: str


class _TriageRule:
    """Internal rule structure mapping keyword patterns to triage suggestions."""

    def __init__(
        self,
        category: str,
        priority: str,
        patterns: list[str],
        rule_name: str,
    ):
        self.category = category
        self.priority = priority
        self.patterns = patterns
        self.rule_name = rule_name
        # Compile case-insensitive word-boundary regex
        combined_pattern = r"\b(" + "|".join(patterns) + r")\b"
        self.regex = re.compile(combined_pattern, re.IGNORECASE)

    def match(self, text: str) -> Optional[str]:
        match = self.regex.search(text)
        return match.group(0) if match else None


# ==============================================================================
# Documented Rule Evaluation Order
#
# Hierarchy:
# 1. Tier 1 - High Priority Safety & Severe Hazards (sparks, exposed wires,
#    burning smell, severe flooding).
# 2. Tier 2 - Specific Infrastructure & Utilities (Plumbing, Network,
#    AV/Equipment, standard Electrical issues) -> Medium Priority.
# 3. Tier 3 - Minor Cosmetic Damage -> Low Priority.
# 4. Tier 4 - Fallback -> Other / Medium / "Manual review needed".
# ==============================================================================
TRIAGE_RULES: list[_TriageRule] = [
    # 1. High Priority - Electrical Hazards
    _TriageRule(
        category="Electrical",
        priority="High",
        patterns=[
            r"spark(?:s|ing|ed)?",
            r"exposed wires?",
            r"burn(?:ing|t)? smell",
            r"short circuits?",
            r"electric shocks?",
            r"wire jal(?:a| gaya)?",
            r"spark ho raha",
            r"bijli shock",
        ],
        rule_name="Electrical hazard (sparks, exposed wires, burning smell)",
    ),
    # 2. High Priority - Severe Flooding Hazards
    _TriageRule(
        category="Plumbing",
        priority="High",
        patterns=[
            r"severe flood(?:ing|ed|s)?",
            r"flood(?:ing|ed|s)?",
            r"water overflow(?:ing)?",
            r"submerged",
            r"pipe burst(?:ed)?",
            r"pa+ni bhar(?: gaya)?",
            r"flood ho gaya",
        ],
        rule_name="Severe flooding hazard",
    ),
    # 3. Medium Priority - Plumbing / Water Issues
    _TriageRule(
        category="Plumbing",
        priority="Medium",
        patterns=[
            r"water leak(?:age|ing|s)?",
            r"leak(?:age|ing|s|y)?",
            r"taps?",
            r"faucets?",
            r"flush",
            r"drains?",
            r"clog(?:ged|ging|s)?",
            r"toilets?",
            r"sinks?",
            r"pipes?",
            r"sewers?",
            r"nals?",
            r"pa+ni tapak(?: raha)?",
            r"pa+ni leak",
        ],
        rule_name="Plumbing / water leakage",
    ),
    # 4. Medium Priority - Network / Connectivity
    _TriageRule(
        category="Network",
        priority="Medium",
        patterns=[
            r"wi-?fi",
            r"internets?",
            r"ethernets?",
            r"lan",
            r"routers?",
            r"network down",
            r"connect nahi ho raha",
            r"internet band",
        ],
        rule_name="Network / connectivity issue",
    ),
    # 5. Medium Priority - AV / Equipment
    _TriageRule(
        category="AV/Equipment",
        priority="Medium",
        patterns=[
            r"projectors?",
            r"microphones?",
            r"mics?",
            r"speakers?",
            r"hdmi",
            r"podiums?",
            r"smart boards?",
            r"display screens?",
            r"projector kharab",
            r"screen nahi chal raha",
        ],
        rule_name="AV / equipment issue",
    ),
    # 6. Medium Priority - Standard Electrical (Non-hazard)
    _TriageRule(
        category="Electrical",
        priority="Medium",
        patterns=[
            r"fans?",
            r"lights?",
            r"tube lights?",
            r"bulbs?",
            r"switch(?:es)?",
            r"switchboards?",
            r"sockets?",
            r"power cuts?",
            r"air conditioners?",
            r"ac",
            r"pankh[ae]",
            r"bijli",
            r"tube light band",
        ],
        rule_name="Electrical appliance / lighting issue",
    ),
    # 7. Low Priority - Minor Cosmetic Damage
    _TriageRule(
        category="Other",
        priority="Low",
        patterns=[
            r"minor cosmetic(?: damage)?",
            r"paints?",
            r"peel(?:ing)?",
            r"scratch(?:es)?",
            r"stains?",
            r"cosmetic",
            r"dents?",
            r"chipped",
            r"cracked tiles?",
            r"rust(?:y)?",
            r"plaster ukhad(?: gaya)?",
            r"rang chhoot(?: gaya)?",
        ],
        rule_name="Minor cosmetic damage",
    ),
]


def triage_complaint(title: str, description: str) -> TriageResult:
    """Evaluate complaint text deterministically using keyword rules.

    Args:
        title: Complaint headline.
        description: Detailed explanation of the issue.

    Returns:
        TriageResult containing suggested category, priority, reason, and source.
    """
    combined_text = f"{title or ''} {description or ''}".strip()

    if not combined_text:
        return TriageResult(
            category="Other",
            priority="Medium",
            reason="Manual review needed",
            source=RULE_BASED_SOURCE,
        )

    for rule in TRIAGE_RULES:
        matched_keyword = rule.match(combined_text)
        if matched_keyword:
            explanation = (
                f"Rule matched '{rule.rule_name}' on keyword '{matched_keyword}'"
            )
            return TriageResult(
                category=rule.category,
                priority=rule.priority,
                reason=explanation,
                source=RULE_BASED_SOURCE,
            )

    # Fallback for unmatched text
    return TriageResult(
        category="Other",
        priority="Medium",
        reason="Manual review needed",
        source=RULE_BASED_SOURCE,
    )
