import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import uuid
import gspread
from google.oauth2.service_account import Credentials

# =========================
# GOOGLE SHEET SETUP
# =========================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def connect_to_gsheet():
    creds_dict = dict(st.secrets["google_credentials"])

    private_key = creds_dict["private_key"].strip()

    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")

    creds_dict["private_key"] = private_key

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    client = gspread.authorize(creds)

    sheet_name = "CampusGroceryRequests"

    try:
        sheet = client.open(sheet_name).sheet1
    except gspread.SpreadsheetNotFound:
        sheet = client.create(sheet_name).sheet1

    return sheet


def load_requests_from_gsheet():
    sheet = connect_to_gsheet()
    records = sheet.get_all_records()
    if records:
        st.session_state.requests = pd.DataFrame(records)


def save_requests_to_gsheet():
    sheet = connect_to_gsheet()
    df = st.session_state.requests

    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# =========================
# LOGIN SYSTEM
# =========================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    with st.form("Login"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if (
                username_input == st.secrets["credentials"]["username"]
                and password_input == st.secrets["credentials"]["password"]
            ):
                st.session_state.authenticated = True
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")

    if not st.session_state.authenticated:
        st.stop()

login()

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="CamPDApp")
st.title("🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱")

# =========================
# SESSION INIT
# =========================
if "requests" not in st.session_state:
    st.session_state.requests = pd.DataFrame(columns=[
        "Tracking ID","Requester","Requester Contact","Campus",
        "Item","Qty","Max Price (SLL)","Expected Delivery Time",
        "Preferred Shopper Base","Surcharge (SLL)",
        "Assigned Shopper","Shopper Name",
        "Timestamp","Status","Rating"
    ])
    load_requests_from_gsheet()

# =========================
# CAMPUS + BASES
# =========================
campus_coordinates = {
    "FBC": (8.4840, -13.2317),
    "IPAM": (8.4875, -13.2344),
    "COMAHS": (8.4655, -13.2689),
}

shopper_bases = {
    "Lumley": (8.4571, -13.2924),
    "Aberdeen": (8.4848, -13.2827),
    "Congo Cross": (8.4842, -13.2673),
}

def calculate_surcharge(distance_km):
    base_fee = 1000
    per_km_fee = 500
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

# =========================
# USER ROLE
# =========================
user_type = st.sidebar.radio("You are a:", ["Requester", "Shopper"])

# =========================
# REQUESTER FLOW
# =========================
if user_type == "Requester":
    st.subheader("📝 Submit Request")

    name = st.text_input("Your Name")
    contact = st.text_input("📞 Your Contact Number")
    campus = st.selectbox("🏫 Select your Campus", list(campus_coordinates.keys()))

    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    lat, lon = campus_coordinates[campus]

    # Map
    m = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
    st_folium(m, width=700, height=400)

    # Surcharge calc
    surcharge_options = {}
    for base_name, (base_lat, base_lon) in shopper_bases.items():
        dist = geodesic((lat, lon), (base_lat, base_lon)).km
        surcharge_options[base_name] = calculate_surcharge(dist)

    surcharge_df = pd.DataFrame([
        {"Shopper Base": k, "Estimated Surcharge (SLL)": v}
        for k, v in sorted(surcharge_options.items(), key=lambda x: x[1])
    ])

    st.dataframe(surcharge_df)

    preferred_base = st.selectbox("Preferred Shopper Base", surcharge_df["Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    if st.button("✅ Submit Request"):
        tracking_id = str(uuid.uuid4())[:8]

        new_row = {
            "Tracking ID": tracking_id,
            "Requester": name,
            "Requester Contact": contact,
            "Campus": campus,
            "Item": item,
            "Qty": qty,
            "Max Price (SLL)": max_price,
            "Expected Delivery Time": delivery_time.strftime("%H:%M"),
            "Preferred Shopper Base": preferred_base,
            "Surcharge (SLL)": selected_surcharge,
            "Assigned Shopper": "Unassigned",
            "Shopper Name": "",
            "Timestamp": datetime.utcnow().isoformat(),
            "Status": "Pending",
            "Rating": ""
        }

        st.session_state.requests = pd.concat(
            [st.session_state.requests, pd.DataFrame([new_row])],
            ignore_index=True
        )

        save_requests_to_gsheet()
        st.success(f"Request submitted! Tracking ID: {tracking_id}")

# =========================
# SHOPPER FLOW
# =========================
elif user_type == "Shopper":
    st.subheader("🛒 Available Requests")

    shopper_name = st.text_input("Your Name")

    df = st.session_state.requests
    available_df = df[df["Assigned Shopper"] == "Unassigned"]

    if available_df.empty:
        st.info("No requests available.")
    else:
        st.dataframe(available_df[[
            "Tracking ID","Requester","Item","Qty","Campus",
            "Preferred Shopper Base","Surcharge (SLL)","Status"
        ]])

        track_id_input = st.text_input("Enter Tracking ID to accept")

        if st.button("📦 Accept Request"):
            if track_id_input in available_df["Tracking ID"].values:
                idx = df.index[df["Tracking ID"] == track_id_input][0]

                st.session_state.requests.at[idx, "Assigned Shopper"] = "Accepted"
                st.session_state.requests.at[idx, "Shopper Name"] = shopper_name
                st.session_state.requests.at[idx, "Status"] = "Assigned"

                save_requests_to_gsheet()
                st.success(f"Request {track_id_input} assigned to you")

    # =========================
    # UPDATE STATUS
    # =========================
    st.subheader("📋 Your Assigned Deliveries")

    my_jobs = df[df["Shopper Name"] == shopper_name]

    if not my_jobs.empty:
        st.dataframe(my_jobs[[
            "Tracking ID","Item","Campus","Status"
        ]])

        update_id = st.text_input("Enter Tracking ID to update status")
        new_status = st.selectbox("Update Status", ["Assigned", "Delivered"])

        if st.button("Update Status"):
            if update_id in my_jobs["Tracking ID"].values:
                idx = df.index[df["Tracking ID"] == update_id][0]
                st.session_state.requests.at[idx, "Status"] = new_status

                save_requests_to_gsheet()
                st.success("Status updated!")

# =========================
# RATING SYSTEM
# =========================
st.subheader("⭐ Rate a Delivery")

rating_id = st.text_input("Enter Tracking ID to rate")
rating_value = st.slider("Rating", 1, 5)

if st.button("Submit Rating"):
    df = st.session_state.requests
    if rating_id in df["Tracking ID"].values:
        idx = df.index[df["Tracking ID"] == rating_id][0]
        st.session_state.requests.at[idx, "Rating"] = rating_value

        save_requests_to_gsheet()
        st.success("Thanks for rating!")
