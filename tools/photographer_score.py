# =========================================
# file: tools/photographer_score.py
# =========================================
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


# -------------------------
# Models
# -------------------------
@dataclass
class ScoreBreakdown:
    pricing: int
    time_workflow: int
    delivery_capacity: int
    risk_resilience: int
    business_hygiene: int

    total: int
    label: str
    vibe: str
    highlights: List[str]
    fixes: List[str]


# -------------------------
# Helpers
# -------------------------
def _clamp_0_100(x: float) -> int:
    return int(max(0, min(100, round(x))))


def _band(total: int) -> Tuple[str, str]:
    if total >= 90:
        return "Sustainable Pro", "You've got systems. You've got margins. You've got peace."
    if total >= 80:
        return "Dialed In", "Solid foundation! A few tweaks and you're unstoppable."
    if total >= 70:
        return "Solid, but Stretched", "You're doing a lot right, but the margins/buffers might be thin."
    if total >= 55:
        return "High Burnout Risk", "It's working... but it's probably costing you sleep."
    return "Chaos Carry-On 🫠", "We're one busy month away from “why did I do this to myself.”"


def _score_from_choice(choice: str, mapping: Dict[str, int], default: int = 0) -> int:
    return int(mapping.get(choice, default))


def _weighted_total(b: Dict[str, int]) -> int:
    # Weights should sum to 1.0
    weights = {
        "pricing": 0.25,
        "time_workflow": 0.25,
        "delivery_capacity": 0.20,
        "risk_resilience": 0.15,
        "business_hygiene": 0.15,
    }
    total = 0.0
    for k, w in weights.items():
        total += float(b.get(k, 0)) * w
    return _clamp_0_100(total)


def _autofill_from_codb_if_available() -> Dict[str, float]:
    """
    OPTIONAL: If your CODB tool stores results in session_state, we can pull a couple signals.
    This function is safe even if nothing exists.
    """
    out: Dict[str, float] = {}

    # If you have something like st.session_state["codb_inputs"] or ["codb_results"], we can read it.
    # We won't assume structure beyond common keys.
    codb_inputs = st.session_state.get("codb_inputs")
    codb_results = st.session_state.get("codb_results")  # you may not have this — totally ok

    if isinstance(codb_inputs, dict):
        # useful hints
        out["current_price"] = float(codb_inputs.get("current_avg_price_per_wedding", 0) or 0)
        out["tax_rate"] = float(codb_inputs.get("effective_tax_rate_pct", 0) or 0)
        out["profit_margin_target"] = float(codb_inputs.get("target_profit_margin_pct", 0) or 0)

    if isinstance(codb_results, dict):
        out["effective_hourly"] = float(codb_results.get("effective_hourly_at_current_price", 0) or 0)
        out["net_profit_per_wedding"] = float(codb_results.get("net_profit_per_wedding_at_current_price", 0) or 0)

    return out


