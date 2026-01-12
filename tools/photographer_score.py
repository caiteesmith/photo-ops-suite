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
# Stable option labels (single source of truth)
# -------------------------
CODB_OPTIONS = {
    "done": "Yes, I've done a CODB calculation",
    "rough": "Rough idea",
    "no": "Nope",
}

HOURLY_OPTIONS = {
    "yes": "Yes (I know my effective hourly rate)",
    "kindof": "Kind of / I can estimate it",
    "no": "No",
}

TAX_OPTIONS = {
    "always": "I set aside taxes from every payment",
    "sometimes": "I set aside sometimes / when I remember",
    "wing": "I wing it (April surprise)",
}

BATCHING_OPTIONS = {
    "yes": "Yes, I batch editing in focused blocks",
    "sometimes": "Sometimes",
    "no": "No, it's mostly squeezed in randomly",
}

OUTSOURCE_OPTIONS = {
    "yes": "Yes (editing/admin help)",
    "sometimes": "Occasionally",
    "no": "No",
}

EDIT_SYSTEM_OPTIONS = {
    "strong": "Strong system (presets, workflow, consistent steps)",
    "some": "Some system, still evolving",
    "chaos": "Chaos/depends on the job",
}

TURNAROUND_OPTIONS = {
    "ontime": "Always early or on time",
    "usually": "Usually on time (rarely late)",
    "sometimes": "Sometimes late",
    "often": "Often late",
}

BOUNDARIES_OPTIONS = {
    "yes": "Yes, I protect at least 1 day off weekly",
    "sometimes": "Sometimes",
    "no": "Not really",
}

BUFFER_OPTIONS = {
    "yes": "Yes, I build buffers into timelines + delivery",
    "sometimes": "Sometimes",
    "no": "No",
}

BACKUP_OPTIONS = {
    "321": "3-2-1 backup (local + cloud + offsite)",
    "two": "Two copies (local + cloud OR local + external)",
    "one": "One backup (or inconsistent)",
    "none": "No real backup system",
}

REDUNDANCY_OPTIONS = {
    "yes": "Yes (backup camera body + essentials)",
    "partial": "Partial (some redundancy)",
    "no": "No",
}

SICK_OPTIONS = {
    "yes": "Yes, I have a contingency plan",
    "kindof": "Kind of (I could figure it out)",
    "no": "No",
}

CONTRACT_OPTIONS = {
    "yes": "Yes, contracts & clear scope",
    "mostly": "Mostly (could be tighter)",
    "inconsistent": "Not consistent",
    "no": "No",
}

CRM_OPTIONS = {
    "yes": "Yes (CRM/templates/process)",
    "some": "Some templates, not fully systemized",
    "manual": "Mostly manual each time",
}

VENUE_OPTIONS = {
    "yes": "Yes, I keep venue/church notes",
    "sometimes": "Sometimes",
    "no": "No",
}

