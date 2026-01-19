# =========================
# file: tools/timeline_builder.py
# =========================
from __future__ import annotations
from datetime import datetime
from typing import List, Tuple, Optional, Dict

import pandas as pd

from core.models import EventInputs, TimelineBlock
from core.timeutils import add_minutes, safe_fmt_time, minutes_between


def _add_block(
    blocks: List[TimelineBlock],
    name: str,
    start: datetime,
    minutes: int,
    location: str,
    notes: str = "",
    audience: str = "Vendor",
    kind: str = "photo",
) -> datetime:
    end = add_minutes(start, minutes)
    blocks.append(
        TimelineBlock(
            name=name,
            start=start,
            end=end,
            location=location,
            notes=notes,
            audience=audience,  # type: ignore
            kind=kind,
        )
    )
    return end


def _add_buffer(
    blocks: List[TimelineBlock],
    t: datetime,
    buffer_minutes: int,
    location: str,
    notes: str = "",
) -> datetime:
    if buffer_minutes <= 0:
        return t
    return _add_block(
        blocks,
        name="Buffer/transition",
        start=t,
        minutes=buffer_minutes,
        location=location,
        notes=notes or "Built-in breathing room (bathroom, moving people, touch-ups, etc.)",
        audience="Vendor",
        kind="buffer",
    )


def _add_travel(blocks: List[TimelineBlock], t: datetime, travel_minutes: int, from_to: str) -> datetime:
    if travel_minutes <= 0:
        return t
    return _add_block(
        blocks,
        name=f"Travel: {from_to}",
        start=t,
        minutes=travel_minutes,
        location="In transit",
        notes="Includes loading up, parking, & walking time as needed.",
        audience="Vendor",
        kind="travel",
    )


def _add_gap_to_cocktail_hour(
    blocks: List[TimelineBlock],
    t: datetime,
    gap_minutes: int,
    location: str,
) -> datetime:
    """
    Optional long gap between ceremony flow and cocktail hour start.
    Useful for church ceremonies + travel/logistics before cocktail hour begins.
    """
    if gap_minutes <= 0:
        return t
    return _add_block(
        blocks,
        name="Gap before cocktail hour",
        start=t,
        minutes=int(gap_minutes),
        location=location,
        notes="Buffer for travel/logistics between ceremony and cocktail hour.",
        audience="Vendor",
        kind="buffer",
    )


def _family_minutes(inputs: EventInputs) -> int:
    if inputs.family_groupings and inputs.family_groupings > 0:
        return int(inputs.family_groupings) * int(inputs.minutes_per_family_grouping)
    return int(inputs.family_portraits_minutes)


def _family_dynamics_notes(inputs: EventInputs) -> str:
    fd = inputs.family_dynamics
    flags = []
    if fd.divorced_parents:
        flags.append("divorced parents")
    if fd.remarried_parents:
        flags.append("remarried parents")
    if fd.strained_relationships:
        flags.append("strained relationships")
    if fd.finicky_family_members:
        flags.append("finicky family members")

    parts = []
    if flags:
        parts.append("Family dynamics: " + ", ".join(flags) + ".")
    if fd.notes.strip():
        parts.append(fd.notes.strip())
    return " ".join(parts).strip()


def _add_coverage_end_marker(blocks: List[TimelineBlock], inputs: EventInputs) -> None:
    blocks.append(
        TimelineBlock(
            name="Coverage ends",
            start=inputs.coverage_end,
            end=inputs.coverage_end,
            location="—",
            notes=f"Coverage: {inputs.coverage_hours:g} hrs starting {safe_fmt_time(inputs.coverage_start)}",
            audience="Internal",
            kind="coverage",
        )
    )


