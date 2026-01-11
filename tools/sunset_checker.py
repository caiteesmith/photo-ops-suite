from __future__ import annotations

from dataclasses import dataclass
from datetime import date as dt_date, datetime
from zoneinfo import ZoneInfo

import streamlit as st
from astral import LocationInfo
from astral.sun import sun
from astral import sun as astral_sun
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

_tf = TimezoneFinder()

_geolocator = Nominatim(user_agent="photo-ops-suite/1.0 (sunset-checker)")
_geocode = RateLimiter(_geolocator.geocode, min_delay_seconds=1.0)

def _tz_from_latlon(lat: float, lon: float) -> str:
    tz = _tf.timezone_at(lat=lat, lng=lon)
    return tz or "UTC"

@st.cache_data(show_spinner=False)
def geocode_address(query: str) -> tuple[float, float, str]:
    """
    Returns (lat, lon, display_name).
    Cached to avoid repeated calls.
    """
    q = (query or "").strip()
    if not q:
        raise ValueError("Please enter a location.")

    loc = _geocode(q)
    if loc is None:
        raise ValueError("Couldn't find that location. Try adding city/state or a full address.")

    return float(loc.latitude), float(loc.longitude), str(loc.address)


def _time_at_altitude(loc: LocationInfo, target_altitude_deg: float, day: dt_date, is_rising: bool) -> datetime:
    observer = loc.observer
    tzinfo = ZoneInfo(loc.timezone)

    try:
        return astral_sun.time_at_elevation(observer, target_altitude_deg, day, tzinfo=tzinfo, rising=is_rising)
    except TypeError:
        direction = astral_sun.SunDirection.RISING if is_rising else astral_sun.SunDirection.SETTING
        return astral_sun.time_at_elevation(observer, target_altitude_deg, day, tzinfo=tzinfo, direction=direction)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


@dataclass(frozen=True)
class SunsetResults:
    timezone: str
    sunrise: datetime
    solar_noon: datetime
    sunset: datetime
    golden_start: datetime
    golden_end: datetime
    blue_start: datetime
    blue_end: datetime


def calculate_sunset_windows(
    day: dt_date,
    lat: float,
    lon: float,
    golden_low_deg: float = -4.0,
    golden_high_deg: float = 6.0,
    blue_low_deg: float = -6.0,
    blue_high_deg: float = -4.0,
) -> SunsetResults:
    tz_name = _tz_from_latlon(lat, lon)
    loc = LocationInfo(name="Wedding Location", region="Custom", timezone=tz_name, latitude=lat, longitude=lon)

    s = sun(loc.observer, date=day, tzinfo=ZoneInfo(tz_name))
    sunrise = s["sunrise"]
    solar_noon = s["noon"]
    sunset = s["sunset"]

    golden_start = _time_at_altitude(loc, golden_high_deg, day, is_rising=False)
    golden_end = _time_at_altitude(loc, golden_low_deg, day, is_rising=False)
    blue_start = _time_at_altitude(loc, blue_high_deg, day, is_rising=False)
    blue_end = _time_at_altitude(loc, blue_low_deg, day, is_rising=False)

    return SunsetResults(
        timezone=tz_name,
        sunrise=sunrise,
        solar_noon=solar_noon,
        sunset=sunset,
        golden_start=golden_start,
        golden_end=golden_end,
        blue_start=blue_start,
        blue_end=blue_end,
    )

def render_sunset_checker() -> None:
    st.subheader("🌅 Sunset & Golden Hour Checker")

    st.markdown(
        """
        Look up sunset, golden hour, and blue hour for a wedding location.
        You can search by city/state or enter lat/lon directly.
        """
    )

    day = st.date_input("Date", value=dt_date.today())

    mode = st.radio("Location input", ["Search by address / venue", "Enter lat/lon"], horizontal=True)

    lat = lon = None
    display_name = None

    if mode == "Search by address / venue":
        query = st.text_input(
            "Search location",
            placeholder="e.g., Saratoga Springs, NY",
        )

        colA, colB = st.columns([1, 1])
        with colA:
            if st.button("Find location", type="primary", use_container_width=True):
                try:
                    lat, lon, display_name = geocode_address(query)
                    st.session_state["sunset_lat"] = lat
                    st.session_state["sunset_lon"] = lon
                    st.session_state["sunset_display"] = display_name
                except Exception as e:
                    st.error(str(e))

        lat = st.session_state.get("sunset_lat", lat)
        lon = st.session_state.get("sunset_lon", lon)
        display_name = st.session_state.get("sunset_display", display_name)

        if lat is not None and lon is not None:
            st.success(f"Using: {display_name}")
            st.caption(f"Lat/Lon: {lat:.6f}, {lon:.6f}")

    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            lat = st.number_input("Latitude", value=40.735657, format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=-74.172367, format="%.6f")

    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        golden_low = st.slider("Golden hour low altitude (°)", -10.0, 5.0, -4.0, 0.5)
        golden_high = st.slider("Golden hour high altitude (°)", 0.0, 15.0, 6.0, 0.5)
    with col2:
        blue_low = st.slider("Blue hour low altitude (°)", -12.0, -3.0, -6.0, 0.5)
        blue_high = st.slider("Blue hour high altitude (°)", -8.0, 0.0, -4.0, 0.5)

    if lat is None or lon is None:
        st.info("Enter a location above to calculate sunset windows.")
        return

    try:
        results = calculate_sunset_windows(
            day=day,
            lat=float(lat),
            lon=float(lon),
            golden_low_deg=float(golden_low),
            golden_high_deg=float(golden_high),
            blue_low_deg=float(blue_low),
            blue_high_deg=float(blue_high),
        )
    except Exception as e:
        st.error(f"Couldn't calculate sunset windows: {e}")
        return

    a, b = st.columns(2)
    with a:
        st.markdown("### ✨ Golden Hour")
        st.write(f"**Start:** {_fmt(results.golden_start)}")
        st.write(f"**End:** {_fmt(results.golden_end)}")
    with b:
        st.markdown("### 🌌 Blue Hour")
        st.write(f"**Start:** {_fmt(results.blue_start)}")
        st.write(f"**End:** {_fmt(results.blue_end)}")

    st.divider()

    st.write(f"**Timezone:** {results.timezone}")
    m1, m2, m3 = st.columns(3)
    m1.metric("Sunrise", _fmt(results.sunrise))
    m2.metric("Solar Noon", _fmt(results.solar_noon))
    m3.metric("Sunset", _fmt(results.sunset))