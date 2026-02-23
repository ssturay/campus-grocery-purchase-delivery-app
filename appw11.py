# ================================
# CamPDApp – Geolocation Logic
# ================================

import streamlit as st
from opencage.geocoder import OpenCageGeocode

# 🔐 Your OpenCage API key
OPENCAGE_KEY = "YOUR_API_KEY"
geocoder = OpenCageGeocode(OPENCAGE_KEY)

# ================================
# 1. Campus Coordinates Dictionary
# ================================
campus_coordinates = {
    "FBC": (8.4840, -13.2317),        # Fourah Bay College
    "IPAM": (8.4875, -13.2344),
    "COMAHS": (8.4655, -13.2689),
    "Njala FT": (8.3780, -13.1665),
    "MMTU": (8.4806, -13.2586),
    "Limkokwing": (8.3942, -13.1510),
    "UNIMTECH": (8.4683, -13.2517),
    "IAMTECH": (8.4752, -13.2498),
    "FTC": (8.4870, -13.2350),
    "LICCSAL": (8.4824, -13.2331),
    "IMAT": (8.4872, -13.2340),
    "Bluecrest": (8.4890, -13.2320),
    "UNIMAK": (8.4660, -13.2675),
    "EBKUST": (8.4700, -13.2600)
}

# ================================
# 2. Shopper Base Coordinates
# ================================
shopper_base_coordinates = {
    "Lumley": (8.4800, -13.2890),
    "Aberdeen": (8.4900, -13.2830),
    "Congo Cross": (8.4833, -13.2500),
    "Upgun": (8.5060, -13.2600),
    "East End": (8.4700, -13.2000)
}

# ================================
# 3. Robust Geocoding Function
# ================================
def geocode_location(location_name):
    if not location_name or location_name.strip() == "":
        return None, None

    try:
        results = geocoder.geocode(location_name + ", Sierra Leone", limit=1)
        if results:
            lat = results[0]['geometry']['lat']
            lon = results[0]['geometry']['lng']
            return lat, lon
    except Exception as e:
        st.error(f"Geocoding error: {e}")

    return None, None

# ================================
# 4. UI – Requester Campus Selection
# ================================
st.subheader("📍 Requester Location")

campus_list = list(campus_coordinates.keys())
requester_campus = st.selectbox("Select your campus", campus_list)

# Default location name = selected campus
location_name = st.text_input("Confirm or enter location", requester_campus)

# ================================
# 5. Determine Requester Coordinates
# ================================
if requester_campus in campus_coordinates:
    lat, lon = campus_coordinates[requester_campus]
else:
    lat, lon = geocode_location(location_name)

# Debug display (remove in production)
st.write("Requester Coordinates:", lat, lon)

# ================================
# 6. Map Display (Safe Loading)
# ================================
if lat is not None and lon is not None:
    st.map({"lat": [lat], "lon": [lon]})
else:
    st.warning("⚠️ Location not found. Please refine your input.")

# ================================
# 7. Shopper Base Selection
# ================================
st.subheader("🛒 Shopper Base")

shopper_base = st.selectbox("Select shopper starting location", list(shopper_base_coordinates.keys()))
shopper_lat, shopper_lon = shopper_base_coordinates[shopper_base]

st.write("Shopper Coordinates:", shopper_lat, shopper_lon)

# ================================
# 8. Ready for Distance Calculation (Next Step)
# ================================
# Placeholder for future distance / emissions model
if lat and lon and shopper_lat and shopper_lon:
    st.success("✅ Locations ready for distance and emissions modelling.")
