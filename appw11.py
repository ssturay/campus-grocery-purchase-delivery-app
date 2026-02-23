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
import random
import string

# ====================
# Login system
# ====================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        with st.form("Login"):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                correct_user = st.secrets["credentials"]["username"]
                correct_pass = st.secrets["credentials"]["password"]

                if username_input == correct_user and password_input == correct_pass:
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")

    return st.session_state.authenticated

# Authenticate
if not login():
    st.stop()

# ====================
# API key for geocoding
# ====================
OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

# ====================
# Geocoding function
# ====================
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

# ====================
# Google Sheets functions
# ====================
def get_google_sheet(sheet_name="GroceryApp"):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
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

# ====================
# Session initialization
# ====================
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

# ====================
# Language dictionaries
# ====================
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
        "status_pending": "Pending",
        "status_assigned": "Assigned",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled",
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
        "status_pending": "Wetin de wait",
        "status_assigned": "Don take",
        "status_delivered": "Don deliver",
        "status_cancelled": "Kansul",
        "campus_select": "🏫 Selekt u Kampos:"
    }
}

selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

# ====================
# Shopper bases & campus coordinates
# ====================
shopper_bases = {
    "Lumley": (8.4571, -13.2924),
    "Aberdeen": (8.4848, -13.2827),
    "Congo Cross": (8.4842, -13.2673),
    "Campbell Street": (8.4865, -13.2409)
}

campus_coordinates = {
    "FBC": (8.4840, -13.2317),
    "IPAM": (8.4875, -13.2344),
    "COMAHS": (8.4655, -13.2689)
}

# ====================
# Helper functions
# ====================
def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

def generate_tracking_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ====================
# Page config
# ====================
st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# ====================
# Requester flow
# ====================
if user_type == txt["requester"]:
    st.subheader("📝 " + txt["submit"])

    name = st.text_input(txt["name"])
    requester_contact = st.text_input("📞 Your Contact Number")
    requester_faculty = st.text_input("Department/Faculty")
    requester_year = st.text_input("Year/Level")
    campus_list = list(campus_coordinates.keys())
    requester_campus = st.selectbox(txt["campus_select"], campus_list)

    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    # Force campus coordinate lock
    lat, lon = campus_coordinates[requester_campus]

    # Show requester map
    m = folium.Map(location=[lat, lon], zoom_start=15)
    folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
    st_folium(m, width=700, height=450)

    # Calculate surcharge
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

    # Validate and submit
    all_filled = all([name.strip(), requester_contact.strip(), requester_faculty.strip(),
                      requester_year.strip(), item.strip(), qty > 0, max_price >= 0])

    if all_filled and st.button(txt["submit"]):
        tracking_id = generate_tracking_id()
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
        st.session_state.requests = pd.concat([st.session_state.requests, pd.DataFrame([new_row])], ignore_index=True)
        save_requests(st.session_state.requests)
        st.success(f"{txt['request_submitted']} Tracking ID: {tracking_id}")

# ====================
# Shopper flow
# ====================
else:
    st.subheader(txt["available_requests"])

    # Shopper info
    shopper_name = st.text_input("Your Name")
    shopper_contact = st.text_input("📞 Contact Number")
    shopper_faculty = st.text_input("Department/Faculty")
    shopper_year = st.text_input("Year/Level")
    current_location = st.text_input(txt["current_location_prompt"])

    shop_lat, shop_lon = geocode_location(current_location)
    if shop_lat and shop_lon:
        st.map(pd.DataFrame([[shop_lat, shop_lon]], columns=['lat','lon']))

    # Filter pending requests
    pending_requests = st.session_state.requests[
        st.session_state.requests['Status'] == txt["status_pending"]
    ].reset_index(drop=True)

    if pending_requests.empty:
        st.info("No requests available at the moment.")
    else:
        st.dataframe(pending_requests[[
            'Tracking ID', 'Requester', 'Item', 'Qty', 'Max Price (SLL)',
            'Preferred Shopper Base', 'Surcharge (SLL)', 'Campus'
        ]])

        selected_tracking_id = st.selectbox("Select Tracking ID to accept", pending_requests['Tracking ID'])
        selected_request = pending_requests[pending_requests['Tracking ID'] == selected_tracking_id].iloc[0]
        req_coords = selected_request['Requester Coordinates'].split(',')
        req_lat, req_lon = float(req_coords[0]), float(req_coords[1])

        # Map with both shopper & requester
        map_req = folium.Map(location=[req_lat, req_lon], zoom_start=15)
        folium.Marker([req_lat, req_lon], tooltip=f"Requester: {selected_request['Requester']}").add_to(map_req)
        if shop_lat and shop_lon:
            folium.Marker([shop_lat, shop_lon], tooltip=f"Your Location: {shopper_name}", icon=folium.Icon(color='green')).add_to(map_req)
        st_folium(map_req, width=700, height=450)

        if st.button("📦 Accept Request"):
            idx = st.session_state.requests[st.session_state.requests['Tracking ID'] == selected_tracking_id].index[0]
            st.session_state.requests.at[idx, 'Assigned Shopper'] = shopper_name
            st.session_state.requests.at[idx, 'Shopper Name'] = shopper_name
            st.session_state.requests.at[idx, 'Shopper Contact'] = shopper_contact
            st.session_state.requests.at[idx, 'Shopper Faculty/Department'] = shopper_faculty
            st.session_state.requests.at[idx, 'Shopper Year/Level'] = shopper_year
            st.session_state.requests.at[idx, 'Shopper Location'] = current_location
            st.session_state.requests.at[idx, 'Shopper Coordinates'] = f"{shop_lat},{shop_lon}"
            st.session_state.requests.at[idx, 'Status'] = txt["status_assigned"]
            save_requests(st.session_state.requests)
            st.success(f"Request {selected_tracking_id} has been assigned to you!")
