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
# LOGIN
# =========================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    with st.form("Login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if u == st.secrets["credentials"]["username"] and p == st.secrets["credentials"]["password"]:
                st.session_state.authenticated = True
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")

    if not st.session_state.authenticated:
        st.stop()

login()

# =========================
# LANGUAGE
# =========================
lang_options = {
    "English": {
        "title": "🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱",
        "submit": "Submit Request",
        "available": "Available Requests",
        "accept": "Accept Request",
        "assigned": "Assigned",
        "pending": "Pending",
        "delivered": "Delivered",
        "rate": "Rate Delivery"
    },
    "Krio": {
        "title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap (CamPDApp) 🇸🇱",
        "submit": "Sen Request",
        "available": "Request dem",
        "accept": "Accept Request",
        "assigned": "Don Tek",
        "pending": "Wetin De Wait",
        "delivered": "Don Deliver",
        "rate": "Rate Delivri"
    }
}

selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

# =========================
# CAMPUSES
# =========================
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

def calculate_surcharge(distance_km):
    base_fee = 1000
    per_km_fee = 500
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

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
# USER ROLE
# =========================
user_type = st.sidebar.radio("You are a:", ["Requester", "Shopper"])

# =========================
# REQUESTER FLOW
# =========================
if user_type == "Requester":
    st.subheader(txt["submit"])

    name = st.text_input("Your Name")
    contact = st.text_input("📞 Contact")
    campus = st.selectbox("🏫 Campus", list(campus_coordinates.keys()))

    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    lat, lon = campus_coordinates[campus]

    m = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon]).add_to(m)
    st_folium(m, width=700, height=400)

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

    if st.button(txt["submit"]):
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
            "Status": txt["pending"],
            "Rating": ""
        }

        st.session_state.requests = pd.concat(
            [st.session_state.requests, pd.DataFrame([new_row])],
            ignore_index=True
        )

        save_requests_to_gsheet()
        st.success(f"Tracking ID: {tracking_id}")

# =========================
# SHOPPER FLOW
# =========================
elif user_type == "Shopper":
    st.subheader(txt["available"])

    shopper_name = st.text_input("Your Name")

    df = st.session_state.requests
    available_df = df[df["Assigned Shopper"] == "Unassigned"]

    if available_df.empty:
        st.info("No requests available.")
    else:
        st.dataframe(available_df)

        track_id_input = st.text_input("Tracking ID")

        if st.button(txt["accept"]):
            if track_id_input in available_df["Tracking ID"].values:
                idx = df.index[df["Tracking ID"] == track_id_input][0]

                st.session_state.requests.at[idx, "Assigned Shopper"] = "Accepted"
                st.session_state.requests.at[idx, "Shopper Name"] = shopper_name
                st.session_state.requests.at[idx, "Status"] = txt["assigned"]

                save_requests_to_gsheet()
                st.success("Assigned!")

    st.subheader("📋 My Deliveries")

    my_jobs = df[df["Shopper Name"] == shopper_name]

    if not my_jobs.empty:
        st.dataframe(my_jobs)

        update_id = st.text_input("Tracking ID to update")
        new_status = st.selectbox("Status", [txt["assigned"], txt["delivered"]])

        if st.button("Update Status"):
            if update_id in my_jobs["Tracking ID"].values:
                idx = df.index[df["Tracking ID"] == update_id][0]
                st.session_state.requests.at[idx, "Status"] = new_status
                save_requests_to_gsheet()
                st.success("Updated!")

# =========================
# RATING
# =========================
st.subheader(txt["rate"])

rating_id = st.text_input("Tracking ID to rate")
rating_value = st.slider("Rating", 1, 5)

if st.button("Submit Rating"):
    df = st.session_state.requests
    if rating_id in df["Tracking ID"].values:
        idx = df.index[df["Tracking ID"] == rating_id][0]
        st.session_state.requests.at[idx, "Rating"] = rating_value
        save_requests_to_gsheet()
        st.success("Thanks for rating!")
