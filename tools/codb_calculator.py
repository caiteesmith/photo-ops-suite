# =========================================
# file: tools/codb_calculator.py
# =========================================
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


# -------------------------
# Data models
# -------------------------
@dataclass
class WeddingCODBInputs:
    # Annual fixed costs
    insurance_annual: float
    software_annual: float
    website_annual: float
    accounting_legal_annual: float
    education_annual: float
    marketing_annual: float
    office_annual: float
    other_fixed_annual: float

    # Gear depreciation (annualized)
    gear_replacement_annual: float

    # Wedding volume
    weddings_per_year: int

    # Variable costs per wedding (averages)
    second_shooter_per_wedding: float
    assistant_per_wedding: float
    travel_per_wedding: float
    lodging_per_wedding: float
    meals_per_wedding: float
    delivery_packaging_per_wedding: float
    gallery_overages_per_wedding: float
    album_prints_per_wedding: float
    other_variable_per_wedding: float

    # Time per wedding (hours)
    inquiry_booking_hours: float
    planning_hours: float
    engagement_hours: float
    wedding_day_hours: float
    travel_hours: float
    culling_hours: float
    editing_hours: float
    export_upload_hours: float
    delivery_admin_hours: float
    blogging_vendor_hours: float

    # Income & pricing inputs
    # Interpreted as *take-home* (after tax) in the UI/calcs below
    target_take_home_income_annual: float
    # Simple effective rate (federal + state + self-employment blended)
    effective_tax_rate_pct: float
    target_profit_margin_pct: float  # e.g. 20 = 20%
    current_avg_price_per_wedding: float
    effective_tax_rate_pct: float  # e.g. 25–35%

@dataclass
class WeddingCODBResults:
    annual_fixed_costs: float
    annual_total_costs: float
    avg_variable_cost_per_wedding: float
    fixed_cost_allocation_per_wedding: float
    true_cost_per_wedding: float

    total_hours_per_wedding: float

    break_even_price_per_wedding_no_profit: float
    recommended_price_per_wedding_with_profit: float

    gross_profit_per_wedding_at_current_price: float
    net_profit_per_wedding_at_current_price: float  # net after allocating fixed costs
    effective_hourly_at_current_price: float

    weddings_needed_to_hit_income_goal_at_current_price: float


# -------------------------
# Helpers
# -------------------------
def _money(x: float) -> str:
    return f"${x:,.0f}"


def _pct(x: float) -> str:
    return f"{x:.0f}%"


def _clamp_nonneg(x: float) -> float:
    try:
        return max(0.0, float(x))
    except Exception:
        return 0.0


def _clamp_int_min1(x: int) -> int:
    try:
        return max(1, int(x))
    except Exception:
        return 1


