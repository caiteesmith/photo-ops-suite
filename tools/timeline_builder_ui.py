from __future__ import annotations
from pathlib import Path

import json
import streamlit as st

from core.models import EventInputs, FamilyDynamics, ReceptionEvents
from core.timeutils import parse_hhmm, add_hours
from tools.timeline_builder import (
    build_timeline,
    blocks_to_dataframe,
    blocks_to_text,
    coverage_allocation_by_kind,
    coverage_allocation_top_blocks,
    coverage_totals,
)

DEFAULTS_PATH = Path(__file__).parent / "defaults.json"

def load_defaults() -> dict:
    if DEFAULTS_PATH.exists():
        return json.loads(DEFAULTS_PATH.read_text())
    return {}


def parse_optional_time(wedding_date: str, raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    return parse_hhmm(wedding_date, raw)

def render_timeline_builder():
    defaults = load_defaults()
    event_defaults = defaults.get("reception_event_defaults", {})

    st.subheader("📸 Wedding Day Timeline Builder")
    st.markdown(
        """
        This timeline builder is designed for wedding photographers who want a **clear, realistic flow**
        to the wedding day, without stressing, over-stuffing, or guesswork.

        Build a timeline that respects **coverage limits**, **portrait priorities**, and **real-world logistics**,
        then quickly spot where time is tight and where adjustments will make the biggest impact.
        """
    )

    with st.expander("How to use this timeline builder", expanded=False):
        st.markdown(
            """
            **1. Start with coverage**
            - Enter your coverage start time and total hours first.
            - This defines the boundaries of the day and keeps everything grounded in reality.

            **2. Work top-down through the day**
            - Add arrival, getting ready, portraits, ceremony, and reception details in order.
            - If you don't use a section, set it to **0 minutes** or leave it off.

            **3. First look matters**
            - If a first look is selected, *all portraits (except sunset)* are completed **before the ceremony**.
            - If not, portraits shift to the post-ceremony window, often overlapping cocktail hour.

            **4. Be honest about family dynamics**
            - Divorced parents, strained relationships, or large families often require extra time.
            - This tool adds notes and small buffers where those realities usually show up.

            **5. Watch the coverage allocation**
            - Use the **Coverage allocation** section to see what's eating the most time.
            - If you're over coverage, portraits and travel are usually the fastest places to adjust.

            **6. Use the timeline as a planning tool, not a promise**
            - This is a working timeline to help guide conversations with couples and planners.
            - Real wedding days flex. The goal is clarity, not rigidity.
            """
        )

    st.caption("Designed to support thoughtful planning, not stressful, over-packed timelines.")

    colA, colB = st.columns([1, 1])

    with colA:
        st.markdown("### Inputs")

        wedding_date = st.text_input("Wedding date (YYYY-MM-DD)", value="2026-06-20")

        coverage_start_str = st.text_input("Coverage start time", value="12:00 PM")

        coverage_hours_choice = st.selectbox(
            "Coverage hours",
            options=[6, 8, 10, 12, "Custom"],
            index=1,
        )
        if coverage_hours_choice == "Custom":
            coverage_hours = st.number_input(
                "Custom coverage hours",
                min_value=1.0,
                max_value=18.0,
                value=float(defaults.get("coverage_hours", 8)),
                step=0.5,
            )
        else:
            coverage_hours = float(coverage_hours_choice)

        ceremony_start_str = st.text_input("Ceremony start time", value="4:00 PM")
        ceremony_minutes = st.number_input(
            "Ceremony length (minutes)",
            min_value=10,
            max_value=120,
            value=int(defaults.get("ceremony_minutes", 30)),
        )

        st.markdown("### Photographer arrival")
        photographer_arrival_str = st.text_input("Photographer arrival time (optional)", value="")
        arrival_setup_minutes = st.number_input(
            "Arrival/setup minutes (optional)",
            min_value=0,
            max_value=60,
            value=int(defaults.get("arrival_setup_minutes", 0)),
        )

        photographer_arrival_time = parse_optional_time(wedding_date, photographer_arrival_str)

        st.markdown("### Locations")
        getting_ready_location = st.text_input("Getting ready location", value="Getting ready location")
        ceremony_location = st.text_input("Ceremony location", value="Ceremony location")
        reception_location = st.text_input("Reception location", value="Reception location")

        st.markdown("### Travel")
        travel_gr_to_ceremony = st.number_input(
            "Getting ready → ceremony (min)",
            min_value=0,
            max_value=240,
            value=int(defaults.get("travel_gr_to_ceremony_minutes", 15)),
        )
        travel_ceremony_to_reception = st.number_input(
            "Ceremony → reception (min)",
            min_value=0,
            max_value=240,
            value=int(defaults.get("travel_ceremony_to_reception_minutes", 15)),
        )

        st.markdown("### Big Decisions")
        first_look = st.toggle("First look", value=True)
        protect_cocktail_hour = st.toggle("Protect cocktail hour (minimize portraits during cocktail hour)", value=True)

        receiving_line = st.toggle("Receiving line after ceremony", value=False)
        receiving_line_minutes = st.number_input(
            "Receiving line minutes",
            min_value=0,
            max_value=45,
            value=int(defaults.get("receiving_line_minutes", 15)),
        )

        st.markdown("### Family dynamics (adds buffer + notes)")
        divorced_parents = st.toggle("Divorced parents", value=False)
        remarried_parents = st.toggle("Remarried parents", value=False)
        strained_relationships = st.toggle("Strained relationships", value=False)
        finicky_family = st.toggle("Finicky family members", value=False)
        family_notes = st.text_area("Family dynamics notes (optional)", value="", height=80)

        st.markdown("### Photo blocks")
        buffer_minutes = st.number_input(
            "Buffer between blocks (min)",
            min_value=0,
            max_value=30,
            value=int(defaults.get("buffer_minutes", 15)),
        )
        flatlay_details_minutes = st.number_input(
            "Flat lay + details (min)",
            min_value=0,
            max_value=90,
            value=int(defaults.get("flatlay_details_minutes", 30)),
        )
        getting_dressed_minutes = st.number_input(
            "Getting dressed (min)",
            min_value=0,
            max_value=90,
            value=int(defaults.get("getting_dressed_minutes", 30)),
        )
        individual_portraits_minutes = st.number_input(
            "Individual portraits (min)",
            min_value=0,
            max_value=90,
            value=int(defaults.get("individual_portraits_minutes", 30)),
        )
        tuckaway_minutes = st.number_input(
            "Tuckaway before ceremony (guest arrivals + ceremony details) (min)",
            min_value=0,
            max_value=60,
            value=int(defaults.get("tuckaway_minutes", 30)),
        )
        first_look_minutes = st.number_input(
            "First look block (min)",
            min_value=0,
            max_value=60,
            value=int(defaults.get("first_look_minutes", 15)),
        )
        couple_portraits_minutes = st.number_input(
            "Couple portraits (min)",
            min_value=0,
            max_value=120,
            value=int(defaults.get("couple_portraits_minutes", 45)),
        )
        wedding_party_portraits_minutes = st.number_input(
            "Wedding party portraits (min)",
            min_value=0,
            max_value=120,
            value=int(defaults.get("wedding_party_portraits_minutes", 30)),
        )

        st.markdown("### Family portraits sizing")
        use_groupings = st.toggle("Family portraits: use # of groupings", value=False)
        minutes_per_grouping = st.number_input(
            "Minutes per family grouping",
            min_value=1,
            max_value=10,
            value=int(defaults.get("minutes_per_family_grouping", 3)),
        )

        family_groupings = None
        if use_groupings:
            family_groupings = st.number_input("# of family groupings", min_value=1, max_value=60, value=10)
            family_portraits_minutes = int(defaults.get("family_portraits_minutes", 30))
        else:
            family_portraits_minutes = st.number_input(
                "Family portraits (min)",
                min_value=0,
                max_value=120,
                value=int(defaults.get("family_portraits_minutes", 30)),
            )

        st.markdown("### Cocktail Hour + Sunset")
        cocktail_hour_minutes = st.number_input(
            "Cocktail hour length (min)",
            min_value=30,
            max_value=180,
            value=int(defaults.get("cocktail_hour_minutes", 60)),
        )
        sunset_time_str = st.text_input("Sunset time (optional)", value="")
        golden_window = st.number_input(
            "Golden hour portrait window (min)",
            min_value=10,
            max_value=40,
            value=int(defaults.get("golden_hour_window_minutes", 20)),
        )

        st.markdown("### Reception")
        reception_start_str = st.text_input("Reception start time (optional)", value="")

        grand_entrance = st.toggle("Grand entrance", value=True)
        first_dance = st.toggle("First dance", value=True)
        father_daughter = st.toggle("Father/daughter dance", value=False)
        mother_son = st.toggle("Mother/son dance", value=False)
        toasts = st.toggle("Toasts", value=True)
        dinner = st.toggle("Dinner block", value=True)
        dancefloor_coverage = st.toggle("Dancefloor coverage", value=True)
        dancefloor_mins = st.number_input("Dancefloor coverage minutes", min_value=0, max_value=240, value=int(defaults.get("dancefloor_minutes", 90)))

        cake_cutting = st.toggle("Cake cutting", value=True)
        bouquet_toss = st.toggle("Bouquet toss", value=False)
        garter_toss = st.toggle("Garter toss", value=False)

        st.markdown("#### Reception event times (optional)")
        ge_time = st.text_input("Grand entrance time (optional)", value="")
        fd_time = st.text_input("First dance time (optional)", value="")
        pd_time = st.text_input("Parent dances time (optional)", value="")
        toasts_time = st.text_input("Toasts time (optional)", value="")
        dinner_time = st.text_input("Dinner start time (optional)", value="")
        cake_time = st.text_input("Cake cutting time (optional)", value="")
        bouquet_time = st.text_input("Bouquet toss time (optional)", value="")
        garter_time = st.text_input("Garter toss time (optional)", value="")

        st.markdown("#### Reception event durations")
        ge_mins = st.number_input("Grand entrance minutes", min_value=2, max_value=30, value=int(event_defaults.get("grand_entrance_minutes", 10)))
        fd_mins = st.number_input("First dance minutes", min_value=2, max_value=20, value=int(event_defaults.get("first_dance_minutes", 8)))
        pd_mins = st.number_input("Parent dances minutes", min_value=2, max_value=25, value=int(event_defaults.get("parent_dances_minutes", 10)))
        toasts_mins = st.number_input("Toasts minutes", min_value=5, max_value=60, value=int(event_defaults.get("toasts_minutes", 20)))
        dinner_mins = st.number_input("Dinner minutes", min_value=30, max_value=120, value=int(event_defaults.get("dinner_minutes", 60)))
        cake_mins = st.number_input("Cake cutting minutes", min_value=3, max_value=30, value=int(event_defaults.get("cake_cutting_minutes", 10)))
        bouquet_mins = st.number_input("Bouquet toss minutes", min_value=3, max_value=20, value=int(event_defaults.get("bouquet_toss_minutes", 8)))
        garter_mins = st.number_input("Garter toss minutes", min_value=2, max_value=15, value=int(event_defaults.get("garter_toss_minutes", 5)))

    with colB:
        st.markdown("### Output")

        try:
            coverage_start = parse_hhmm(wedding_date, coverage_start_str)
            coverage_end = add_hours(coverage_start, float(coverage_hours))

            ceremony_start = parse_hhmm(wedding_date, ceremony_start_str)
            reception_start = parse_optional_time(wedding_date, reception_start_str)
            sunset_time = parse_optional_time(wedding_date, sunset_time_str)

            family_dyn = FamilyDynamics(
                divorced_parents=bool(divorced_parents),
                remarried_parents=bool(remarried_parents),
                strained_relationships=bool(strained_relationships),
                finicky_family_members=bool(finicky_family),
                notes=family_notes or "",
            )

            rec_events = ReceptionEvents(
                grand_entrance=bool(grand_entrance),
                first_dance=bool(first_dance),
                father_daughter_dance=bool(father_daughter),
                mother_son_dance=bool(mother_son),
                toasts=bool(toasts),
                dinner=bool(dinner),

                dancefloor_coverage=bool(dancefloor_coverage),
                dancefloor_minutes=int(dancefloor_mins),

                cake_cutting=bool(cake_cutting),
                bouquet_toss=bool(bouquet_toss),
                garter_toss=bool(garter_toss),

                grand_entrance_time=parse_optional_time(wedding_date, ge_time),
                first_dance_time=parse_optional_time(wedding_date, fd_time),
                parent_dances_time=parse_optional_time(wedding_date, pd_time),
                toasts_time=parse_optional_time(wedding_date, toasts_time),
                dinner_start_time=parse_optional_time(wedding_date, dinner_time),
                cake_cutting_time=parse_optional_time(wedding_date, cake_time),
                bouquet_toss_time=parse_optional_time(wedding_date, bouquet_time),
                garter_toss_time=parse_optional_time(wedding_date, garter_time),

                grand_entrance_minutes=int(ge_mins),
                first_dance_minutes=int(fd_mins),
                parent_dances_minutes=int(pd_mins),
                toasts_minutes=int(toasts_mins),
                dinner_minutes=int(dinner_mins),
                cake_cutting_minutes=int(cake_mins),
                bouquet_toss_minutes=int(bouquet_mins),
                garter_toss_minutes=int(garter_mins),
            )

            inputs = EventInputs(
                wedding_date=wedding_date.strip() or None,

                coverage_start=coverage_start,
                coverage_hours=float(coverage_hours),
                coverage_end=coverage_end,

                photographer_arrival_time=photographer_arrival_time,
                arrival_setup_minutes=int(arrival_setup_minutes),

                ceremony_start=ceremony_start,
                ceremony_minutes=int(ceremony_minutes),

                getting_ready_location=getting_ready_location,
                ceremony_location=ceremony_location,
                reception_location=reception_location,

                travel_gr_to_ceremony_minutes=int(travel_gr_to_ceremony),
                travel_ceremony_to_reception_minutes=int(travel_ceremony_to_reception),

                first_look=bool(first_look),
                receiving_line=bool(receiving_line),
                receiving_line_minutes=int(receiving_line_minutes),

                cocktail_hour_minutes=int(cocktail_hour_minutes),
                protect_cocktail_hour=bool(protect_cocktail_hour),

                family_dynamics=family_dyn,

                buffer_minutes=int(buffer_minutes),
                flatlay_details_minutes=int(flatlay_details_minutes),
                getting_dressed_minutes=int(getting_dressed_minutes),
                individual_portraits_minutes=int(individual_portraits_minutes),
                first_look_minutes=int(first_look_minutes),
                couple_portraits_minutes=int(couple_portraits_minutes),
                wedding_party_portraits_minutes=int(wedding_party_portraits_minutes),
                family_portraits_minutes=int(family_portraits_minutes),
                tuckaway_minutes=int(tuckaway_minutes),

                family_groupings=int(family_groupings) if family_groupings else None,
                minutes_per_family_grouping=int(minutes_per_grouping),

                sunset_time=sunset_time,
                golden_hour_window_minutes=int(golden_window),

                reception_start=reception_start,
                reception_events=rec_events,
            )

            blocks, warnings = build_timeline(inputs)
            df = blocks_to_dataframe(blocks)

            st.info(
                f"Coverage window: {coverage_hours:g} hrs • "
                f"{coverage_start.strftime('%-I:%M %p')}–{coverage_end.strftime('%-I:%M %p')}"
            )

            totals = coverage_totals(blocks, coverage_start, coverage_end)
            alloc_kind = coverage_allocation_by_kind(blocks, coverage_start, coverage_end)
            top_blocks = coverage_allocation_top_blocks(blocks, coverage_start, coverage_end, top_n=8)

            with st.expander("⏱️ Coverage allocation", expanded=True):
                st.caption("**(What to shorten to stay within coverage)**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Minutes in coverage", totals["in_coverage_minutes"])
                m2.metric("Total scheduled minutes", totals["scheduled_minutes_total"])
                m3.metric("Minutes past coverage", totals["overage_minutes"])

                st.markdown("**Minutes used by category**")
                if len(alloc_kind) == 0:
                    st.caption("No in-coverage minutes to summarize yet.")
                else:
                    st.dataframe(alloc_kind, use_container_width=True, hide_index=True)

                st.markdown("### Timeline")
                st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("**Biggest time sinks**")
                if len(top_blocks) == 0:
                    st.caption("No blocks overlap with the coverage window yet.")
                else:
                    st.dataframe(top_blocks, use_container_width=True, hide_index=True)

                st.caption(
                    "Tip: if you're over coverage, the fastest wins are usually reducing "
                    "time for portraits or tightening buffers/travel assumptions."
                )

            if warnings:
                for w in warnings:
                    st.warning(w)

            st.markdown("### Exports")
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download timeline CSV", data=csv_bytes, file_name="timeline.csv", mime="text/csv")

            st.markdown("#### Copy/paste version")
            st.text_area("Timeline text", value=blocks_to_text(blocks), height=320)

        except Exception as e:
            st.error(f"Couldn't generate timeline yet: {e}")
            st.info("Tip: Use times like '4:00 PM' and date like '2026-06-20'.")

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
        if b.kind == "coverage":
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
        if b.kind == "coverage":
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
    blocks: List[TimelineBlock] = []
    warnings: List[str] = []

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
            notes="Private moment & first reactions.",
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
            "Couple portraits",
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
            "Wedding party portraits",
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
            "Family portraits",
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

    # Only add reset time if user wants buffer time
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
            notes="Candids & reception details",
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
            notes=("Keep list tight & assign a wrangler. " + dyn_note).strip(),
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
    # ✅ Reception start marker (shows in timeline)
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

        lines.append(f"{safe_fmt_time(b.start)}–{safe_fmt_time(b.end)} • {b.name} ({b.location})")
        if b.notes:
            lines.append(f"  - {b.notes}")

    return "\n".join(lines)