from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal

Audience = Literal["Couple", "Vendor", "Wedding Party", "Internal"]

@dataclass(frozen=True)
class FamilyDynamics:
    divorced_parents: bool = False
    remarried_parents: bool = False
    strained_relationships: bool = False
    finicky_family_members: bool = False
    notes: str = ""  # e.g. “Don’t pair X with Y. Do bride’s side first.”

@dataclass(frozen=True)
class ReceptionEvents:
    # toggles
    grand_entrance: bool = True
    first_dance: bool = True
    father_daughter_dance: bool = False
    mother_son_dance: bool = False
    toasts: bool = True
    dinner: bool = True
    cake_cutting: bool = True
    bouquet_toss: bool = False
    garter_toss: bool = False

    # optional hard times (if planner provides them)
    grand_entrance_time: Optional[datetime] = None
    first_dance_time: Optional[datetime] = None
    parent_dances_time: Optional[datetime] = None
    toasts_time: Optional[datetime] = None
    dinner_start_time: Optional[datetime] = None
    cake_cutting_time: Optional[datetime] = None
    bouquet_toss_time: Optional[datetime] = None
    garter_toss_time: Optional[datetime] = None

    # default durations (minutes)
    grand_entrance_minutes: int = 10
    first_dance_minutes: int = 8
    parent_dances_minutes: int = 10
    toasts_minutes: int = 20
    dinner_minutes: int = 60
    cake_cutting_minutes: int = 10
    bouquet_toss_minutes: int = 8
    garter_toss_minutes: int = 5

@dataclass(frozen=True)
class EventInputs:
    wedding_date: Optional[str]  # "YYYY-MM-DD"

    # Coverage constraint
    coverage_start: datetime
    coverage_hours: float  # e.g. 6, 8, 10, 12
    coverage_end: datetime  # computed in app.py

    # Ceremony anchors
    ceremony_start: datetime
    ceremony_minutes: int  # 30–90+

    # Locations
    getting_ready_location: str
    ceremony_location: str
    reception_location: str

    # Travel
    travel_gr_to_ceremony_minutes: int
    travel_ceremony_to_reception_minutes: int

    # Big decisions
    first_look: bool
    receiving_line: bool
    receiving_line_minutes: int

    # Cocktail hour context
    cocktail_hour_minutes: int
    protect_cocktail_hour: bool

    # Family dynamics
    family_dynamics: FamilyDynamics

    # Photo blocks
    buffer_minutes: int
    flatlay_details_minutes: int
    getting_dressed_minutes: int
    individual_portraits_minutes: int
    first_look_minutes: int
    couple_portraits_minutes: int
    wedding_party_portraits_minutes: int
    family_portraits_minutes: int
    tuckaway_minutes: int

    # Optional family sizing
    family_groupings: Optional[int]
    minutes_per_family_grouping: int

    # Optional light anchor
    sunset_time: Optional[datetime]
    golden_hour_window_minutes: int

    # Reception anchors & coverage
    reception_start: Optional[datetime]
    reception_events: ReceptionEvents

@dataclass
class TimelineBlock:
    name: str
    start: datetime
    end: datetime
    location: str
    notes: str = ""
    audience: Audience = "Vendor"
    kind: str = "photo"  # "travel", "buffer", "event", "photo", "coverage"

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)