# ---------- Coverage allocation helpers ----------
def _overlap_minutes(a_start: datetime, a_end: datetime, w_start: datetime, w_end: datetime) -> int:
    """
    Minutes of overlap between [a_start, a_end] and [w_start, w_end].
    """
    start = max(a_start, w_start)
    end = min(a_end, w_end)
    if end <= start:
        return 0
    return int((end - start).total_seconds() // 60)


def coverage_allocation_by_kind(blocks: List[TimelineBlock], coverage_start: datetime, coverage_end: datetime) -> pd.DataFrame:
    """
    Minutes IN coverage window by Kind.
    Displays: '90 min (1.5 hr)'.
    """
    dancefloor = _dancefloor_intervals(blocks)

    rows = []
    for b in blocks:
        if b.kind in {"coverage", "window"}:
            continue

        mins = _overlap_minutes(b.start, b.end, coverage_start, coverage_end)
        if mins <= 0:
            continue

        if b.kind == "event" and b.name in {"Cake cutting", "Bouquet toss", "Garter toss"} and dancefloor:
            embedded = _embedded_in_dancefloor_minutes(b, dancefloor, coverage_start, coverage_end)
            mins = max(0, mins - embedded)

        if mins <= 0:
            continue

        rows.append({"Kind": b.kind, "Minutes": mins})

    if not rows:
        return pd.DataFrame(columns=["Kind", "Time Used"])

    df = pd.DataFrame(rows)
    grouped = (
        df.groupby("Kind", as_index=False)["Minutes"]
        .sum()
        .sort_values("Minutes", ascending=False)
    )
    grouped["Time Used"] = grouped["Minutes"].apply(lambda m: f"{m} min ({round(m / 60, 2)} hr)")
    return grouped[["Kind", "Time Used"]]


def coverage_allocation_top_blocks(blocks: List[TimelineBlock], coverage_start: datetime, coverage_end: datetime, top_n: int = 8) -> pd.DataFrame:
    """
    Picks top_n blocks by minutes-in-coverage, then displays chronologically.
    """
    dancefloor = _dancefloor_intervals(blocks)

    rows = []
    for b in blocks:
        if b.kind in {"coverage", "window"}:
            continue

        mins = _overlap_minutes(b.start, b.end, coverage_start, coverage_end)
        if mins <= 0:
            continue

        if b.kind == "event" and b.name in {"Cake cutting", "Bouquet toss", "Garter toss"} and dancefloor:
            embedded = _embedded_in_dancefloor_minutes(b, dancefloor, coverage_start, coverage_end)
            mins = max(0, mins - embedded)

        if mins <= 0:
            continue

        rows.append(
            {
                "StartDT": b.start,
                "Start": safe_fmt_time(b.start),
                "End": safe_fmt_time(b.end),
                "Block": b.name,
                "Kind": b.kind,
                "Time Used": f"{mins} min ({round(mins / 60, 2)} hr)",
                "Location": b.location,
                "MinutesSort": mins,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["Start", "End", "Block", "Kind", "Time Used", "Location"])

    df = pd.DataFrame(rows)

    df = df.sort_values("MinutesSort", ascending=False).head(top_n)
    df = df.sort_values("StartDT").drop(columns=["StartDT", "MinutesSort"]).reset_index(drop=True)
    return df


def coverage_totals(blocks: List[TimelineBlock], coverage_start: datetime, coverage_end: datetime) -> Dict[str, int]:
    """
    Returns:
      - in_coverage_minutes: sum overlap of all blocks with coverage window
      - scheduled_minutes_total: sum of all block durations (excluding coverage marker)
      - overage_minutes: (latest_end - coverage_end) if latest_end > coverage_end else 0
    """
    in_cov = 0
    scheduled_total = 0
    latest_end = coverage_start

    for b in blocks:
        if b.kind in {"coverage", "window"}:
            continue
        scheduled_total += max(0, b.duration_minutes)
        latest_end = max(latest_end, b.end)
        in_cov += _overlap_minutes(b.start, b.end, coverage_start, coverage_end)

    overage = max(0, minutes_between(coverage_end, latest_end)) if latest_end > coverage_end else 0
    return {
        "in_coverage_minutes": int(in_cov),
        "scheduled_minutes_total": int(scheduled_total),
        "overage_minutes": int(overage),
    }


def _dancefloor_intervals(blocks: List[TimelineBlock]) -> List[tuple[datetime, datetime]]:
    intervals = []
    for b in blocks:
        if b.name.startswith("Dancefloor coverage"):
            intervals.append((b.start, b.end))
    return intervals


def _embedded_in_dancefloor_minutes(
    b: TimelineBlock,
    dancefloor_intervals: List[tuple[datetime, datetime]],
    coverage_start: datetime,
    coverage_end: datetime,
) -> int:
    total = 0
    for ds, de in dancefloor_intervals:
        total += _overlap_minutes(b.start, b.end, max(ds, coverage_start), min(de, coverage_end))
    return total


# ---------- Main timeline builder ----------
def build_timeline(inputs: EventInputs) -> Tuple[List[TimelineBlock], List[str]]:
    """
    Notes:
    - Cocktail hour is ALWAYS included exactly once.
    - If inputs.reception_start is provided, cocktail hour is anchored to it (starts reception_start - cocktail_minutes).
    - If reception_start is not provided:
        - If inputs.cocktail_hour_follows_ceremony is True (default), cocktail starts immediately after ceremony/reset.
        - Else, a long gap block is inserted before cocktail (inputs.ceremony_to_cocktail_gap_minutes).
    - When no first look, portraits are scheduled post-ceremony and may overlap what guests experience as "cocktail hour".
      In that case, we mark cocktail hour as kind="window" so it doesn't double-count coverage minutes.
    """
    blocks: List[TimelineBlock] = []
    warnings: List[str] = []

    # Centralized portrait location (fallbacks)
    portrait_location = (
        getattr(inputs, "portraits_location", None)
        or inputs.ceremony_location
        or inputs.getting_ready_location
    )

    # ------------------------
    # PRE-CEREMONY
    # ------------------------
    t = inputs.coverage_start

    # ------------------------
    # PHOTOGRAPHER ARRIVAL
    # ------------------------
    if inputs.photographer_arrival_time is not None:
        _add_block(
            blocks,
            "Photographer arrival",
            inputs.photographer_arrival_time,
            0,
            inputs.getting_ready_location,
            notes="Arrival on-site (Park, unload, setup gear).",
            audience="Vendor",
            kind="event",
        )

        arrival_end = inputs.photographer_arrival_time

        if inputs.arrival_setup_minutes and inputs.arrival_setup_minutes > 0:
            arrival_end = _add_block(
                blocks,
                "Arrival/Gear setup",
                inputs.photographer_arrival_time,
                int(inputs.arrival_setup_minutes),
                inputs.getting_ready_location,
                notes="Unload, prep gear, scout light, confirm timeline, detail staging.",
                audience="Vendor",
                kind="photo",
            )

        if arrival_end > t:
            t = arrival_end

    t = _add_block(
        blocks,
        "Flat lay & details",
        t,
        inputs.flatlay_details_minutes,
        inputs.getting_ready_location,
        notes="Invitation suite, rings, vow books, perfume, jewelry, etc.",
        audience="Vendor",
        kind="photo",
    )
    t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.getting_ready_location)

    t = _add_block(
        blocks,
        "Getting dressed",
        t,
        inputs.getting_dressed_minutes,
        inputs.getting_ready_location,
        notes="Dress/veil, boutonniere, letter reading, parent reveals.",
        audience="Vendor",
        kind="photo",
    )
    t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.getting_ready_location)

    t = _add_block(
        blocks,
        "Individual portraits",
        t,
        inputs.individual_portraits_minutes,
        inputs.getting_ready_location,
        notes="Each partner individually (or solo portraits) while everyone's fresh.",
        audience="Vendor",
        kind="photo",
    )
    t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.getting_ready_location)

    t = _add_travel(blocks, t, inputs.travel_gr_to_ceremony_minutes, "Getting ready → Ceremony")
    t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

    # First look flow
    if inputs.first_look:
        t = _add_block(
            blocks,
            "First look",
            t,
            inputs.first_look_minutes,
            portrait_location,
            notes="Private moment & first reactions.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, portrait_location)

        # If there IS a first look, do ALL portraits pre-ceremony
        dyn_note = _family_dynamics_notes(inputs)
        fam_minutes = _family_minutes(inputs)

        # Couple portraits
        t = _add_block(
            blocks,
            "Couple portraits",
            t,
            inputs.couple_portraits_minutes,
            portrait_location,
            notes="All couple portraits completed pre-ceremony when first look is scheduled.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, portrait_location)

        # Wedding party portraits
        t = _add_block(
            blocks,
            "Wedding party portraits",
            t,
            inputs.wedding_party_portraits_minutes,
            portrait_location,
            notes="All wedding party portraits completed pre-ceremony when first look is scheduled.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, portrait_location)

        # Family portraits
        extra_family_buffer = 0
        if (
            inputs.family_dynamics.divorced_parents
            or inputs.family_dynamics.strained_relationships
            or inputs.family_dynamics.finicky_family_members
        ):
            extra_family_buffer = max(5, inputs.buffer_minutes // 2)

        t = _add_block(
            blocks,
            "Family portraits",
            t,
            fam_minutes,
            portrait_location,
            notes=("All family formals completed pre-ceremony when first look is scheduled. " + dyn_note).strip(),
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes + extra_family_buffer, portrait_location)

    # Pre-ceremony tuckaway
    if t < inputs.ceremony_start:
        slack = minutes_between(t, inputs.ceremony_start)

        tuck_mins = min(int(inputs.tuckaway_minutes), int(slack))
        if tuck_mins > 0:
            t = _add_block(
                blocks,
                "Tuckaway before ceremony",
                t,
                tuck_mins,
                inputs.ceremony_location,
                notes="Guest arrivals candids & ceremony space details (programs, florals, wide shots, signage).",
                audience="Vendor",
                kind="photo",
            )
            slack = minutes_between(t, inputs.ceremony_start)

        if slack >= 8:
            t = _add_block(
                blocks,
                "Flexible pre-ceremony coverage",
                t,
                slack,
                inputs.ceremony_location,
                notes="Extra cushion for delays or additional venue/guest coverage.",
                audience="Vendor",
                kind="buffer",
            )
    else:
        if inputs.tuckaway_minutes > 0:
            warnings.append(
                "No time available before the ceremony for tuckaway "
                "Start coverage earlier or reduce pre-ceremony blocks."
            )

    if t > inputs.ceremony_start:
        over = minutes_between(inputs.ceremony_start, t)
        warnings.append(
            f"Pre-ceremony schedule runs {over} min past ceremony start. Reduce blocks or start coverage earlier."
        )

    # ------------------------
    # CEREMONY
    # ------------------------
    t = inputs.ceremony_start
    t = _add_block(
        blocks,
        "Ceremony",
        t,
        inputs.ceremony_minutes,
        inputs.ceremony_location,
        notes="",
        audience="Vendor",
        kind="event",
    )

    # Receiving line
    if inputs.receiving_line:
        t = _add_block(
            blocks,
            "Receiving line",
            t,
            inputs.receiving_line_minutes,
            inputs.ceremony_location,
            notes="If the couple greets guests immediately after the ceremony.",
            audience="Vendor",
            kind="event",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

    # Reset time
    t = _add_buffer(
        blocks,
        t,
        inputs.buffer_minutes,
        inputs.ceremony_location,
        notes="Quick reset (water, touch-ups, bustle, regroup).",
    )

    fam_minutes = _family_minutes(inputs)
    dyn_note = _family_dynamics_notes(inputs)

    extra_family_buffer = 0
    if (
        inputs.family_dynamics.divorced_parents
        or inputs.family_dynamics.strained_relationships
        or inputs.family_dynamics.finicky_family_members
    ):
        extra_family_buffer = max(5, inputs.buffer_minutes // 2)

    # ------------------------
    # POST-CEREMONY (portraits if no first look)
    # ------------------------
    if not inputs.first_look:
        t = _add_block(
            blocks,
            "Family portraits",
            t,
            fam_minutes,
            portrait_location,
            notes=("Keep list tight & assign a wrangler. " + dyn_note).strip(),
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes + extra_family_buffer, portrait_location)

        t = _add_block(
            blocks,
            "Wedding party portraits",
            t,
            inputs.wedding_party_portraits_minutes,
            portrait_location,
            notes="Full group + smaller combos.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, portrait_location)

        t = _add_block(
            blocks,
            "Couple portraits",
            t,
            inputs.couple_portraits_minutes,
            portrait_location,
            notes="Aim for flattering light + a little breathing room.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, portrait_location)

        # feasibility warning
        est_post = fam_minutes + inputs.wedding_party_portraits_minutes + inputs.couple_portraits_minutes
        if inputs.receiving_line:
            est_post += inputs.receiving_line_minutes

        if est_post > inputs.cocktail_hour_minutes:
            warnings.append(
                f"No first look: estimated post-ceremony portraits ~{est_post} min vs cocktail hour "
                f"{inputs.cocktail_hour_minutes} min. Expect tight timing unless portrait time is reduced or cocktail hour extended."
            )
        if inputs.protect_cocktail_hour:
            warnings.append(
                "Protect cocktail hour is enabled but there is no first look. This usually conflicts unless portrait time is reduced or cocktail hour is extended."
            )

    # ------------------------
    # TRAVEL TO RECEPTION (if any)
    # ------------------------
    t = _add_travel(blocks, t, inputs.travel_ceremony_to_reception_minutes, "Ceremony → Reception")

    # ------------------------
    # COCKTAIL HOUR (always included exactly once)
    # ------------------------
    cocktail_kind = "photo" if inputs.first_look else "window"
    cocktail_notes = (
        "Candids & reception details."
        if inputs.first_look
        else "Cocktail hour window. If there is no first look, portraits/travel may overlap this time."
    )

    cocktail_location = inputs.reception_location or inputs.ceremony_location

    # Preferred: anchor cocktail hour off reception_start if provided
    if inputs.reception_start is not None:
        cocktail_start = add_minutes(inputs.reception_start, -int(inputs.cocktail_hour_minutes))
        if cocktail_start < t:
            warnings.append(
                f"Cocktail hour start ({safe_fmt_time(cocktail_start)}) is earlier than the current timeline position "
                f"({safe_fmt_time(t)}). Portraits/travel may be too long."
            )
    else:
        # Otherwise: either starts immediately after ceremony flow, or after a user-defined gap
        cocktail_start = t
        follows = getattr(inputs, "cocktail_hour_follows_ceremony", True)
        gap_mins = int(getattr(inputs, "ceremony_to_cocktail_gap_minutes", 0) or 0)

        if not follows:
            cocktail_start = _add_gap_to_cocktail_hour(blocks, cocktail_start, gap_mins, cocktail_location)

    # Add the one cocktail hour block
    t = _add_block(
        blocks,
        "Cocktail hour",
        cocktail_start,
        int(inputs.cocktail_hour_minutes),
        cocktail_location,
        notes=cocktail_notes,
        audience="Vendor",
        kind=cocktail_kind,
    )

    # Ensure the main cursor advances to the end of cocktail hour
    t = add_minutes(cocktail_start, int(inputs.cocktail_hour_minutes))
    t = _add_buffer(blocks, t, inputs.buffer_minutes, cocktail_location)

    # ------------------------
    # Reception start anchor (optional)
    # ------------------------
    if inputs.reception_start is not None:
        _add_block(
            blocks,
            "Reception start",
            inputs.reception_start,
            0,
            inputs.reception_location,
            notes="Planned reception start time.",
            audience="Vendor",
            kind="event",
        )

    if inputs.reception_start and t > inputs.reception_start:
        late = minutes_between(inputs.reception_start, t)
        warnings.append(f"Arrives {late} min after reception start time you entered (timeline may be too tight).")

    if inputs.reception_start and t < inputs.reception_start:
        slack = minutes_between(t, inputs.reception_start)
        if slack >= 10:
            t = _add_block(
                blocks,
                "Reception details (before guests enter)",
                t,
                slack,
                inputs.reception_location,
                notes="Tablescape, florals, signage, wide shots.",
                audience="Vendor",
                kind="photo",
            )
            t = inputs.reception_start

    # ------------------------
    # RECEPTION EVENTS
    # ------------------------
    re = inputs.reception_events

    def schedule_event_if_toggle(name: str, enabled: bool, when: Optional[datetime], minutes: int, notes: str):
        nonlocal t
        if not enabled:
            return
        if when is not None:
            if when < t:
                warnings.append(
                    f"{name} time ({safe_fmt_time(when)}) is earlier than current timeline position ({safe_fmt_time(t)}). Check planner times."
                )
            t = when
        t = _add_block(blocks, name, t, minutes, inputs.reception_location, notes=notes, audience="Vendor", kind="event")
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.reception_location)

    dancefloor_start: Optional[datetime] = None
    dancefloor_end: Optional[datetime] = None

    def place_embedded_event(name: str, enabled: bool, when: Optional[datetime], minutes: int, default_offset_min: int):
        if not enabled:
            return
        if not dancefloor_start or not dancefloor_end:
            return  # no dancefloor window to embed into

        start_time = when if when is not None else add_minutes(dancefloor_start, default_offset_min)

        # clamp into dancefloor window
        if start_time < dancefloor_start:
            start_time = dancefloor_start
        if start_time > add_minutes(dancefloor_end, -minutes):
            start_time = add_minutes(dancefloor_end, -minutes)

        _add_block(
            blocks,
            name,
            start_time,
            minutes,
            inputs.reception_location,
            notes="Happens during dancefloor coverage.",
            audience="Vendor",
            kind="event",
        )

    # Hard-time events
    schedule_event_if_toggle("Grand entrance", re.grand_entrance, re.grand_entrance_time, re.grand_entrance_minutes, "If couple is announced into reception.")
    schedule_event_if_toggle("First dance", re.first_dance, re.first_dance_time, re.first_dance_minutes, "If scheduled at reception.")
    schedule_event_if_toggle(
        "Parent dances",
        (re.father_daughter_dance or re.mother_son_dance),
        re.parent_dances_time,
        re.parent_dances_minutes,
        "Father/daughter and/or mother/son dances.",
    )
    schedule_event_if_toggle("Toasts", re.toasts, re.toasts_time, re.toasts_minutes, "Speeches/toasts block.")

    # Dinner
    if re.dinner and re.dinner_start_time is not None:
        if re.dinner_start_time < t:
            warnings.append(f"Dinner start ({safe_fmt_time(re.dinner_start_time)}) is earlier than current timeline position ({safe_fmt_time(t)}).")
        t = re.dinner_start_time
        t = _add_block(blocks, "Dinner", t, re.dinner_minutes, inputs.reception_location, notes="Dinner service", audience="Vendor", kind="event")
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.reception_location)
    elif re.dinner:
        t = _add_block(
            blocks,
            "Dinner",
            t,
            re.dinner_minutes,
            inputs.reception_location,
            notes="Replace with planner-provided dinner time when available.",
            audience="Vendor",
            kind="event",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.reception_location)

    if re.dancefloor_coverage:
        dancefloor_start = t
        dancefloor_end = add_minutes(dancefloor_start, re.dancefloor_minutes)

        # main dancing block (continuous)
        _ = _add_block(
            blocks,
            "Dancefloor coverage",
            dancefloor_start,
            re.dancefloor_minutes,
            inputs.reception_location,
            notes="General dancing coverage. Cake + bouquet/garter usually happen during this window.",
            audience="Vendor",
            kind="photo",
        )

    if re.dancefloor_coverage:
        place_embedded_event("Cake cutting", re.cake_cutting, re.cake_cutting_time, re.cake_cutting_minutes, default_offset_min=15)
        place_embedded_event("Bouquet toss", re.bouquet_toss, re.bouquet_toss_time, re.bouquet_toss_minutes, default_offset_min=45)
        place_embedded_event("Garter toss", re.garter_toss, re.garter_toss_time, re.garter_toss_minutes, default_offset_min=55)

        # After dancefloor, advance t to the end of dancefloor for anything that follows
        t = dancefloor_end
    else:
        schedule_event_if_toggle("Cake cutting", re.cake_cutting, re.cake_cutting_time, re.cake_cutting_minutes, "Cake cutting.")
        schedule_event_if_toggle("Bouquet toss", re.bouquet_toss, re.bouquet_toss_time, re.bouquet_toss_minutes, "Bouquet toss.")
        schedule_event_if_toggle("Garter toss", re.garter_toss, re.garter_toss_time, re.garter_toss_minutes, "Garter toss.")

    # Sunset marker (shows in timeline)
    if inputs.sunset_time is not None:
        golden_start = add_minutes(inputs.sunset_time, -30)
        _add_block(
            blocks,
            "Golden hour portraits",
            golden_start,
            int(inputs.golden_hour_window_minutes),
            portrait_location or inputs.reception_location or inputs.ceremony_location,
            notes=f"Sunset ~ {safe_fmt_time(inputs.sunset_time)}.",
            audience="Vendor",
            kind="photo",
        )

    # Coverage constraint check
    latest_end = max((b.end for b in blocks), default=inputs.coverage_start)
    if latest_end > inputs.coverage_end:
        over = minutes_between(inputs.coverage_end, latest_end)
        warnings.append(
            f"Timeline runs {over} min past coverage end ({safe_fmt_time(inputs.coverage_end)}). "
            f"Reduce portrait/event coverage, shorten blocks, or increase coverage hours."
        )

    _add_coverage_end_marker(blocks, inputs)
    return blocks, warnings


def blocks_to_dataframe(blocks: List[TimelineBlock]) -> pd.DataFrame:
    rows = []
    for b in blocks:
        rows.append(
            {
                "StartDT": b.start,
                "EndDT": b.end,
                "Start": safe_fmt_time(b.start),
                "End": safe_fmt_time(b.end),
                "Block": b.name,
                "Minutes": b.duration_minutes,
                "Location": b.location,
                "Audience": b.audience,
                "Notes": b.notes,
                "Kind": b.kind,
            }
        )
    df = pd.DataFrame(rows)
    df = df.sort_values(["StartDT", "EndDT", "Block"]).drop(columns=["StartDT", "EndDT"]).reset_index(drop=True)
    return df


def blocks_to_text(blocks: List[TimelineBlock], audience_filter: str | None = None) -> str:
    sorted_blocks = sorted(blocks, key=lambda b: (b.start, b.end, b.name))

    lines: List[str] = []
    for b in sorted_blocks:
        if audience_filter and b.audience != audience_filter:
            continue

        if b.duration_minutes == 0:
            lines.append(f"{safe_fmt_time(b.start)} • {b.name}")
            if b.notes:
                lines.append(f"  - {b.notes}")
            continue

        lines.append(f"{safe_fmt_time(b.start)}-{safe_fmt_time(b.end)} | {b.name} ({b.location})")
        if b.notes:
            lines.append(f"  - {b.notes}")

    return "\n".join(lines)