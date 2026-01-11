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
        name="Buffer / transition",
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
        notes="Includes loading up + parking + walking time as needed.",
        audience="Vendor",
        kind="travel",
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


def coverage_allocation_by_kind(
    blocks: List[TimelineBlock],
    coverage_start: datetime,
    coverage_end: datetime
) -> pd.DataFrame:
    """
    Returns time IN coverage window, grouped by Kind.
    Displays combined string: '90 min (1.5 hr)'.
    """
    rows = []
    for b in blocks:
        if b.kind == "coverage":
            continue

        mins = _overlap_minutes(b.start, b.end, coverage_start, coverage_end)
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

    grouped["Time Used"] = grouped["Minutes"].apply(
        lambda m: f"{m} min ({round(m / 60, 2)} hr)"
    )

    return grouped[["Kind", "Time Used"]]


def coverage_allocation_top_blocks(
    blocks: List[TimelineBlock],
    coverage_start: datetime,
    coverage_end: datetime,
    top_n: int = 8
) -> pd.DataFrame:
    """
    Shows top N time sinks by minutes-in-coverage,
    displayed chronologically with combined time string.
    """
    rows = []
    for b in blocks:
        if b.kind == "coverage":
            continue

        mins = _overlap_minutes(b.start, b.end, coverage_start, coverage_end)
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
        return pd.DataFrame(
            columns=["Start", "End", "Block", "Kind", "Time Used", "Location"]
        )

    df = pd.DataFrame(rows)

    # Pick top N by duration
    df = df.sort_values("MinutesSort", ascending=False).head(top_n)

    # Display chronologically
    df = (
        df.sort_values("StartDT")
        .drop(columns=["StartDT", "MinutesSort"])
        .reset_index(drop=True)
    )

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
        if b.kind == "coverage":
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


