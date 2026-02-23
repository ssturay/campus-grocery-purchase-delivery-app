import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
from opencage.geocoder import OpenCageGeocode
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
import uuid

# --- Login credentials (can move to st.secrets) ---
USERNAME = "adminsst"
PASSWORD = "isst@2025"

# --- Login system ---
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        with st.form("Login"):
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                correct_user = st.secrets["credentials"]["username"]
                correct_pass = st.secrets["credentials"]["password"]

                if user_input == correct_user and pass_input == correct_pass:
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                else:
                    st.error("Invalid credentials")

    return st.session_state.authenticated

if not login():
    st.stop()

# --- OpenCage API ---
OPENCAGE_API_KEY = st.secrets.get("OPENCAGE_API_KEY", "")
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

def geocode_location(location_name):
    try:
        results = geocoder.geocode(location_name + ", Sierra Leone")
        if results and len(results):
            lat = results[0]['geometry']['lat']
            lon = results[0]['geometry']['lng']
            return lat, lon
    except Exception as e:
        st.warning(f"Geocoding error: {e}")
    return None, None

# --- Google Sheets ---
def get_google_sheet(sheet_name="GroceryApp"):
    scope = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def load_requests():
    try:
        sheet = get_google_sheet()
        df = get_as_dataframe(sheet)
        return df.dropna(how='all')
    except Exception as e:
        st.warning(f"Failed to load requests: {e}")
        return pd.DataFrame()

def save_requests(df):
    try:
        sheet = get_google_sheet()
        sheet.clear()
        set_with_dataframe(sheet, df)
    except Exception as e:
        st.error(f"⚠️ Failed to save request: {e}")

# --- Session init ---
if "requests" not in st.session_state:
    st.session_state.requests = load_requests()

# --- Language dictionaries ---
lang_options = {
    "English": {
        "title": "🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱",
        "user_role": "You are a:",
        "requester": "Requester (On Campus)",
        "shopper": "Shopper (Downtown)",
        "name": "Your Name",
        "location_prompt": "📍 Your Campus or Address",
        "submit": "✅ Submit Request",
        "request_submitted": "Your request has been submitted!",
        "campus_select": "🏫 Select your Campus:",
        "status_pending": "Pending",
        "status_assigned": "Assigned",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled"
    },
    "Krio": {
        "title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap (CamPDApp) 🇸🇱",
        "user_role": "U na:",
        "requester": "Pipul woi wan buy (Kampos pipul)",
        "shopper": "Shopa (Donton)",
        "name": "U Name",
        "location_prompt": "📍 U Kampos or adres",
        "submit": "✅ Sen request",
        "request_submitted": "Dn sen u request!",
        "campus_select": "🏫 Selekt u Kampos:",
        "status_pending": "Wetin de wait",
        "status_assigned": "Don take",
        "status_delivered": "Don deliver",
        "status_cancelled": "Kansul"
    }
}

selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

# --- Shopper bases ---
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

# --- Surcharge calculation ---
def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

# --- Campus list ---
campus_list = [
    "FBC", "IPAM", "COMAHS", "Njala FT", "MMTU", "Limkokwing",
    "UNIMTECH", "IAMTECH", "FTC", "LICCSAL", "IMAT",
    "Bluecrest", "UNIMAK", "EBKUST", "Others"
]

# --- Page setup ---
st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# === REQUESTER FLOW ===
if user_type == txt["requester"]:
    st.subheader(txt["submit"])
    name = st.text_input(txt["name"])
    contact = st.text_input("📞 Your Contact Number")
    faculty = st.text_input("Department/Faculty")
    year = st.text_input("Year/Level")
    campus = st.selectbox(txt["campus_select"], campus_list)

    # Location input defaults to selected campus
    location_name = st.text_input(txt["location_prompt"], campus)
    lat, lon = geocode_location(location_name)

    # Map
    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
        st_folium(m, width=700, height=450)
    else:
        st.warning("⚠️ Location not found.")

    # Surcharge calculation
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

    all_filled = all([name.strip(), contact.strip(), faculty.strip(), year.strip(),
                      location_name.strip(), preferred_base, lat, lon])

    if st.button(txt["submit"]) and all_filled:
        tracking_id = str(uuid.uuid4())[:8]  # short unique ID
        new_row = {
            "Tracking ID": tracking_id,
            "Requester": name,
            "Requester Faculty/Department": faculty,
            "Requester Year/Level": year,
            "Requester Contact": contact,
            "Requester Location": location_name,
            "Requester Coordinates": f"{lat},{lon}",
            "Campus": campus,
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
            "Status": txt["status_pending"]
        }
        st.session_state.requests = pd.concat(
            [st.session_state.requests, pd.DataFrame([new_row])],
            ignore_index=True
        )
        save_requests(st.session_state.requests)
        st.success(f"{txt['request_submitted']} Tracking ID: {tracking_id}")
    elif st.button(txt["submit"]):
        st.warning("Please fill in all required fields and ensure location is valid.")

# === SHOPPER FLOW ===
if user_type == txt["shopper"]:
    st.subheader("📋 Available Requests")
    if st.session_state.requests.empty:
        st.info("No requests available.")
    else:
        available_requests = st.session_state.requests[
            st.session_state.requests["Status"] == txt["status_pending"]
        ]
        st.dataframe(available_requests)
