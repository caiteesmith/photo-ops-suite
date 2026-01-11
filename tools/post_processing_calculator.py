import streamlit as st

from math import ceil

def render_post_processing_calculator():
    st.subheader("🧠 Post-Processing Calculator")

    st.markdown(
        """
        Estimate your total post-wedding workload based on **photos captured**, **photos delivered**, and your average pace.
        This includes **culling**, **editing**, and a little overhead for **ingest/export/upload**.
        """
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        captured = st.number_input("Photos captured (total)", min_value=0, value=3000, step=50)
        delivered_mode = st.selectbox("Delivered photos input", ["Enter delivered count", "Estimate delivered %"], index=0)

        if delivered_mode == "Enter delivered count":
            delivered = st.number_input("Photos delivered (final)", min_value=0, value=700, step=25)
            delivered_pct = None
        else:
            delivered_pct = st.slider("Delivered % of captured", 5, 60, 25, 1)
            delivered = int(round(captured * (delivered_pct / 100.0)))

        if captured and delivered > captured:
            st.warning("Delivered is greater than captured — double check inputs.")

    with col2:
        cull_rate = st.number_input("Culling speed (photos per hour)", min_value=50, value=800, step=50)
        edit_seconds = st.number_input("Avg edit time per delivered photo (seconds)", min_value=1, value=35, step=1)
        weekly_hours = st.number_input("Editing hours available per week", min_value=1.0, value=8.0, step=1.0)

    st.divider()
    st.markdown("### Overhead")
    ingest_backup_min = st.slider("Ingest + backup (minutes)", 0, 180, 35, 5)
    export_upload_min = st.slider("Export + upload (minutes)", 0, 240, 45, 5)

    cull_hours = (captured / cull_rate) if cull_rate else 0.0
    edit_hours = (delivered * edit_seconds) / 3600.0
    overhead_hours = (ingest_backup_min + export_upload_min) / 60.0

    total_hours = cull_hours + edit_hours + overhead_hours
    weeks = (total_hours / weekly_hours) if weekly_hours else 0.0

    st.subheader("Results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cull time", f"{cull_hours:.1f} hrs")
    m2.metric("Edit time", f"{edit_hours:.1f} hrs")
    m3.metric("Overhead", f"{overhead_hours:.1f} hrs")
    m4.metric("Total", f"{total_hours:.1f} hrs")

    st.divider()
    st.markdown("### Delivery Pace")
    st.write(f"Estimated delivered photos: **{delivered:,}**" + (f" (**{delivered_pct}%**) " if delivered_pct else ""))
    st.write(f"At **{weekly_hours:.1f} hrs/week**, this is about **{weeks:.1f} weeks** (~**{ceil(weeks)} weeks** with buffer).")

    with st.expander("What-if scenarios", expanded=False):
        for mult, label in [(0.75, "Faster"), (1.0, "Baseline"), (1.25, "Slower")]:
            scenario_edit_seconds = edit_seconds * mult
            scenario_edit_hours = (delivered * scenario_edit_seconds) / 3600.0
            scenario_total = cull_hours + scenario_edit_hours + overhead_hours
            scenario_weeks = (scenario_total / weekly_hours) if weekly_hours else 0.0
            st.write(f"**{label}:** {scenario_total:.1f} hrs → {scenario_weeks:.1f} weeks (edit {scenario_edit_seconds:.0f}s/photo)")