# ---------- Main timeline builder ----------
def build_timeline(inputs: EventInputs) -> Tuple[List[TimelineBlock], List[str]]:
    blocks: List[TimelineBlock] = []
    warnings: List[str] = []

    # ------------------------
    # PRE-CEREMONY
    # ------------------------
    t = inputs.coverage_start

    t = _add_block(
        blocks,
        "Flat lay + details",
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
        "Getting dressed + final touches",
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
        notes="Each partner individually (or solo portraits) while everyone’s fresh.",
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
            inputs.ceremony_location,
            notes="Private moment + first reactions.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

        # If there IS a first look, do ALL portraits pre-ceremony
        dyn_note = _family_dynamics_notes(inputs)
        fam_minutes = _family_minutes(inputs)

        # Couple portraits
        t = _add_block(
            blocks,
            "Couple portraits (pre-ceremony)",
            t,
            inputs.couple_portraits_minutes,
            inputs.ceremony_location,
            notes="All couple portraits completed pre-ceremony when first look is scheduled.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

        # Wedding party portraits
        t = _add_block(
            blocks,
            "Wedding party portraits (pre-ceremony)",
            t,
            inputs.wedding_party_portraits_minutes,
            inputs.ceremony_location,
            notes="All wedding party portraits completed pre-ceremony when first look is scheduled.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

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
            "Family portraits (pre-ceremony)",
            t,
            fam_minutes,
            inputs.ceremony_location,
            notes=("All family formals completed pre-ceremony when first look is scheduled. " + dyn_note).strip(),
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes + extra_family_buffer, inputs.ceremony_location)

    # Pre-ceremony tuckaway
    if t < inputs.ceremony_start:
        slack = minutes_between(t, inputs.ceremony_start)

        tuck_mins = min(int(inputs.tuckaway_minutes), int(slack))
        if tuck_mins > 0:
            t = _add_block(
                blocks,
                "Tuckaway (pre-ceremony) — guest arrivals + ceremony details",
                t,
                tuck_mins,
                inputs.ceremony_location,
                notes="Guest arrivals candids + ceremony space details (programs, florals, wide shots, signage).",
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
                "No time available before the ceremony for tuckaway (guest arrivals + ceremony details). "
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

    # Quick reset
    t = _add_block(
        blocks,
        "Quick reset (post-ceremony)",
        t,
        max(8, int(inputs.buffer_minutes)),
        inputs.ceremony_location,
        notes="Water, touch-ups, bustle, regroup before portraits.",
        audience="Vendor",
        kind="buffer",
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
    # POST-CEREMONY
    # ------------------------
    if inputs.first_look:
        # No portraits post-ceremony (except optional sunset photos later)
        t = _add_block(
            blocks,
            "Cocktail hour coverage",
            t,
            inputs.cocktail_hour_minutes,
            inputs.ceremony_location,
            notes="Candids + room atmosphere. Portraits are already completed pre-ceremony.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

    else:
        # No first look → portraits happen post-ceremony (often during cocktail hour)
        t = _add_block(
            blocks,
            "Family portraits",
            t,
            fam_minutes,
            inputs.ceremony_location,
            notes=("Keep list tight + assign a wrangler. " + dyn_note).strip(),
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes + extra_family_buffer, inputs.ceremony_location)

        t = _add_block(
            blocks,
            "Wedding party portraits",
            t,
            inputs.wedding_party_portraits_minutes,
            inputs.ceremony_location,
            notes="Full group + smaller combos.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

        t = _add_block(
            blocks,
            "Couple portraits",
            t,
            inputs.couple_portraits_minutes,
            inputs.ceremony_location,
            notes="Aim for flattering light + a little breathing room.",
            audience="Vendor",
            kind="photo",
        )
        t = _add_buffer(blocks, t, inputs.buffer_minutes, inputs.ceremony_location)

        # Cocktail hour feasibility warning remains relevant here
        est_post = fam_minutes + inputs.wedding_party_portraits_minutes + inputs.couple_portraits_minutes
        if inputs.receiving_line:
            est_post += inputs.receiving_line_minutes
        if est_post > inputs.cocktail_hour_minutes:
            warnings.append(
                f"No first look: estimated post-ceremony portraits ~{est_post} min vs cocktail hour "
                f"{inputs.cocktail_hour_minutes} min. Expect tight timing unless portrait time is reduced or cocktail hour extended."
            )

    # Cocktail hour feasibility warning (no first look)
    if not inputs.first_look:
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
    # TRAVEL TO RECEPTION
    # ------------------------
    t = _add_travel(blocks, t, inputs.travel_ceremony_to_reception_minutes, "Ceremony → Reception")

    # Reception start anchor (optional)
    if inputs.reception_start and t > inputs.reception_start:
        late = minutes_between(inputs.reception_start, t)
        warnings.append(f"Arrives {late} min after reception start time you entered (portraits/travel may be too long).")

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

    schedule_event_if_toggle("Cake cutting", re.cake_cutting, re.cake_cutting_time, re.cake_cutting_minutes, "Cake cutting.")
    schedule_event_if_toggle("Bouquet toss", re.bouquet_toss, re.bouquet_toss_time, re.bouquet_toss_minutes, "Bouquet toss.")
    schedule_event_if_toggle("Garter toss", re.garter_toss, re.garter_toss_time, re.garter_toss_minutes, "Garter toss.")

    # Golden hour reminder
    if inputs.sunset_time:
        golden_start = add_minutes(inputs.sunset_time, -30)
        golden_end = add_minutes(golden_start, inputs.golden_hour_window_minutes)
        warnings.append(
            f"Sunset is around {safe_fmt_time(inputs.sunset_time)}. Consider reserving "
            f"{inputs.golden_hour_window_minutes} min for golden hour portraits around "
            f"{safe_fmt_time(golden_start)}–{safe_fmt_time(golden_end)}."
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
    return pd.DataFrame(rows)


def blocks_to_text(blocks: List[TimelineBlock], audience_filter: str | None = None) -> str:
    lines: List[str] = []
    for b in blocks:
        if audience_filter and b.audience != audience_filter:
            continue
        if b.kind == "coverage" and b.start == b.end:
            lines.append(f"{safe_fmt_time(b.start)} • {b.name}")
            if b.notes:
                lines.append(f"  - {b.notes}")
            continue

        lines.append(f"{safe_fmt_time(b.start)}–{safe_fmt_time(b.end)} • {b.name} ({b.location})")
        if b.notes:
            lines.append(f"  - {b.notes}")
    return "\n".join(lines)