EXPECT_OPTIONS = {
    "very": "Very clear (timeline & delivery expectations set early)",
    "usually": "Usually clear",
    "not": "Not consistent",
}


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


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
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
            CODB_OPTIONS["done"]: 40,
            CODB_OPTIONS["rough"]: 20,
            CODB_OPTIONS["no"]: 0,
        },
    )

    pricing += _score_from_choice(
        str(answers["hourly_known"]),
        {
            HOURLY_OPTIONS["yes"]: 30,
            HOURLY_OPTIONS["kindof"]: 15,
            HOURLY_OPTIONS["no"]: 0,
        },
    )

    pricing += _score_from_choice(
        str(answers["tax_plan"]),
        {
            TAX_OPTIONS["always"]: 30,
            TAX_OPTIONS["sometimes"]: 15,
            TAX_OPTIONS["wing"]: 0,
        },
    )

    pricing = _clamp_0_100(pricing)

    # --- Time & workflow (0-100) ---
    time_workflow = 0

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
            BATCHING_OPTIONS["yes"]: 30,
            BATCHING_OPTIONS["sometimes"]: 15,
            BATCHING_OPTIONS["no"]: 0,
        },
    )

    time_workflow += _score_from_choice(
        str(answers["outsourcing"]),
        {
            OUTSOURCE_OPTIONS["yes"]: 25,
            OUTSOURCE_OPTIONS["sometimes"]: 12,
            OUTSOURCE_OPTIONS["no"]: 0,
        },
    )

    time_workflow += _score_from_choice(
        str(answers["editing_system"]),
        {
            EDIT_SYSTEM_OPTIONS["strong"]: 20,
            EDIT_SYSTEM_OPTIONS["some"]: 10,
            EDIT_SYSTEM_OPTIONS["chaos"]: 0,
        },
    )

    time_workflow = _clamp_0_100(time_workflow)

    # --- Delivery & capacity (0-100) ---
    delivery_capacity = 0

    delivery_capacity += _score_from_choice(
        str(answers["turnaround"]),
        {
            TURNAROUND_OPTIONS["ontime"]: 35,
            TURNAROUND_OPTIONS["usually"]: 25,
            TURNAROUND_OPTIONS["sometimes"]: 12,
            TURNAROUND_OPTIONS["often"]: 0,
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
            BOUNDARIES_OPTIONS["yes"]: 25,
            BOUNDARIES_OPTIONS["sometimes"]: 12,
            BOUNDARIES_OPTIONS["no"]: 0,
        },
    )

    delivery_capacity += _score_from_choice(
        str(answers["buffering"]),
        {
            BUFFER_OPTIONS["yes"]: 15,
            BUFFER_OPTIONS["sometimes"]: 8,
            BUFFER_OPTIONS["no"]: 0,
        },
    )

    delivery_capacity = _clamp_0_100(delivery_capacity)

    # --- Risk & resilience (0-100) ---
    risk_resilience = 0

    risk_resilience += _score_from_choice(
        str(answers["backups"]),
        {
            BACKUP_OPTIONS["321"]: 45,
            BACKUP_OPTIONS["two"]: 30,
            BACKUP_OPTIONS["one"]: 10,
            BACKUP_OPTIONS["none"]: 0,
        },
    )

    risk_resilience += _score_from_choice(
        str(answers["gear_redundancy"]),
        {
            REDUNDANCY_OPTIONS["yes"]: 30,
            REDUNDANCY_OPTIONS["partial"]: 15,
            REDUNDANCY_OPTIONS["no"]: 0,
        },
    )

    risk_resilience += _score_from_choice(
        str(answers["sick_plan"]),
        {
            SICK_OPTIONS["yes"]: 25,
            SICK_OPTIONS["kindof"]: 12,
            SICK_OPTIONS["no"]: 0,
        },
    )

    risk_resilience = _clamp_0_100(risk_resilience)

    # --- Business hygiene (0-100) ---
    business_hygiene = 0

    business_hygiene += _score_from_choice(
        str(answers["contracts"]),
        {
            CONTRACT_OPTIONS["yes"]: 35,
            CONTRACT_OPTIONS["mostly"]: 20,
            CONTRACT_OPTIONS["inconsistent"]: 8,
            CONTRACT_OPTIONS["no"]: 0,
        },
    )

    business_hygiene += _score_from_choice(
        str(answers["crm_system"]),
        {
            CRM_OPTIONS["yes"]: 30,
            CRM_OPTIONS["some"]: 15,
            CRM_OPTIONS["manual"]: 0,
        },
    )

    business_hygiene += _score_from_choice(
        str(answers["venue_notes"]),
        {
            VENUE_OPTIONS["yes"]: 20,
            VENUE_OPTIONS["sometimes"]: 10,
            VENUE_OPTIONS["no"]: 0,
        },
    )

    business_hygiene += _score_from_choice(
        str(answers["client_expectations"]),
        {
            EXPECT_OPTIONS["very"]: 15,
            EXPECT_OPTIONS["usually"]: 8,
            EXPECT_OPTIONS["not"]: 0,
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

    nice_names = {
        "pricing": "Pricing & CODB",
        "time_workflow": "Time & Workflow",
        "delivery_capacity": "Delivery & Capacity",
        "risk_resilience": "Risk & Resilience",
        "business_hygiene": "Business Hygiene",
    }

    sorted_items = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
    top2 = sorted_items[:2]
    bottom2 = sorted_items[-2:]

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

    return ScoreBreakdown(
        pricing=pricing,
        time_workflow=time_workflow,
        delivery_capacity=delivery_capacity,
        risk_resilience=risk_resilience,
        business_hygiene=business_hygiene,
        total=total,
        label=label,
        vibe=vibe,
        highlights=_dedupe(highlights),
        fixes=_dedupe(fixes)[:5],
    )


# -------------------------
# UI
# -------------------------
def render_wedding_photographer_score():
    st.title("🎯 What's Your Wedding Photographer Score?")
    st.caption(
        "Just for fun but based on real sustainability signals (pricing, workflow, delivery, risk). "
        "No judgment, just data."
    )

    st.subheader("Answer honestly (this is for you)")

    colL, colR = st.columns([1.0, 1.0], gap="large")

    with colL:
        st.markdown("### 💰 Pricing & Money")
        codb_known = st.radio(
            "Do you know your true cost per wedding (CODB)?",
            list(CODB_OPTIONS.values()),
            index=0,
            key="wps_codb_known",
        )

        hourly_known = st.radio(
            "Do you know your effective hourly rate (after time + costs)?",
            list(HOURLY_OPTIONS.values()),
            index=1,
            key="wps_hourly_known",
        )

        tax_plan = st.radio(
            "Taxes: what's your plan?",
            list(TAX_OPTIONS.values()),
            index=1,
            key="wps_tax_plan",
        )

        st.markdown("### ⏱ Time & Workflow")
        editing_hours_per_wedding = st.slider(
            "Roughly how many total editing hours per wedding?",
            min_value=0,
            max_value=60,
            value=18,
            help="Include culling, editing, export, upload, & delivery admin if you want it to be more honest.",
            key="wps_editing_hours_per_wedding",
        )

        batching = st.radio(
            "Do you batch editing into focused blocks?",
            list(BATCHING_OPTIONS.values()),
            index=1,
            key="wps_batching",
        )

        outsourcing = st.radio(
            "Do you outsource anything (editing/admin)?",
            list(OUTSOURCE_OPTIONS.values()),
            index=2,
            key="wps_outsourcing",
        )

        editing_system = st.radio(
            "How would you describe your editing/workflow system?",
            list(EDIT_SYSTEM_OPTIONS.values()),
            index=1,
            key="wps_editing_system",
        )

    with colR:
        st.markdown("### 📆 Delivery & Capacity")
        turnaround = st.radio(
            "Are you delivering on time?",
            list(TURNAROUND_OPTIONS.values()),
            index=1,
            key="wps_turnaround",
        )

        weddings_per_year = st.slider(
            "How many weddings do you typically take per year?",
            min_value=0,
            max_value=60,
            value=20,
            key="wps_weddings_per_year",
        )

        boundaries = st.radio(
            "Do you protect recovery time?",
            list(BOUNDARIES_OPTIONS.values()),
            index=1,
            key="wps_boundaries",
        )

        buffering = st.radio(
            "Do you build buffers into timelines and delivery expectations?",
            list(BUFFER_OPTIONS.values()),
            index=1,
            key="wps_buffering",
        )

        st.markdown("### ⚠️ Risk & Resilience")
        backups = st.radio(
            "Backups: what's your setup?",
            list(BACKUP_OPTIONS.values()),
            index=1,
            key="wps_backups",
        )

        gear_redundancy = st.radio(
            "Gear redundancy?",
            list(REDUNDANCY_OPTIONS.values()),
            index=1,
            key="wps_gear_redundancy",
        )

        sick_plan = st.radio(
            "If you're sick for a week in peak season…",
            list(SICK_OPTIONS.values()),
            index=1,
            key="wps_sick_plan",
        )

        st.markdown("### 🧾 Business Hygiene")
        contracts = st.radio(
            "Contracts + scope boundaries?",
            list(CONTRACT_OPTIONS.values()),
            index=0,
            key="wps_contracts",
        )

        crm_system = st.radio(
            "Client workflow system (CRM/templates/process)?",
            list(CRM_OPTIONS.values()),
            index=1,
            key="wps_crm_system",
        )

        venue_notes = st.radio(
            "Do you keep venue/church notes (restrictions, best spots, rain plans)?",
            list(VENUE_OPTIONS.values()),
            index=1,
            key="wps_venue_notes",
        )

        client_expectations = st.radio(
            "Do you set clear expectations early (timeline + delivery + what's realistic)?",
            list(EXPECT_OPTIONS.values()),
            index=1,
            key="wps_client_expectations",
        )

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

    st.bar_chart(df.set_index("Category")["Score"], use_container_width=True)

    st.subheader("Shareable summary (copy/paste)")
    share_text = (
        f"My Wedding Photographer Score: {result.total}/100 — {result.label}\n"
        f"Top strengths: {', '.join([h.replace('**', '') for h in result.highlights[:2]])}\n"
        f"Next fixes: {', '.join([f.replace('**', '') for f in result.fixes[:2]])}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d')}"
    )
    st.code(share_text, language="text")

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


if __name__ == "__main__":
    st.set_page_config(page_title="What's Your Wedding Photographer Score?", layout="wide")
    render_wedding_photographer_score()