def compute_results(inp: WeddingCODBInputs) -> WeddingCODBResults:
    weddings = _clamp_int_min1(inp.weddings_per_year)

    annual_fixed = (
        _clamp_nonneg(inp.insurance_annual)
        + _clamp_nonneg(inp.software_annual)
        + _clamp_nonneg(inp.website_annual)
        + _clamp_nonneg(inp.accounting_legal_annual)
        + _clamp_nonneg(inp.education_annual)
        + _clamp_nonneg(inp.marketing_annual)
        + _clamp_nonneg(inp.office_annual)
        + _clamp_nonneg(inp.other_fixed_annual)
        + _clamp_nonneg(inp.gear_replacement_annual)
    )

    avg_variable = (
        _clamp_nonneg(inp.second_shooter_per_wedding)
        + _clamp_nonneg(inp.assistant_per_wedding)
        + _clamp_nonneg(inp.travel_per_wedding)
        + _clamp_nonneg(inp.lodging_per_wedding)
        + _clamp_nonneg(inp.meals_per_wedding)
        + _clamp_nonneg(inp.delivery_packaging_per_wedding)
        + _clamp_nonneg(inp.gallery_overages_per_wedding)
        + _clamp_nonneg(inp.album_prints_per_wedding)
        + _clamp_nonneg(inp.other_variable_per_wedding)
    )

    fixed_alloc = annual_fixed / weddings
    true_cost = avg_variable + fixed_alloc

    total_hours = (
        _clamp_nonneg(inp.inquiry_booking_hours)
        + _clamp_nonneg(inp.planning_hours)
        + _clamp_nonneg(inp.engagement_hours)
        + _clamp_nonneg(inp.wedding_day_hours)
        + _clamp_nonneg(inp.travel_hours)
        + _clamp_nonneg(inp.culling_hours)
        + _clamp_nonneg(inp.editing_hours)
        + _clamp_nonneg(inp.export_upload_hours)
        + _clamp_nonneg(inp.delivery_admin_hours)
        + _clamp_nonneg(inp.blogging_vendor_hours)
    )

    # Income allocation per wedding (gross-up take-home for taxes)
    tax_rate = max(0.0, min(0.9, float(inp.effective_tax_rate_pct) / 100.0))
    target_take_home = _clamp_nonneg(inp.target_take_home_income_annual)

    required_pre_tax_income = (
        target_take_home / (1.0 - tax_rate) if tax_rate < 1.0 else target_take_home
    )

    income_per_wedding = required_pre_tax_income / weddings
    break_even_no_profit = true_cost + income_per_wedding

    profit_pct = max(0.0, min(95.0, float(inp.target_profit_margin_pct)))  # keep sane
    # Profit margin means: profit = margin * price => price = cost/(1-margin)
    recommended_with_profit = (
        break_even_no_profit / (1 - (profit_pct / 100.0)) if profit_pct < 100 else break_even_no_profit
    )

    current_price = _clamp_nonneg(inp.current_avg_price_per_wedding)
    gross_profit_current = current_price - avg_variable
    net_profit_current = current_price - true_cost
    effective_hourly = (net_profit_current / total_hours) if total_hours > 0 else 0.0

    # Weddings needed to hit income goal using net profit (after fixed allocation)
    # If net per wedding is <= 0, then you effectively can't hit it with that price.
    if net_profit_current > 0:
        weddings_needed = required_pre_tax_income / net_profit_current
    else:
        weddings_needed = float("inf")

    annual_total = annual_fixed + (avg_variable * weddings)

    return WeddingCODBResults(
        annual_fixed_costs=annual_fixed,
        annual_total_costs=annual_total,
        avg_variable_cost_per_wedding=avg_variable,
        fixed_cost_allocation_per_wedding=fixed_alloc,
        true_cost_per_wedding=true_cost,
        total_hours_per_wedding=total_hours,
        break_even_price_per_wedding_no_profit=break_even_no_profit,
        recommended_price_per_wedding_with_profit=recommended_with_profit,
        gross_profit_per_wedding_at_current_price=gross_profit_current,
        net_profit_per_wedding_at_current_price=net_profit_current,
        effective_hourly_at_current_price=effective_hourly,
        weddings_needed_to_hit_income_goal_at_current_price=weddings_needed,
    )


def _defaults() -> WeddingCODBInputs:
    # Reasonable starter defaults (edit as you want)
    return WeddingCODBInputs(
        insurance_annual=900,
        software_annual=900,  # LR/PS + galleries/CRM etc.
        website_annual=350,
        accounting_legal_annual=600,
        education_annual=800,
        marketing_annual=1200,
        office_annual=0,
        other_fixed_annual=300,
        gear_replacement_annual=1500,
        weddings_per_year=20,
        second_shooter_per_wedding=450,
        assistant_per_wedding=0,
        travel_per_wedding=80,
        lodging_per_wedding=0,
        meals_per_wedding=30,
        delivery_packaging_per_wedding=10,
        gallery_overages_per_wedding=0,
        album_prints_per_wedding=0,
        other_variable_per_wedding=0,
        inquiry_booking_hours=2.0,
        planning_hours=3.0,
        engagement_hours=0.0,  # if you include engagement, put hours here
        wedding_day_hours=8.0,
        travel_hours=2.0,
        culling_hours=3.0,
        editing_hours=10.0,
        export_upload_hours=1.5,
        delivery_admin_hours=1.0,
        blogging_vendor_hours=1.0,
        target_take_home_income_annual=70000,
        effective_tax_rate_pct=30,
        target_profit_margin_pct=20,
        current_avg_price_per_wedding=4500,
    )


def _ensure_state():
    st.session_state.setdefault("codb_inputs", asdict(_defaults()))
    d = st.session_state["codb_inputs"]
    if "target_personal_income_annual" in d and "target_take_home_income_annual" not in d:
        d["target_take_home_income_annual"] = d.pop("target_personal_income_annual")
    if "effective_tax_rate_pct" not in d:
        d["effective_tax_rate_pct"] = 30
    st.session_state["codb_inputs"] = d

    st.session_state.setdefault("codb_last_saved", None)


