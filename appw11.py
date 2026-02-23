import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
from opencage.geocoder import OpenCageGeocode
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
import folium
from streamlit_folium import st_folium

# === Login system ===
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        with st.form("Login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                correct_user = st.secrets["credentials"]["username"]
                correct_pass = st.secrets["credentials"]["password"]

                if username == correct_user and password == correct_pass:
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    return st.session_state.authenticated


if not login():
    st.stop()

# === API Key ===
OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

# === Geocode function ===
@st.cache_data(show_spinner=False)
def geocode_location(location_name):
    try:
        results = geocoder.geocode(location_name + ", Sierra Leone")
        if results and len(results):
            lat = results[0]['geometry']['lat']
            lon = results[0]['geometry']['lng']
            return lat, lon
    except Exception:
        pass
    return None, None

# === Google Sheets ===
def get_google_sheet(sheet_name="GroceryApp"):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["google_credentials"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).sheet1


def load_requests():
    sheet = get_google_sheet()
    df = get_as_dataframe(sheet)
    return df.dropna(how='all')


def save_requests(df):
    sheet = get_google_sheet()
    sheet.clear()
    set_with_dataframe(sheet, df)

# === Session Init ===
if "requests" not in st.session_state:
    try:
        st.session_state.requests = load_requests()
    except Exception:
        st.session_state.requests = pd.DataFrame(columns=[
            "Requester", "Requester Faculty/Department", "Requester Year/Level",
            "Requester Contact", "Requester Location", "Requester Coordinates",
            "Campus", "Item", "Qty", "Max Price (SLL)", "Expected Delivery Time",
            "Preferred Shopper Base", "Surcharge (SLL)", "Assigned Shopper",
            "Shopper Name", "Shopper Faculty/Department", "Shopper Year/Level",
            "Shopper Contact", "Shopper Location", "Shopper Coordinates",
            "Timestamp", "Status", "Rating"
        ])

# === Campus list ===
campus_list = [
    "FBC", "IPAM", "COMAHS", "Njala FT", "MMTU", "Limkokwing",
    "UNIMTECH", "IAMTECH", "FTC", "LICCSAL", "IMAT",
    "Bluecrest", "UNIMAK", "EBKUST", "Others"
]

# === Campus Coordinates (fast fallback, no API call) ===
campus_coordinates = {
    "FBC": (8.4840, -13.2317),
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
    "EBKUST": (8.4700, -13.2600),
    "Others": None
}

# === Shopper bases ===
shopper_bases = {
    "Lumley": (8.4571, -13.2924),
    "Aberdeen": (8.4848, -13.2827),
    "Congo Cross": (8.4842, -13.2673),
    "Campbell Street": (8.4865, -13.2409),
    "Calaba Town": (8.3786, -13.1664),
    "Jui": (8.3543, -13.1216),
    "Siaka Stevens Street": (8.4867, -13.2349),
    "Circular Road": (8.4830, -13.2260),
    "Eastern Police": (8.4722, -13.2167),
    "Rawdon Street": (8.4856, -13.2338),
    "New England": (8.4746, -13.2500),
    "Hill Station": (8.4698, -13.2661),
    "Hastings": (8.3873, -13.1272),
    "Wilberforce": (8.4678, -13.255)
}

# === Surcharge function ===
def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

# === UI ===
st.set_page_config(page_title="🛍️🚚 CamPDApp 🇸🇱")
st.title("🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱")

user_type = st.sidebar.radio("You are a:", ["Requester (On Campus)", "Shopper (Downtown)"])

# =========================================================
# ===================== REQUESTER FLOW ====================
# =========================================================
if user_type == "Requester (On Campus)":

    st.subheader("📝 Submit Request")

    name = st.text_input("Your Name")
    requester_contact = st.text_input("📞 Your Contact Number")
    requester_faculty = st.text_input("Department/Faculty")
    requester_year = st.text_input("Year/Level")
    requester_campus = st.selectbox("🏫 Select your Campus:", campus_list)

    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    location_name = st.text_input("📍 Your Campus or Address", requester_campus)

    # === Step 1: Try campus coordinates first (FAST) ===
    lat, lon = campus_coordinates.get(requester_campus, (None, None)) \
        if campus_coordinates.get(requester_campus) else (None, None)

    # === Step 2: If user typed a different location → geocode ===
    if location_name != requester_campus:
        lat, lon = geocode_location(location_name)

    # === Step 3: If still None → fallback to campus geocode ===
    if lat is None or lon is None:
        lat, lon = geocode_location(requester_campus)
        if lat and lon:
            st.info("📍 Using campus location for distance calculation.")
        else:
            st.warning("⚠️ Location not found. Please enter a valid campus or area.")

    # === Map ===
    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
        st_folium(m, width=700, height=450)

    # === Surcharge Calculation ===
    surcharge_options = {}

    if lat and lon:
        for base_name, (base_lat, base_lon) in shopper_bases.items():
            dist = geodesic((lat, lon), (base_lat, base_lon)).km
            surcharge_options[base_name] = calculate_surcharge(dist)

        surcharge_df = pd.DataFrame([
            {"Shopper Base": k, "Estimated Surcharge (SLL)": v}
            for k, v in sorted(surcharge_options.items(), key=lambda x: x[1])
        ])

        st.markdown("### Estimated Surcharges")
        st.dataframe(surcharge_df)

        preferred_base = st.selectbox("Preferred Shopper Base", surcharge_df["Shopper Base"])
        selected_surcharge = surcharge_options[preferred_base]
    else:
        preferred_base = None
        selected_surcharge = None

    # === Validation ===
    all_filled = all([
        name.strip(),
        requester_contact.strip(),
        requester_faculty.strip(),
        requester_year.strip(),
        item.strip(),
        qty > 0,
        max_price >= 0,
        lat is not None,
        lon is not None,
        preferred_base is not None
    ])

    if not all_filled:
        st.info("Please fill in all required fields to submit your request.")
    else:
        if st.button("✅ Submit Request"):
            new_row = {
                "Requester": name,
                "Requester Faculty/Department": requester_faculty,
                "Requester Year/Level": requester_year,
                "Requester Contact": requester_contact,
                "Requester Location": location_name,
                "Requester Coordinates": f"{lat},{lon}",
                "Campus": requester_campus,
                "Item": item,
                "Qty": qty,
                "Max Price (SLL)": max_price,
                "Expected Delivery Time": delivery_time.strftime("%H:%M"),
                "Preferred Shopper Base": preferred_base,
                "Surcharge (SLL)": selected_surcharge,
                "Assigned Shopper": "Unassigned",
                "Shopper Name": "",
                "Shopper Faculty/Department": "",
                "Shopper Year/Level": "",
                "Shopper Contact": "",
                "Shopper Location": "",
                "Shopper Coordinates": "",
                "Timestamp": datetime.utcnow().isoformat(),
                "Status": "Pending",
                "Rating": None
            }

            st.session_state.requests = pd.concat(
                [st.session_state.requests, pd.DataFrame([new_row])],
                ignore_index=True
            )

            save_requests(st.session_state.requests)
            st.success("Your request has been submitted!")
