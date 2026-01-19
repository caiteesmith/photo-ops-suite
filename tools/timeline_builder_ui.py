# =========================
# file: tools/timeline_builder_ui.py
# =========================
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


def _fmt_minutes_hm(minutes: int) -> str:
    """
    Render minutes as 'X hr Y min' / 'X hr' / 'Y min'.
    """
    mins = int(minutes or 0)
    hours = mins // 60
    rem = mins % 60

    if hours and rem:
        return f"{hours} hr {rem} min"
    if hours:
        return f"{hours} hr" if hours == 1 else f"{hours} hrs"
    return f"{rem} min"


def render_timeline_builder():
    defaults = load_defaults()
    event_defaults = defaults.get("reception_event_defaults", {})

    st.subheader("📸 Wedding Day Timeline Builder")
    st.markdown(
        """
        This timeline builder is designed for wedding photographers who want a clear, realistic flow
        to the wedding day, without stressing, over-stuffing, or guesswork.

        Build a timeline that respects coverage limits, portrait priorities, and real-world logistics,
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
        st.markdown("### Coverage Details")

        couple = st.text_input("Couple's Name", "Johnny & June")

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
            "Early arrival/setup minutes (optional)",
            min_value=0,
            max_value=60,
            value=int(defaults.get("arrival_setup_minutes", 0)),
        )

        photographer_arrival_time = parse_optional_time(wedding_date, photographer_arrival_str)

        st.markdown("### Locations")
        st.caption("Define your location or use the default values.")
        getting_ready_location = st.text_input("Getting ready location", value="Getting ready location")
        ceremony_location = st.text_input("Ceremony location", value="Ceremony location")
        portraits_location = st.text_input("Portraits location", value="Portraits location")
        reception_location = st.text_input("Reception location", value="Reception location")

        st.markdown("### Travel")
        travel_gr_to_ceremony = st.number_input(
            "Getting ready → ceremony",
            min_value=0,
            max_value=240,
            value=int(defaults.get("travel_gr_to_ceremony_minutes", 15)),
        )
        travel_ceremony_to_reception = st.number_input(
            "Ceremony → reception",
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
            value=int(defaults.get("buffer_minutes", 0)),
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
        dancefloor_mins = st.number_input(
            "Dancefloor coverage minutes",
            min_value=0,
            max_value=240,
            value=int(defaults.get("dancefloor_minutes", 90)),
        )

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
        ge_mins = st.number_input(
            "Grand entrance minutes",
            min_value=2,
            max_value=30,
            value=int(event_defaults.get("grand_entrance_minutes", 10)),
        )
        fd_mins = st.number_input(
            "First dance minutes",
            min_value=2,
            max_value=20,
            value=int(event_defaults.get("first_dance_minutes", 8)),
        )
        pd_mins = st.number_input(
            "Parent dances minutes",
            min_value=2,
            max_value=25,
            value=int(event_defaults.get("parent_dances_minutes", 10)),
        )
        toasts_mins = st.number_input(
            "Toasts minutes",
            min_value=5,
            max_value=60,
            value=int(event_defaults.get("toasts_minutes", 20)),
        )
        dinner_mins = st.number_input(
            "Dinner minutes",
            min_value=30,
            max_value=120,
            value=int(event_defaults.get("dinner_minutes", 60)),
        )
        cake_mins = st.number_input(
            "Cake cutting minutes",
            min_value=3,
            max_value=30,
            value=int(event_defaults.get("cake_cutting_minutes", 10)),
        )
        bouquet_mins = st.number_input(
            "Bouquet toss minutes",
            min_value=0,
            max_value=20,
            value=int(event_defaults.get("bouquet_toss_minutes", 8)),
        )
        garter_mins = st.number_input(
            "Garter toss minutes",
            min_value=0,
            max_value=15,
            value=int(event_defaults.get("garter_toss_minutes", 5)),
        )

    with colB:
        st.markdown("### Timeline")

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
                portraits_location=portraits_location,
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

            # Add couple + date context row in the UI
            st.info(
                f"🤍 {couple}, {wedding_date} 📸 "
                f"Coverage: {coverage_hours:g} hrs, "
                f"from {coverage_start.strftime('%-I:%M %p')} to {coverage_end.strftime('%-I:%M %p')}"
            )

            totals = coverage_totals(blocks, coverage_start, coverage_end)

            # Add couple + date as columns in the timeline table / CSV
            df_display = df.copy()
            # df_display.insert(0, "Couple", couple)
            # df_display.insert(1, "Wedding Date", wedding_date)

            with st.expander("⏱️ Coverage allocation", expanded=True):
                m0, m1, m2, m3 = st.columns(4)

                m0.metric(
                    "Coverage Hours",
                    f"{inputs.coverage_hours:g} hrs",
                )

                m1.metric(
                    "Coverage Used",
                    totals["in_coverage_minutes"],
                    delta=_fmt_minutes_hm(totals["in_coverage_minutes"]),
                )
                m2.metric(
                    "Timeline Scheduled",
                    totals["scheduled_minutes_total"],
                    delta=_fmt_minutes_hm(totals["scheduled_minutes_total"]),
                )
                m3.metric(
                    "Over Coverage",
                    totals["overage_minutes"],
                    delta=_fmt_minutes_hm(totals["overage_minutes"]),
                )

                st.markdown("### Timeline")
                st.dataframe(df_display, use_container_width=True, hide_index=True)

                st.caption(
                    "Tip: if you're over coverage, the fastest wins are usually reducing "
                    "time for portraits or tightening buffers/travel assumptions."
                )

            if warnings:
                for w in warnings:
                    st.warning(w)

            st.markdown("### Exports")
            couplesName = couple.replace(" ", "_").replace("&", "and")

            # Format date safely (fallback if blank/malformed)
            weddingDate = wedding_date.strip() or "wedding"

            csv_bytes = df_display.to_csv(index=False).encode("utf-8")

            st.download_button(
                "Download timeline CSV",
                data=csv_bytes,
                file_name=f"{couplesName}_{weddingDate}_timeline.csv",
                mime="text/csv",
            )

            st.markdown("#### Copy/paste version")
            timeline_header = (
                f"{couple}: {wedding_date}\n"
                f"Coverage: {coverage_start.strftime('%-I:%M %p')}-"
                f"{coverage_end.strftime('%-I:%M %p')} "
                f"({coverage_hours:g} hrs)\n"
            )
            timeline_text = timeline_header + "\n" + blocks_to_text(blocks)
            st.text_area("Timeline text", value=timeline_text, height=320)

        except Exception as e:
            st.error(f"Couldn't generate timeline yet: {e}")
            st.info("Tip: Use times like '4:00 PM' and date like '2026-06-20'.")