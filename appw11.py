import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
from opencage.geocoder import OpenCageGeocode
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from streamlit_folium import st_folium
import folium
import uuid  # For tracking ID

# =========================
# ===== Login System ======
# =========================
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
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")
    return st.session_state.authenticated

if not login():
    st.stop()

# =========================
# ===== API KEYS ==========
# =========================
OPENCAGE_API_KEY = st.secrets.get("OPENCAGE_API_KEY", "")
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

# =========================
# ===== Geocode ===========
# =========================
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

# =========================
# ===== Google Sheets =====
# =========================
def get_google_sheet(sheet_name="GroceryApp"):
    creds_dict = st.secrets["google_credentials"]  # JSON dict
    client = gspread.service_account_from_dict(creds_dict)
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

# =========================
# ===== Session Init ======
# =========================
if "requests" not in st.session_state:
    try:
        st.session_state.requests = load_requests()
    except Exception:
        st.session_state.requests = pd.DataFrame(columns=[
            "Tracking ID", "Requester", "Requester Faculty/Department", "Requester Year/Level",
            "Requester Contact", "Requester Location", "Requester Coordinates",
            "Campus", "Item", "Qty", "Max Price (SLL)", "Expected Delivery Time",
            "Preferred Shopper Base", "Surcharge (SLL)", "Assigned Shopper",
            "Shopper Name", "Shopper Faculty/Department", "Shopper Year/Level",
            "Shopper Contact", "Shopper Location", "Shopper Coordinates",
            "Timestamp", "Status", "Rating"
        ])

# =========================
# ===== Language ==========
# =========================
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

# =========================
# ===== Campus List & Coordinates =====
# =========================
campus_list = [
    "FBC", "IPAM", "COMAHS", "Njala FT", "MMTU", "Limkokwing",
    "UNIMTECH", "IAMTECH", "FTC", "LICCSAL", "IMAT",
    "Bluecrest", "UNIMAK", "EBKUST", "Others"
]

campus_coordinates = {
    "FBC": (8.4820, -13.2340),
    "IPAM": (8.4835, -13.2365),
    "COMAHS": (8.4790, -13.2300),
    "Njala FT": (8.4650, -13.2500),
    "MMTU": (8.4800, -13.2200),
    "Limkokwing": (8.4900, -13.2400),
    "UNIMTECH": (8.4700, -13.2250),
    "IAMTECH": (8.4750, -13.2350),
    "FTC": (8.4850, -13.2450),
    "LICCSAL": (8.4780, -13.2420),
    "IMAT": (8.4725, -13.2380),
    "Bluecrest": (8.4760, -13.2480),
    "UNIMAK": (8.4810, -13.2320),
    "EBKUST": (8.4675, -13.2475),
    "Others": (8.484, -13.232)
}

# =========================
# ===== Shopper Bases =====
# =========================
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

# =========================
# ===== Surcharge Helper ===
# =========================
def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

# =========================
# ===== Page Setup =======
# =========================
st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# =========================
# ===== Requester Flow =====
# =========================
if user_type == txt["requester"]:
    st.subheader("📝 " + txt["submit"])

    # Form Inputs
    name = st.text_input(txt["name"])
    requester_contact = st.text_input("📞 Contact Number")
    requester_faculty = st.text_input("Department/Faculty")
    requester_year = st.text_input("Year/Level")
    requester_campus = st.selectbox(txt["campus_select"], campus_list)
    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    # Map defaults to campus
    default_lat, default_lon = campus_coordinates.get(requester_campus, (8.484, -13.232))
    st.markdown("📍 Your location (drag marker if needed):")
    m = folium.Map(location=[default_lat, default_lon], zoom_start=15)
    folium.Marker([default_lat, default_lon], draggable=True, tooltip="Requester Location").add_to(m)
    map_data = st_folium(m, width=700, height=450, returned_objects=["last_clicked"])

    if map_data and map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
    else:
        lat, lon = default_lat, default_lon

    # Surcharge calculation
    surcharge_options = {}
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

    # Validation & Submit
    all_filled = all([
        name.strip(), requester_contact.strip(), requester_faculty.strip(),
        requester_year.strip(), item.strip(), qty > 0, max_price >= 0,
        lat is not None, lon is not None
    ])

    if not all_filled:
        st.info("Please fill in all required fields to submit your request.")
    else:
        if st.button(txt["submit"]):
            tracking_id = str(uuid.uuid4())[:8]  # short tracking ID
            new_row = {
                "Tracking ID": tracking_id,
                "Requester": name,
                "Requester Faculty/Department": requester_faculty,
                "Requester Year/Level": requester_year,
                "Requester Contact": requester_contact,
                "Requester Location": requester_campus,
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
            try:
                save_requests(st.session_state.requests)
                st.success(f"{txt['request_submitted']} Tracking ID: {tracking_id}")
            except Exception as e:
                st.error(f"⚠️ Failed to save request: {e}")

# =========================
# ===== Shopper Flow =====
# =========================
elif user_type == txt["shopper"]:
    st.subheader(txt["shopper"])
    df = st.session_state.requests
    available_df = df[df["Status"] == txt["status_pending"]]
    if available_df.empty:
        st.info("No requests available.")
    else:
        st.dataframe(available_df)