# -------------------------
# UI
# -------------------------
def render_wedding_codb_calculator():
    _ensure_state()

    st.title("Wedding Photographer CODB Calculator")
    st.caption(
        "Figure out your true cost per wedding, break-even pricing, and what your current pricing actually nets you."
    )

    with st.expander("How to use this", expanded=False):
        st.markdown(
            """
            1) Enter your annual fixed costs (subscriptions, insurance, marketing baseline, gear replacement, etc.).  
            2) Enter your average variable costs per wedding (second shooter, travel, meals, etc.).  
            3) Enter your hours per wedding (include *everything* from inquiry to delivery).  
            4) Set your income goal and desired profit margin, then compare against your **current average price**.  
            """.strip()
        )

    colA, colB = st.columns([0.9, 1.1], gap="large")

    # --- Inputs ---
    with colA:
        st.subheader("Inputs")

        # Load dict from state, edit it, then write back
        d = dict(st.session_state["codb_inputs"])

        with st.expander("Annual fixed costs", expanded=True):
            d["insurance_annual"] = st.number_input("Insurance", min_value=0.0, value=float(d["insurance_annual"]), step=50.0)
            d["software_annual"] = st.number_input("Software stack", min_value=0.0, value=float(d["software_annual"]), step=50.0)
            d["website_annual"] = st.number_input("Website & domain", min_value=0.0, value=float(d["website_annual"]), step=25.0)
            d["accounting_legal_annual"] = st.number_input("Accounting & legal", min_value=0.0, value=float(d["accounting_legal_annual"]), step=50.0)
            d["education_annual"] = st.number_input("Education", min_value=0.0, value=float(d["education_annual"]), step=50.0)
            d["marketing_annual"] = st.number_input("Marketing baseline", min_value=0.0, value=float(d["marketing_annual"]), step=50.0)
            d["office_annual"] = st.number_input("Office/home office", min_value=0.0, value=float(d["office_annual"]), step=50.0)
            d["other_fixed_annual"] = st.number_input("Other fixed costs", min_value=0.0, value=float(d["other_fixed_annual"]), step=50.0)
            d["gear_replacement_annual"] = st.number_input(
                "Gear replacement/depreciation", min_value=0.0, value=float(d["gear_replacement_annual"]), step=100.0,
                help="Think: how much you should set aside yearly to replace bodies/lenses over time."
            )

        with st.expander("Wedding volume", expanded=True):
            d["weddings_per_year"] = st.number_input("Weddings per year", min_value=1, value=int(d["weddings_per_year"]), step=1)

        with st.expander("Variable costs per wedding (averages)", expanded=False):
            d["second_shooter_per_wedding"] = st.number_input("Second shooter", min_value=0.0, value=float(d["second_shooter_per_wedding"]), step=25.0)
            d["assistant_per_wedding"] = st.number_input("Assistant", min_value=0.0, value=float(d["assistant_per_wedding"]), step=25.0)
            d["travel_per_wedding"] = st.number_input("Travel: Gas/tolls/parking", min_value=0.0, value=float(d["travel_per_wedding"]), step=10.0)
            d["lodging_per_wedding"] = st.number_input("Lodging", min_value=0.0, value=float(d["lodging_per_wedding"]), step=25.0)
            d["meals_per_wedding"] = st.number_input("Meals", min_value=0.0, value=float(d["meals_per_wedding"]), step=5.0)
            d["delivery_packaging_per_wedding"] = st.number_input("Delivery/packaging", min_value=0.0, value=float(d["delivery_packaging_per_wedding"]), step=5.0)
            d["gallery_overages_per_wedding"] = st.number_input("Gallery hosting overages", min_value=0.0, value=float(d["gallery_overages_per_wedding"]), step=5.0)
            d["album_prints_per_wedding"] = st.number_input("Albums/prints costs", min_value=0.0, value=float(d["album_prints_per_wedding"]), step=25.0)
            d["other_variable_per_wedding"] = st.number_input("Other variable costs", min_value=0.0, value=float(d["other_variable_per_wedding"]), step=10.0)

        with st.expander("Time per wedding (hours)", expanded=False):
            d["inquiry_booking_hours"] = st.number_input("Inquiry + booking admin", min_value=0.0, value=float(d["inquiry_booking_hours"]), step=0.5)
            d["planning_hours"] = st.number_input("Planning (timeline, questionnaires, calls)", min_value=0.0, value=float(d["planning_hours"]), step=0.5)
            d["engagement_hours"] = st.number_input("Engagement session (if included)", min_value=0.0, value=float(d["engagement_hours"]), step=0.5)
            d["wedding_day_hours"] = st.number_input("Wedding day coverage hours", min_value=0.0, value=float(d["wedding_day_hours"]), step=0.5)
            d["travel_hours"] = st.number_input("Travel time", min_value=0.0, value=float(d["travel_hours"]), step=0.5)
            d["culling_hours"] = st.number_input("Culling", min_value=0.0, value=float(d["culling_hours"]), step=0.5)
            d["editing_hours"] = st.number_input("Editing", min_value=0.0, value=float(d["editing_hours"]), step=0.5)
            d["export_upload_hours"] = st.number_input("Export + upload", min_value=0.0, value=float(d["export_upload_hours"]), step=0.5)
            d["delivery_admin_hours"] = st.number_input("Delivery + admin follow-up", min_value=0.0, value=float(d["delivery_admin_hours"]), step=0.5)
            d["blogging_vendor_hours"] = st.number_input("Blogging + vendor outreach", min_value=0.0, value=float(d["blogging_vendor_hours"]), step=0.5)

        with st.expander("Income & pricing", expanded=True):
            d["target_take_home_income_annual"] = st.number_input(
                "Target take-home income (annual)",
                min_value=0.0,
                value=float(d.get("target_take_home_income_annual", 70000)),
                step=1000.0,
                help="Your goal after taxes (roughly). The calculator will gross this up using the estimated tax rate.",
                key="codb_target_take_home_income_annual",
            )

            d["effective_tax_rate_pct"] = st.slider(
                "Estimated effective tax rate (%)",
                min_value=10,
                max_value=45,
                value=int(d.get("effective_tax_rate_pct", 30)),
                help="Rough blended rate (federal + state + self-employment). Estimate only.",
                key="codb_effective_tax_rate_pct",
            )

            d["target_profit_margin_pct"] = st.slider(
                "Target profit margin (%)",
                min_value=0,
                max_value=60,
                value=int(d.get("target_profit_margin_pct", 20)),
                key="codb_target_profit_margin_pct",
            )

            d["current_avg_price_per_wedding"] = st.number_input(
                "Current average price per wedding",
                min_value=0.0,
                value=float(d.get("current_avg_price_per_wedding", 4500)),
                step=100.0,
                key="codb_current_avg_price_per_wedding",
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Reset to defaults", use_container_width=True):
                st.session_state["codb_inputs"] = asdict(_defaults())
                st.rerun()
        with c2:
            if st.button("Save snapshot", use_container_width=True):
                st.session_state["codb_last_saved"] = {
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "inputs": dict(d),
                }
                st.success("Saved!")

        st.session_state["codb_inputs"] = d

    # --- Results ---
    with colB:
        inp = WeddingCODBInputs(**st.session_state["codb_inputs"])
        res = compute_results(inp)

        st.subheader("Results")

        m1, m2, m3 = st.columns(3)
        m1.metric("True cost per wedding", _money(res.true_cost_per_wedding))
        m2.metric("Break-even price (incl. taxes)", _money(res.break_even_price_per_wedding_no_profit))
        m3.metric("Recommended price (with profit)", _money(res.recommended_price_per_wedding_with_profit))

        st.divider()

        m4, m5, m6 = st.columns(3)
        m4.metric("Hours per wedding", f"{res.total_hours_per_wedding:.1f} hrs")
        m5.metric("Net profit per wedding (current price)", _money(res.net_profit_per_wedding_at_current_price))
        m6.metric("Effective hourly (current price)", f"${res.effective_hourly_at_current_price:,.0f}/hr")

        # Warnings / insights
        st.divider()
        st.subheader("Insights")

        current_price = float(inp.current_avg_price_per_wedding)
        gap = res.recommended_price_per_wedding_with_profit - current_price

        if res.net_profit_per_wedding_at_current_price <= 0:
            st.error(
                "At your current average price, you're not covering your total costs (after fixed-cost allocation). "
                "This usually means your fixed costs are too high for your volume, your time is undercounted, or pricing needs to move."
            )
        elif res.effective_hourly_at_current_price < 35:
            st.warning(
                f"Your effective hourly rate at your current price is about ${res.effective_hourly_at_current_price:,.0f}/hr. "
                "If that feels low, your quickest levers are pricing, outsourcing, reducing editing time, or increasing volume."
            )
        else:
            st.success("This looks sustainable on paper! Now sanity-check your time estimates and seasonal workload.")

        delta = res.recommended_price_per_wedding_with_profit - float(inp.current_avg_price_per_wedding)
        delta_str = f"{'up' if delta >= 0 else 'down'} {_money(abs(delta))}"

        st.info(
            f"To hit your target profit margin of {_pct(inp.target_profit_margin_pct)}, "
            f"your recommended price is {_money(res.recommended_price_per_wedding_with_profit)} — "
            f"that’s {delta_str} vs your current avg."
        )

        if res.weddings_needed_to_hit_income_goal_at_current_price == float("inf"):
            st.warning(
                "With your current average price and costs, the model can't reach your income goal (net profit per wedding is ≤ 0)."
            )
        else:
            st.caption(
                f"Estimated weddings needed to hit your annual income goal at current pricing: "
                f"{res.weddings_needed_to_hit_income_goal_at_current_price:.1f}"
            )

        # Breakdowns
        st.divider()
        st.subheader("Breakdowns")

        cost_df = pd.DataFrame(
            [
                {"Category": "Annual: Fixed costs", "Amount": res.annual_fixed_costs},
                {"Category": "Annual: Variable costs", "Amount": res.avg_variable_cost_per_wedding * inp.weddings_per_year},
                {"Category": "Annual: Total costs", "Amount": res.annual_total_costs},
            ]
        )
        st.dataframe(cost_df, use_container_width=True, hide_index=True)

        per_wedding_df = pd.DataFrame(
            [
                {"Category": "Fixed allocation per wedding", "Amount": res.fixed_cost_allocation_per_wedding},
                {"Category": "Avg variable cost per wedding", "Amount": res.avg_variable_cost_per_wedding},
                {"Category": "True cost per wedding", "Amount": res.true_cost_per_wedding},
            ]
        )
        st.dataframe(per_wedding_df, use_container_width=True, hide_index=True)

        hours_df = pd.DataFrame(
            [
                ("Inquiry + booking", inp.inquiry_booking_hours),
                ("Planning", inp.planning_hours),
                ("Engagement (if included)", inp.engagement_hours),
                ("Wedding day coverage", inp.wedding_day_hours),
                ("Travel", inp.travel_hours),
                ("Culling", inp.culling_hours),
                ("Editing", inp.editing_hours),
                ("Export + upload", inp.export_upload_hours),
                ("Delivery + admin", inp.delivery_admin_hours),
                ("Blogging + vendor outreach", inp.blogging_vendor_hours),
            ],
            columns=["Stage", "Hours"],
        )
        st.dataframe(hours_df, use_container_width=True, hide_index=True)

        # Export
        st.divider()
        st.subheader("Export")
        export_payload = {
            "inputs": asdict(inp),
            "results": asdict(res),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

        st.download_button(
            "Download JSON summary",
            data=pd.Series(export_payload).to_json(indent=2),
            file_name="wedding_codb_summary.json",
            mime="application/json",
            use_container_width=True,
        )

        # Optional: CSV of key results
        key_results_df = pd.DataFrame(
            [
                {"Metric": "Annual fixed costs", "Value": res.annual_fixed_costs},
                {"Metric": "Avg variable cost per wedding", "Value": res.avg_variable_cost_per_wedding},
                {"Metric": "True cost per wedding", "Value": res.true_cost_per_wedding},
                {"Metric": "Hours per wedding", "Value": res.total_hours_per_wedding},
                {"Metric": "Break-even (no profit)", "Value": res.break_even_price_per_wedding_no_profit},
                {"Metric": "Recommended (with profit)", "Value": res.recommended_price_per_wedding_with_profit},
                {"Metric": "Net profit per wedding (current price)", "Value": res.net_profit_per_wedding_at_current_price},
                {"Metric": "Effective hourly (current price)", "Value": res.effective_hourly_at_current_price},
            ]
        )

        st.download_button(
            "Download CSV (key results)",
            data=key_results_df.to_csv(index=False),
            file_name="wedding_codb_key_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # Saved snapshot viewer
        snap = st.session_state.get("codb_last_saved")
        if snap:
            with st.expander("Last saved snapshot", expanded=False):
                st.caption(f"Saved at: {snap.get('saved_at')}")
                st.json(snap, expanded=False)


# If you want to run this file directly for quick testing:
if __name__ == "__main__":
    st.set_page_config(page_title="Wedding CODB Calculator", layout="wide")
    render_wedding_codb_calculator()