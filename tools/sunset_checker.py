# =========================
# file: tools/sunset_checker.py
# =========================
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


# -------------------------
# Helpers
# -------------------------
@dataclass
class GeoCandidate:
    label: str
    lat: float
    lon: float
    elevation_m: Optional[float] = None
    timezone: Optional[str] = None
    source: str = "geocoding"


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _parse_date_yyyy_mm_dd(raw: str) -> date:
    return datetime.strptime(raw.strip(), "%Y-%m-%d").date()


def _parse_12h_time(raw: str) -> Optional[datetime]:
    """
    Parses times like: '7:06:58 AM' from SunriseSunset.io
    Returns a datetime with today's date (caller will replace date anyway).
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%I:%M:%S %p", "%I:%M %p"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def _fmt_time(dt: Optional[datetime]) -> str:
    if not dt:
        return "—"
    # Cross-platform: avoid %-I on Windows by doing manual strip
    return dt.strftime("%I:%M %p").lstrip("0")


def _add_minutes(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=int(minutes))


def _build_dt(on_date: date, t: datetime) -> datetime:
    """
    SunriseSunset.io returns times only; we attach the selected date.
    """
    return datetime(
        year=on_date.year,
        month=on_date.month,
        day=on_date.day,
        hour=t.hour,
        minute=t.minute,
        second=t.second,
    )


# -------------------------
# Geocoding (Address -> Lat/Lon)
# -------------------------
@st.cache_data(show_spinner=False, ttl=60 * 60)  # cache results for 1 hour
def _geocode_open_meteo(query: str, limit: int = 8) -> List[GeoCandidate]:
    """
    Open-Meteo geocoding is fast and gives timezone + elevation for many results.
    Great for city / venue names, sometimes weaker on full street addresses.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": query,
        "count": limit,
        "language": "en",
        "format": "json",
    }

    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    results = data.get("results") or []
    candidates: List[GeoCandidate] = []

    for item in results:
        lat = _safe_float(item.get("latitude"))
        lon = _safe_float(item.get("longitude"))
        if lat is None or lon is None:
            continue

        name = (item.get("name") or "").strip()
        admin1 = (item.get("admin1") or "").strip()
        admin2 = (item.get("admin2") or "").strip()
        country = (item.get("country") or "").strip()
        tz = (item.get("timezone") or "").strip() or None
        elev = _safe_float(item.get("elevation"))

        parts = [p for p in [name, admin2, admin1, country] if p]
        label = " • ".join(parts) if parts else f"{lat:.5f}, {lon:.5f}"

        candidates.append(
            GeoCandidate(
                label=label,
                lat=float(lat),
                lon=float(lon),
                elevation_m=elev,
                timezone=tz,
                source="open-meteo",
            )
        )

    return candidates


