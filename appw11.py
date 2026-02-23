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

# Simple login credentials (can be moved to st.secrets for security)
username = "adminsst"
password = "isst@2025"

# === Login system using secrets ===
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

# === Authenticate before running app ===
if not login():
    st.stop()

# === API Key ===
OPENCAGE_API_KEY = "313dd388b5e6451582d57045f93510a5"
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

# === Geocode function ===
def geocode_location(location_name):
    try:
        results = geocoder.geocode(location_name + ", Sierra Leone")
        if results and len(results):
            lat = results[0]['geometry']['lat']
            lon = results[0]['geometry']['lng']
            return lat, lon
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None, None

# === Google Sheets functions ===
def get_google_sheet(sheet_name="GroceryApp"):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    import json
    creds_dict = st.secrets["google_credentials"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def load_requests():
    sheet = get_google_sheet()
    df = get_as_dataframe(sheet)
    df = df.dropna(how='all')
    return df

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

if "Delivery Time" in st.session_state.requests.columns:
    st.session_state.requests.rename(
        columns={"Delivery Time": "Expected Delivery Time"},
        inplace=True
    )

# === Language dictionaries ===
lang_options = {
    "English": {
        "title": "🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱",
        "user_role": "You are a:",
        "requester": "Requester (On Campus)",
        "shopper": "Shopper (Downtown)",
        "name": "Your Name",
        "location_prompt": "📍 Your Campus or Address",
        "current_location_prompt": "📍 Your Current Area",
        "submit": "✅ Submit Request",
        "request_submitted": "Your request has been submitted!",
        "available_requests": "🛒 Available Requests to Deliver",
        "index_prompt": "Enter the index of the request you want to deliver",
        "accept_request": "📦 Accept This Request",
        "assigned_success": "You've been assigned to deliver request #",
        "assigned_error": "Invalid index or empty list",
        "your_assignments": "📋 Your Assigned Deliveries",
        "status_pending": "Pending",
        "status_assigned": "Assigned",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled",
        "status_update": "Update Request Status",
        "rate_request": "⭐ Rate this delivery (1-5):",
        "submit_rating": "Submit Rating",
        "rating_thanks": "Thanks for rating!",
        "no_requests": "No requests available.",
        "campus_select": "🏫 Select your Campus:"
    },
    "Krio": {
        "title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap (CamPDApp) 🇸🇱",
        "user_role": "U na:",
        "requester": "Pipul woi wan buy (Kampos pipul)",
        "shopper": "Shopa (Donton)",
        "name": "U Name",
        "location_prompt": "📍 U Kampos or adres",
        "current_location_prompt": "📍 U curent area",
        "submit": "✅ Sen request",
        "request_submitted": "Dn sen u request!",
        "available_requests": "🛒 Request woi de fɔ delivri",
        "index_prompt": "Put di index woi u wan fɔ deliver",
        "accept_request": "📦 Accept dis request",
        "assigned_success": "U don accept fɔ delivr d request #",
        "assigned_error": "Index no lek valid or list empty",
        "your_assignments": "📋 Tin dem woi u for delivr",
        "status_pending": "Wetin de wait",
        "status_assigned": "Don take",
        "status_delivered": "Don deliver",
        "status_cancelled": "Kansul",
        "status_update": "Mek change pan buy status",
        "rate_request": "⭐ Rate dis delivri (1-5):",
        "submit_rating": "Sen Rate",
        "rating_thanks": "Tenki for rate!",
        "no_requests": "No request rynna.",
        "campus_select": "🏫 Selekt u Kampos:"
    }
}

# === UI language selector ===
selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

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

# === Helper function to calculate surcharge ===
def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

# === Campus Coordinates Fix ===
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
    "EBKUST": (8.4700, -13.2600)
}

# === Page config and title ===
st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# === Requester flow ===
if user_type == txt["requester"]:
    st.subheader("📝 " + txt["submit"])

    name = st.text_input(txt["name"])
    requester_contact = st.text_input("📞 Your Contact Number")
    requester_faculty = st.text_input("Department/Faculty")
    requester_year = st.text_input("Year/Level")
    requester_campus = st.selectbox(txt["campus_select"], campus_list)

    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    location_name = st.text_input(txt["location_prompt"], requester_campus)

# === USE CAMPUS COORDINATES FIRST, ELSE GEOCODE ===
if requester_campus in campus_coordinates:
    lat, lon = campus_coordinates[requester_campus]
else:
    lat, lon = geocode_location(location_name)

    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
        st_folium(m, width=700, height=450)
    else:
        st.warning("⚠️ Location not found.")

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

    all_filled = all([
        name.strip(), requester_contact.strip(), requester_faculty.strip(),
        requester_year.strip(), location_name.strip(), item.strip(),
        qty > 0, max_price >= 0, lat is not None, lon is not None
    ])

    if not all_filled:
        st.info("Please fill in all required fields to submit your request.")
    else:
        if st.button(txt["submit"]):
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
                "Status": txt["status_pending"],
                "Rating": None
            }

            st.session_state.requests = pd.concat(
                [st.session_state.requests, pd.DataFrame([new_row])],
                ignore_index=True
            )

            save_requests(st.session_state.requests)
            st.success(txt["request_submitted"])