# -------------------------
# Main scoring engine
# -------------------------
def compute_score(answers: Dict[str, object]) -> ScoreBreakdown:
    highlights: List[str] = []
    fixes: List[str] = []

    # --- Pricing & CODB (0-100) ---
    pricing = 0

    pricing += _score_from_choice(
        str(answers["codb_known"]),
        {
            "Yes — I’ve done a CODB calculation": 40,
            "Rough idea": 20,
            "Nope": 0,
        },
    )

    pricing += _score_from_choice(
        str(answers["hourly_known"]),
        {
            "Yes (I know my effective hourly rate)": 30,
            "Kind of / I can estimate it": 15,
            "No": 0,
        },
    )

    pricing += _score_from_choice(
        str(answers["tax_plan"]),
        {
            "I set aside taxes from every payment": 30,
            "I set aside sometimes / when I remember": 15,
            "I wing it (April surprise)": 0,
        },
    )

    pricing = _clamp_0_100(pricing)

    # --- Time & workflow (0-100) ---
    time_workflow = 0

    # Editing hours per wedding (lower is not always better; we’re scoring predictability + intentionality)
    edit_hours = float(answers["editing_hours_per_wedding"])
    if edit_hours <= 10:
        time_workflow += 25
    elif edit_hours <= 18:
        time_workflow += 18
    elif edit_hours <= 28:
        time_workflow += 10
    else:
        time_workflow += 0

    time_workflow += _score_from_choice(
        str(answers["batching"]),
        {
            "Yes — I batch editing in focused blocks": 30,
            "Sometimes": 15,
            "No — it’s mostly squeezed in randomly": 0,
        },
    )

    time_workflow += _score_from_choice(
        str(answers["outsourcing"]),
        {
            "Yes (editing/admin help)": 25,
            "Occasionally": 12,
            "No": 0,
        },
    )

    time_workflow += _score_from_choice(
        str(answers["editing_system"]),
        {
            "Strong system (presets, workflow, consistent steps)": 20,
            "Some system, still evolving": 10,
            "Chaos / depends on the job": 0,
        },
    )

    time_workflow = _clamp_0_100(time_workflow)

    # --- Delivery & capacity (0-100) ---
    delivery_capacity = 0

    turnaround = str(answers["turnaround"])
    delivery_capacity += _score_from_choice(
        turnaround,
        {
            "Always early or on time": 35,
            "Usually on time (rarely late)": 25,
            "Sometimes late": 12,
            "Often late": 0,
        },
    )

    weddings_per_year = int(answers["weddings_per_year"])
    if weddings_per_year <= 15:
        delivery_capacity += 25
    elif weddings_per_year <= 25:
        delivery_capacity += 18
    elif weddings_per_year <= 35:
        delivery_capacity += 10
    else:
        delivery_capacity += 0

    delivery_capacity += _score_from_choice(
        str(answers["boundaries"]),
        {
            "Yes — I protect at least 1 day off weekly": 25,
            "Sometimes": 12,
            "Not really": 0,
        },
    )

    delivery_capacity += _score_from_choice(
        str(answers["buffering"]),
        {
            "Yes — I build buffers into timelines + delivery": 15,
            "Sometimes": 8,
            "No": 0,
        },
    )

    delivery_capacity = _clamp_0_100(delivery_capacity)

    # --- Risk & resilience (0-100) ---
    risk_resilience = 0

    backups = str(answers["backups"])
    risk_resilience += _score_from_choice(
        backups,
        {
            "3-2-1 backup (local + cloud + offsite)": 45,
            "Two copies (local + cloud OR local + external)": 30,
            "One backup (or inconsistent)": 10,
            "No real backup system": 0,
        },
    )

    redundancy = str(answers["gear_redundancy"])
    risk_resilience += _score_from_choice(
        redundancy,
        {
            "Yes (backup camera body + essentials)": 30,
            "Partial (some redundancy)": 15,
            "No": 0,
        },
    )

    risk_resilience += _score_from_choice(
        str(answers["sick_plan"]),
        {
            "Yes — I have a contingency plan": 25,
            "Kind of (I could figure it out)": 12,
            "No": 0,
        },
    )

    risk_resilience = _clamp_0_100(risk_resilience)

    # --- Business hygiene (0-100) ---
    business_hygiene = 0

    business_hygiene += _score_from_choice(
        str(answers["contracts"]),
        {
            "Yes — contracts + clear scope": 35,
            "Mostly (could be tighter)": 20,
            "Not consistent": 8,
            "No": 0,
        },
    )

    business_hygiene += _score_from_choice(
        str(answers["crm_system"]),
        {
            "Yes (CRM / templates / process)": 30,
            "Some templates, not fully systemized": 15,
            "Mostly manual each time": 0,
        },
    )

    business_hygiene += _score_from_choice(
        str(answers["venue_notes"]),
        {
            "Yes — I keep venue/church notes": 20,
            "Sometimes": 10,
            "No": 0,
        },
    )

    business_hygiene += _score_from_choice(
        str(answers["client_expectations"]),
        {
            "Very clear (timeline + delivery expectations set early)": 15,
            "Usually clear": 8,
            "Not consistent": 0,
        },
    )

    business_hygiene = _clamp_0_100(business_hygiene)

    breakdown = {
        "pricing": pricing,
        "time_workflow": time_workflow,
        "delivery_capacity": delivery_capacity,
        "risk_resilience": risk_resilience,
        "business_hygiene": business_hygiene,
    }
    total = _weighted_total(breakdown)
    label, vibe = _band(total)

    # Highlights / Fixes (rule-of-thumb)
    # Pick top 2 highlights and top 2 fixes
    sorted_items = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
    top2 = sorted_items[:2]
    bottom2 = sorted_items[-2:]

    nice_names = {
        "pricing": "Pricing & CODB",
        "time_workflow": "Time & Workflow",
        "delivery_capacity": "Delivery & Capacity",
        "risk_resilience": "Risk & Resilience",
        "business_hygiene": "Business Hygiene",
    }

    for k, v in top2:
        if v >= 70:
            highlights.append(f"Strong **{nice_names[k]}** ({v}/100).")
        else:
            highlights.append(f"Best area right now: **{nice_names[k]}** ({v}/100).")

    for k, v in bottom2:
        if v < 55:
            fixes.append(f"Priority fix: **{nice_names[k]}** ({v}/100).")
        else:
            fixes.append(f"Opportunity: **{nice_names[k]}** ({v}/100).")

    # Extra tailored nudges
    if pricing < 60:
        fixes.append("Run the **Wedding CODB Calculator** and set a tax rate + take-home goal.")
    if risk_resilience < 60:
        fixes.append("Implement at least **two backups** + a simple contingency plan.")
    if delivery_capacity < 60:
        fixes.append("Add buffer blocks + protect a weekly recovery day to avoid backlog drift.")
    if time_workflow < 60:
        fixes.append("Batch editing into focused blocks (even 2x/week) to reduce context-switch cost.")

    # De-dupe while preserving order
    def dedupe(items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    return ScoreBreakdown(
        pricing=pricing,
        time_workflow=time_workflow,
        delivery_capacity=delivery_capacity,
        risk_resilience=risk_resilience,
        business_hygiene=business_hygiene,
        total=total,
        label=label,
        vibe=vibe,
        highlights=dedupe(highlights),
        fixes=dedupe(fixes)[:5],
    )


# -------------------------
# UI
# -------------------------
def render_wedding_photographer_score():
    st.title("🎯 What’s Your Wedding Photographer Score?")
    st.caption(
        "Just for fun but based on real sustainability signals (pricing, workflow, delivery, risk). "
        "No judgment, just data."
    )

    # --- Questions ---
    st.subheader("Answer honestly (this is for you)")

    # Progress (we’ll increment as we go)
    progress = 0
    total_steps = 10

    def bump():
        nonlocal progress
        progress += 1
        st.progress(progress / total_steps)

    st.progress(0.0)

    colL, colR = st.columns([1.0, 1.0], gap="large")

    with colL:
        st.markdown("### 💰 Pricing & Money")
        codb_known = st.radio(
            "Do you know your true cost per wedding (CODB)?",
            ["Yes, I've done a CODB calculation", "Rough idea", "Nope"],
            index=0,
            key="wps_codb_known",
        )
        bump()

        hourly_known = st.radio(
            "Do you know your effective hourly rate (after time + costs)?",
            ["Yes (I know my effective hourly rate)", "Kind of / I can estimate it", "No"],
            index=1,
            key="wps_hourly_known",
        )
        bump()

        tax_plan = st.radio(
            "Taxes: what's your plan?",
            ["I set aside taxes from every payment", "I set aside sometimes / when I remember", "I wing it (April surprise)"],
            index=1,
            key="wps_tax_plan",
        )
        bump()

        st.markdown("### ⏱ Time & Workflow")
        editing_hours_per_wedding = st.slider(
            "Roughly how many total editing hours per wedding?",
            min_value=0,
            max_value=60,
            value=18,
            help="Include culling, editing, export, upload, & delivery admin if you want it to be more honest.",
            key="wps_editing_hours_per_wedding",
        )
        bump()

        batching = st.radio(
            "Do you batch editing into focused blocks?",
            ["Yes, I batch editing in focused blocks", "Sometimes", "No, it's mostly squeezed in randomly"],
            index=1,
            key="wps_batching",
        )
        bump()

        outsourcing = st.radio(
            "Do you outsource anything (editing/admin)?",
            ["Yes (editing/admin help)", "Occasionally", "No"],
            index=2,
            key="wps_outsourcing",
        )
        bump()

        editing_system = st.radio(
            "How would you describe your editing/workflow system?",
            ["Strong system (presets, workflow, consistent steps)", "Some system, still evolving", "Chaos/depends on the job"],
            index=1,
            key="wps_editing_system",
        )
        bump()

    with colR:
        st.markdown("### 📆 Delivery & Capacity")
        turnaround = st.radio(
            "Are you delivering on time?",
            ["Always early or on time", "Usually on time (rarely late)", "Sometimes late", "Often late"],
            index=1,
            key="wps_turnaround",
        )
        bump()

        weddings_per_year = st.slider(
            "How many weddings do you typically take per year?",
            min_value=0,
            max_value=60,
            value=20,
            key="wps_weddings_per_year",
        )
        bump()

        boundaries = st.radio(
            "Do you protect recovery time?",
            ["Yes, I protect at least 1 day off weekly", "Sometimes", "Not really"],
            index=1,
            key="wps_boundaries",
        )

        buffering = st.radio(
            "Do you build buffers into timelines and delivery expectations?",
            ["Yes, I build buffers into timelines + delivery", "Sometimes", "No"],
            index=1,
            key="wps_buffering",
        )

        st.markdown("### ⚠️ Risk & Resilience")
        backups = st.radio(
            "Backups: what's your setup?",
            [
                "3-2-1 backup (local + cloud + offsite)",
                "Two copies (local + cloud OR local + external)",
                "One backup (or inconsistent)",
                "No real backup system",
            ],
            index=1,
            key="wps_backups",
        )

        gear_redundancy = st.radio(
            "Gear redundancy?",
            ["Yes (backup camera body + essentials)", "Partial (some redundancy)", "No"],
            index=1,
            key="wps_gear_redundancy",
        )

        sick_plan = st.radio(
            "If you're sick for a week in peak season…",
            ["Yes, I have a contingency plan", "Kind of (I could figure it out)", "No"],
            index=1,
            key="wps_sick_plan",
        )

        st.markdown("### 🧾 Business Hygiene")
        contracts = st.radio(
            "Contracts + scope boundaries?",
            ["Yes, contracts & clear scope", "Mostly (could be tighter)", "Not consistent", "No"],
            index=0,
            key="wps_contracts",
        )

        crm_system = st.radio(
            "Client workflow system (CRM/templates/process)?",
            ["Yes (CRM/templates/process)", "Some templates, not fully systemized", "Mostly manual each time"],
            index=1,
            key="wps_crm_system",
        )

        venue_notes = st.radio(
            "Do you keep venue/church notes (restrictions, best spots, rain plans)?",
            ["Yes, I keep venue/church notes", "Sometimes", "No"],
            index=1,
            key="wps_venue_notes",
        )

        client_expectations = st.radio(
            "Do you set clear expectations early (timeline + delivery + what's realistic)?",
            ["Very clear (timeline & delivery expectations set early)", "Usually clear", "Not consistent"],
            index=1,
            key="wps_client_expectations",
        )

    # --- Compute ---
    st.divider()

    answers = {
        "codb_known": codb_known,
        "hourly_known": hourly_known,
        "tax_plan": tax_plan,
        "editing_hours_per_wedding": editing_hours_per_wedding,
        "batching": batching,
        "outsourcing": outsourcing,
        "editing_system": editing_system,
        "turnaround": turnaround,
        "weddings_per_year": weddings_per_year,
        "boundaries": boundaries,
        "buffering": buffering,
        "backups": backups,
        "gear_redundancy": gear_redundancy,
        "sick_plan": sick_plan,
        "contracts": contracts,
        "crm_system": crm_system,
        "venue_notes": venue_notes,
        "client_expectations": client_expectations,
    }

    result = compute_score(answers)

    st.subheader("Your results")

    left, mid, right = st.columns([1.1, 1.0, 1.1], gap="large")
    with left:
        st.metric("Wedding Photographer Score", f"{result.total}/100")
        st.caption(f"**{result.label}** — {result.vibe}")

    with mid:
        # Make the breakdown feel “game-like”
        st.write("**Category breakdown**")
        df = pd.DataFrame(
            {
                "Category": [
                    "Pricing & CODB",
                    "Time & Workflow",
                    "Delivery & Capacity",
                    "Risk & Resilience",
                    "Business Hygiene",
                ],
                "Score": [
                    result.pricing,
                    result.time_workflow,
                    result.delivery_capacity,
                    result.risk_resilience,
                    result.business_hygiene,
                ],
            }
        )
        st.dataframe(df, hide_index=True, use_container_width=True)

    with right:
        st.write("**Strengths**")
        for h in result.highlights:
            st.write(f"✅ {h}")

        st.write("**Next fixes**")
        for f in result.fixes:
            st.write(f"🛠️ {f}")

    # Simple chart (Streamlit-native)
    st.bar_chart(
        df.set_index("Category")["Score"],
        use_container_width=True,
    )

    # Shareable summary
    st.subheader("Shareable summary (copy/paste)")
    share_text = (
        f"My Wedding Photographer Score: {result.total}/100 — {result.label}\n"
        f"Top strengths: {', '.join([h.replace('**','') for h in result.highlights[:2]])}\n"
        f"Next fixes: {', '.join([f.replace('**','') for f in result.fixes[:2]])}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d')}"
    )
    st.code(share_text, language="text")

    # Export
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "answers": answers,
        "result": asdict(result),
    }

    st.download_button(
        "Download results (JSON)",
        data=pd.Series(payload).to_json(indent=2),
        file_name="wedding_photographer_score.json",
        mime="application/json",
        use_container_width=True,
    )


# If you want to run this file directly for quick testing:
if __name__ == "__main__":
    st.set_page_config(page_title="What's Your Wedding Photographer Score?", layout="wide")
    render_wedding_photographer_score()