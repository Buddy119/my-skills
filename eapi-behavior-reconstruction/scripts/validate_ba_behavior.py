#!/usr/bin/env python3
"""Reject the retired one-to-one BA Behavior document model."""

from __future__ import annotations

import sys


def main() -> int:
    print(
        "ERROR: BA Behavior documents are retired; use validate_ba_journey.py and "
        "validate_ba_scenario.py"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