@st.cache_data(show_spinner=False, ttl=60 * 60)  # cache results for 1 hour
def _geocode_nominatim(query: str, limit: int = 8) -> List[GeoCandidate]:
    """
    Fallback: Nominatim (OpenStreetMap) tends to be better for full street addresses.
    Note: doesn't reliably return elevation/timezone.

    IMPORTANT: Nominatim is rate-limited. This app intentionally searches only when the user
    clicks Search (not on every keystroke) to reduce failures.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": limit,
        "addressdetails": 1,
    }
    headers = {
        # A descriptive UA helps avoid blocks. If you have a real contact email, include it.
        "User-Agent": "PhotoOpsSuite/1.0 (Streamlit app; geocoding)",
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    candidates: List[GeoCandidate] = []
    for item in data:
        lat = _safe_float(item.get("lat"))
        lon = _safe_float(item.get("lon"))
        if lat is None or lon is None:
            continue

        label = (item.get("display_name") or "").strip()
        if not label:
            label = f"{lat:.5f}, {lon:.5f}"

        candidates.append(
            GeoCandidate(
                label=label,
                lat=float(lat),
                lon=float(lon),
                elevation_m=None,
                timezone=None,
                source="nominatim",
            )
        )

    return candidates


def geocode_location(query: str) -> List[GeoCandidate]:
    """
    Two-pass approach:
      1) Open-Meteo (great for place names + gives timezone/elevation)
      2) Nominatim fallback (better for full addresses)
    """
    query = (query or "").strip()
    if not query:
        return []

    # Try the exact query first
    candidates = _geocode_open_meteo(query)

    # If nothing, try a slightly simplified query (sometimes commas confuse results)
    if not candidates and "," in query:
        simplified = " ".join([p.strip() for p in query.split(",") if p.strip()])
        candidates = _geocode_open_meteo(simplified)

    # Fallback to Nominatim for street-level searches
    if not candidates:
        candidates = _geocode_nominatim(query)

    return candidates


# -------------------------
# Sunrise/Sunset + Twilight
# -------------------------
def fetch_sun_times(lat: float, lon: float, on_date: date, timezone: Optional[str] = None) -> Dict[str, Any]:
    """
    Uses SunriseSunset.io (free) to get sunrise/sunset + dawn/dusk.
    """
    url = "https://api.sunrisesunset.io/json"
    params = {
        "lat": lat,
        "lng": lon,
        "date": on_date.isoformat(),
    }
    if timezone:
        params["timezone"] = timezone

    r = requests.get(url, params=params, timeout=12)
    r.raise_for_status()
    data = r.json()

    if (data or {}).get("status") != "OK":
        raise RuntimeError(f"SunriseSunset.io error: {data}")

    return data.get("results") or {}


def compute_windows(results: Dict[str, Any], on_date: date, golden_minutes_am: int, golden_minutes_pm: int) -> Dict[str, Any]:
    """
    Builds the key photo windows:
      - Sunset time
      - Golden hour (AM + PM)
      - Blue hour (AM + PM)

    Definitions used:
      - Blue hour AM: dawn -> sunrise
      - Blue hour PM: sunset -> dusk
      - Golden hour AM: sunrise -> sunrise + golden_minutes_am
      - Golden hour PM: sunset - golden_minutes_pm -> sunset

    Note: We intentionally compute golden hour lengths based on your sliders (minutes),
    rather than relying on any provider-specific "golden hour start" definition.
    """
    sunrise_t = _parse_12h_time(results.get("sunrise"))
    sunset_t = _parse_12h_time(results.get("sunset"))
    dawn_t = _parse_12h_time(results.get("dawn"))   # civil twilight begin
    dusk_t = _parse_12h_time(results.get("dusk"))   # civil twilight end

    sunrise = _build_dt(on_date, sunrise_t) if sunrise_t else None
    sunset = _build_dt(on_date, sunset_t) if sunset_t else None
    dawn = _build_dt(on_date, dawn_t) if dawn_t else None
    dusk = _build_dt(on_date, dusk_t) if dusk_t else None

    # Blue hour windows
    blue_am = (dawn, sunrise) if dawn and sunrise else (None, None)
    blue_pm = (sunset, dusk) if sunset and dusk else (None, None)

    # Golden hour windows (based on your chosen minutes)
    golden_am = (sunrise, _add_minutes(sunrise, golden_minutes_am)) if sunrise else (None, None)
    golden_pm = (_add_minutes(sunset, -golden_minutes_pm), sunset) if sunset else (None, None)

    return {
        "sunrise": sunrise,
        "sunset": sunset,
        "dawn": dawn,
        "dusk": dusk,
        "golden_am": golden_am,
        "golden_pm": golden_pm,
        "blue_am": blue_am,
        "blue_pm": blue_pm,
        "timezone": results.get("timezone"),
        "utc_offset": results.get("utc_offset"),
        "day_length": results.get("day_length"),
        "first_light": results.get("first_light"),
        "last_light": results.get("last_light"),
        "solar_noon": results.get("solar_noon"),
    }


# -------------------------
# UI
# -------------------------
def render_sunset_checker():
    st.subheader("🌅 Sunset, Golden Hour, and Blue Hour Checker")

    st.markdown(
        """
This tool helps you plan portrait timing **fast**:
- **Sunset** (the anchor)
- **Golden hour** (best light for portraits)
- **Blue hour** (the dreamy post-sunset glow)

It supports **searching by address/venue name** *or* entering **lat/lon** directly.
"""
    )

    with st.expander("Altitude note (why it matters)", expanded=False):
        st.markdown(
            """
**Altitude can shift these times slightly** because the sun becomes visible earlier (and sets later)
when you’re higher above sea level.

- Most public APIs return times using standard astronomical models and local conditions (and often assume sea-level).
- In practice, altitude usually changes sunrise/sunset by **seconds to a couple minutes**, but it can matter
  in mountainous locations or when you’re cutting it close.

