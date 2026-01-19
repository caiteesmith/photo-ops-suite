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
    notes: str = ""

@dataclass(frozen=True)
class ReceptionEvents:
    # toggles
    grand_entrance: bool = True
    first_dance: bool = True
    father_daughter_dance: bool = False
    mother_son_dance: bool = False
    toasts: bool = True
    dinner: bool = True

    dancefloor_coverage: bool = True

    cake_cutting: bool = True
    bouquet_toss: bool = False
    garter_toss: bool = False

    # optional hard times
    grand_entrance_time: Optional[datetime] = None
    first_dance_time: Optional[datetime] = None
    parent_dances_time: Optional[datetime] = None
    toasts_time: Optional[datetime] = None
    dinner_start_time: Optional[datetime] = None

    # events that typically happen during dancing
    cake_cutting_time: Optional[datetime] = None
    bouquet_toss_time: Optional[datetime] = None
    garter_toss_time: Optional[datetime] = None

    # durations
    grand_entrance_minutes: int = 10
    first_dance_minutes: int = 8
    parent_dances_minutes: int = 10
    toasts_minutes: int = 20
    dinner_minutes: int = 60

    dancefloor_minutes: int = 90

    cake_cutting_minutes: int = 10
    bouquet_toss_minutes: int = 0
    garter_toss_minutes: int = 0

@dataclass(frozen=True)
class EventInputs:
    wedding_date: Optional[str]

    coverage_start: datetime
    coverage_hours: float
    coverage_end: datetime

    photographer_arrival_time: Optional[datetime]
    arrival_setup_minutes: int

    ceremony_start: datetime
    ceremony_minutes: int

    getting_ready_location: str
    ceremony_location: str
    portraits_location: str
    reception_location: str

    travel_gr_to_ceremony_minutes: int
    travel_ceremony_to_reception_minutes: int

    first_look: bool
    receiving_line: bool
    receiving_line_minutes: int

    cocktail_hour_minutes: int
    protect_cocktail_hour: bool

    family_dynamics: FamilyDynamics

    buffer_minutes: int
    flatlay_details_minutes: int
    getting_dressed_minutes: int
    individual_portraits_minutes: int
    first_look_minutes: int
    couple_portraits_minutes: int
    wedding_party_portraits_minutes: int
    family_portraits_minutes: int
    tuckaway_minutes: int

    family_groupings: Optional[int]
    minutes_per_family_grouping: int

    sunset_time: Optional[datetime]
    golden_hour_window_minutes: int

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
    kind: str = "Photo"  # "Travel", "Buffer", "Event", "Photo", "Coverage"

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)