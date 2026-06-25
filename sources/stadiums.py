"""Approximate stadium coordinates for matching fixtures to weather.

Keyed by The Odds API team name. Extend for more leagues. National teams are intentionally
absent — World Cup venues vary by fixture, so we don't attach a fixed-stadium weather to them.
"""
from __future__ import annotations

STADIUMS: dict[str, tuple[float, float]] = {
    "Arsenal": (51.5549, -0.1084),
    "Chelsea": (51.4817, -0.1910),
    "Liverpool": (53.4308, -2.9608),
    "Man City": (53.4831, -2.2004),
    "Man United": (53.4631, -2.2913),
    "Tottenham": (51.6043, -0.0664),
    "Newcastle": (54.9756, -1.6217),
    "Aston Villa": (52.5092, -1.8847),
    "West Ham": (51.5386, -0.0166),
    "Everton": (53.4388, -2.9663),
    "Brighton": (50.8616, -0.0837),
    "Wolves": (52.5902, -2.1303),
}


def coords_for(team: str) -> tuple[float, float] | None:
    return STADIUMS.get(team)