**What this app does:**  
If we can detect elevation from geocoding (Open-Meteo), we’ll display it.  
It’s mainly a planning reference — not required for the calculation.
"""
        )

    # ✅ FIX: define hints BEFORE any widget uses them (prevents UnboundLocalError on reruns)
    if "tz_hint" not in st.session_state:
        st.session_state["tz_hint"] = ""
    if "last_candidates" not in st.session_state:
        st.session_state["last_candidates"] = []
    if "last_query" not in st.session_state:
        st.session_state["last_query"] = ""

    tz_hint: str = st.session_state.get("tz_hint", "") or ""

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Date & Settings")
        wedding_date = st.text_input("Date (YYYY-MM-DD)", value=date.today().isoformat())

        timezone_override = st.text_input(
            "Timezone (optional)",
            value=tz_hint,
            placeholder="e.g., America/New_York (leave blank to auto-detect)",
            help="If left blank, the API will infer local time. If you want to force a timezone, enter an IANA name like America/New_York.",
        )

        st.markdown("### Location")
        mode = st.radio(
            "How do you want to set the location?",
            ["Search by address / venue", "Enter lat/lon manually"],
            index=0,
            horizontal=True,
        )

        location_label: Optional[str] = None
        lat: Optional[float] = None
        lon: Optional[float] = None
        elevation_m: Optional[float] = None

        if mode == "Search by address / venue":
            query = st.text_input(
                "Search",
                value=st.session_state.get("last_query", ""),
                placeholder="Try: 'Franklin Plaza, NJ' or '123 Main St, Morristown, NJ'",
                help="If street-level searches fail, try adding city/state, or search the venue name + town.",
            )

            # Search button (prevents constant rate-limit failures & the annoying 'Couldn't find' while typing)
            do_search = st.button("Search location")

            candidates: List[GeoCandidate] = st.session_state.get("last_candidates", [])

            if do_search:
                q = (query or "").strip()
                st.session_state["last_query"] = q

                if len(q) < 3:
                    candidates = []
                    st.session_state["last_candidates"] = []
                else:
                    with st.spinner("Searching..."):
                        candidates = geocode_location(q)
                    st.session_state["last_candidates"] = candidates

            if st.session_state.get("last_query") and do_search and not candidates:
                st.error("Couldn't find that location. Try adding city/state, ZIP, or a more complete address.")

            if candidates:
                choice = st.selectbox(
                    "Choose the best match",
                    options=list(range(len(candidates))),
                    format_func=lambda i: f"{candidates[i].label}  ({candidates[i].source})",
                )
                picked = candidates[int(choice)]
                lat, lon = picked.lat, picked.lon
                elevation_m = picked.elevation_m
                location_label = picked.label

                # ✅ If we got a timezone from Open-Meteo, use it as a helpful default
                if picked.timezone:
                    st.session_state["tz_hint"] = picked.timezone

                # Show picked details
                st.caption(f"Picked: {location_label}")
                st.caption(f"Lat/Lon: {lat:.5f}, {lon:.5f}")
                if elevation_m is not None:
                    ft = float(elevation_m) * 3.28084
                    st.caption(f"Elevation (from geocoder): {float(elevation_m):.0f} m ({ft:.0f} ft)")
                if picked.timezone:
                    st.caption(f"Timezone hint: {picked.timezone}")

        else:
            lat = float(st.number_input("Latitude", value=40.7128, format="%.6f"))
            lon = float(st.number_input("Longitude", value=-74.0060, format="%.6f"))
            elevation_m = float(st.number_input("Altitude (meters) (optional)", value=0.0, step=10.0))
            location_label = f"{lat:.5f}, {lon:.5f}"

        st.markdown("### Golden hour settings")
        golden_minutes_am = st.slider(
            "Morning golden hour length (minutes)",
            min_value=10,
            max_value=120,
            value=60,
            step=5,
        )
        golden_minutes_pm = st.slider(
            "Evening golden hour length (minutes)",
            min_value=10,
            max_value=120,
            value=60,
            step=5,
        )

    with col2:
        st.markdown("### Results")

        if lat is None or lon is None:
            st.info("Enter a location to see results.")
            return

        try:
            on_date = _parse_date_yyyy_mm_dd(wedding_date)
        except Exception:
            st.error("Please use a date like 2026-06-20.")
            return

        try:
            tz = timezone_override.strip() or None

            with st.spinner("Fetching sun times..."):
                results = fetch_sun_times(float(lat), float(lon), on_date, timezone=tz)

            windows = compute_windows(
                results,
                on_date,
                golden_minutes_am=int(golden_minutes_am),
                golden_minutes_pm=int(golden_minutes_pm),
            )

            # --- PROMINENT SUMMARY (no columns; no truncation) ---
            sunset = windows["sunset"]
            golden_pm_start, golden_pm_end = windows["golden_pm"]
            blue_pm_start, blue_pm_end = windows["blue_pm"]

            st.markdown("## 🧭 Quick Plan")

            st.markdown(
                f"""
<div style="padding: 14px 16px; border: 1px solid #E6E9ED; border-radius: 16px; background: #F8F9FA;">
  <div style="font-size: 13px; opacity: 0.7; margin-bottom: 6px;">Sunset</div>
  <div style="font-size: 28px; font-weight: 700;">{_fmt_time(sunset)}</div>
</div>

<div style="padding: 14px 16px; border: 1px solid #E6E9ED; border-radius: 16px; background: #F8F9FA; margin-top: 10px;">
  <div style="font-size: 13px; opacity: 0.7; margin-bottom: 6px;">Golden hour (PM)</div>
  <div style="font-size: 24px; font-weight: 700;">{_fmt_time(golden_pm_start)}–{_fmt_time(golden_pm_end)}</div>
  <div style="font-size: 12px; opacity: 0.65; margin-top: 6px;">(using your slider: {int(golden_minutes_pm)} min before sunset)</div>
</div>

<div style="padding: 14px 16px; border: 1px solid #E6E9ED; border-radius: 16px; background: #F8F9FA; margin-top: 10px;">
  <div style="font-size: 13px; opacity: 0.7; margin-bottom: 6px;">Blue hour (PM)</div>
  <div style="font-size: 24px; font-weight: 700;">{_fmt_time(blue_pm_start)}–{_fmt_time(blue_pm_end)}</div>
</div>
""",
                unsafe_allow_html=True,
            )

            st.caption(f"Location: {location_label or f'{lat:.5f}, {lon:.5f}'}")
            tz_display = windows.get("timezone") or (timezone_override.strip() if timezone_override.strip() else None)
            if tz_display:
                st.caption(f"Timezone: {tz_display}")

            if elevation_m is not None:
                ft = float(elevation_m) * 3.28084
                st.caption(f"Approx. altitude: {float(elevation_m):.0f} m ({ft:.0f} ft)")

            st.divider()

            # --- FULL DETAIL ---
            st.markdown("### All windows")

            sunrise = windows["sunrise"]
            golden_am_start, golden_am_end = windows["golden_am"]
            blue_am_start, blue_am_end = windows["blue_am"]
            dawn = windows["dawn"]
            dusk = windows["dusk"]

            r1, r2 = st.columns(2)
            with r1:
                st.markdown("**Evening**")
                st.write(f"- **Golden hour:** {_fmt_time(golden_pm_start)}–{_fmt_time(golden_pm_end)}")
                st.write(f"- **Sunset:** {_fmt_time(sunset)}")
                st.write(f"- **Dusk:** {_fmt_time(dusk)}")
                st.write(f"- **Blue hour:** {_fmt_time(blue_pm_start)}–{_fmt_time(blue_pm_end)}")
                st.write(f"- **Last light:** {results.get('last_light') or '—'}")

            with r2:
                st.markdown("**Morning**")
                st.write(f"- **First light:** {results.get('first_light') or '—'}")
                st.write(f"- **Dawn:** {_fmt_time(dawn)}")
                st.write(f"- **Sunrise:** {_fmt_time(sunrise)}")
                st.write(f"- **Golden hour:** {_fmt_time(golden_am_start)}–{_fmt_time(golden_am_end)}")
                st.write(f"- **Blue hour:** {_fmt_time(blue_am_start)}–{_fmt_time(blue_am_end)}")

            with st.expander("More details", expanded=False):
                st.write(f"**Solar noon:** {windows.get('solar_noon') or '—'}")
                st.write(f"**Day length:** {windows.get('day_length') or '—'}")
                st.write(f"**UTC offset (mins):** {windows.get('utc_offset') if windows.get('utc_offset') is not None else '—'}")

            st.map([{"lat": float(lat), "lon": float(lon)}], zoom=10)

        except requests.HTTPError as e:
            st.error(f"Network/API error: {e}")
            st.info("If searching by address keeps failing, try again in a moment (geocoders can rate-limit) or enter lat/lon directly.")
        except Exception as e:
            st.error(f"Couldn't calculate times: {e}")
            st.info("Tip: Try a different search wording (venue + city/state) or enter lat/lon directly.")