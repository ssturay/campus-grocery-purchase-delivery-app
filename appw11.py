import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import uuid
import json
import gspread
from google.oauth2.service_account import Credentials

# =========================
# 🌐 LANGUAGE OPTIONS
# =========================
lang_options = {
    "English": {
        "title": "🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱",
        "user_role": "You are a:",
        "requester": "Requester (On Campus)",
        "shopper": "Shopper (Downtown)",
        "submit": "✅ Submit Request",
        "available": "🛒 Available Requests",
        "accept": "📦 Accept Request",
        "success": "Request submitted!",
        "no_requests": "No requests available.",
        "invalid": "Invalid Tracking ID",
        "assigned": "Request accepted: "
    },
    "Krio": {
        "title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap 🇸🇱",
        "user_role": "U na:",
        "requester": "Pipul woi wan buy",
        "shopper": "Shopa",
        "submit": "✅ Sen Request",
        "available": "🛒 Request woi de",
        "accept": "📦 Accept dis request",
        "success": "Don sen request!",
        "no_requests": "No request rynna.",
        "invalid": "Tracking ID no correct",
        "assigned": "U don accept: "
    }
}

selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

# =========================
# 🔐 GOOGLE SHEETS SETUP
# =========================
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def connect_to_gsheet():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
    client = gspread.authorize(creds)
    return client.open("GroceryApp").sheet1

sheet = connect_to_gsheet()

@st.cache_data(ttl=10)
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def save_to_gsheet(row_dict):
    sheet.append_row(list(row_dict.values()))

# =========================
# 🔑 LOGIN
# =========================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    with st.form("Login"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if (
                user == st.secrets["credentials"]["username"]
                and pw == st.secrets["credentials"]["password"]
            ):
                st.session_state.authenticated = True
                st.success("Login successful")
            else:
                st.error("Invalid credentials")

    if not st.session_state.authenticated:
        st.stop()

login()

st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

# =========================
# 📍 DATA
# =========================
campus_coordinates = {
    "FBC": (8.4840, -13.2317),
    "IPAM": (8.4875, -13.2344),
    "COMAHS": (8.4655, -13.2689),
    "Njala FT": (8.3780, -13.1665),
    "MMTU": (8.4806, -13.2586),
}

shopper_bases = {
    "Lumley": (8.4571, -13.2924),
    "Aberdeen": (8.4848, -13.2827),
    "Congo Cross": (8.4842, -13.2673),
    "Campbell Street": (8.4865, -13.2409),
}

def calculate_surcharge(distance_km):
    base_fee = 1000
    per_km_fee = 500
    return int(math.ceil((base_fee + per_km_fee * distance_km) / 100.0) * 100)

user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# =====================================================
# 🧑‍🎓 REQUESTER
# =====================================================
if user_type == txt["requester"]:

    name = st.text_input("Requester")
    faculty = st.text_input("Requester Faculty/Department")
    year = st.text_input("Requester Year/Level")
    contact = st.text_input("Requester Contact")
    campus = st.selectbox("Campus", list(campus_coordinates.keys()))

    item = st.text_input("Item")
    qty = st.number_input("Qty", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    lat, lon = campus_coordinates[campus]

    # 🗺️ MAP
    m = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
    st_folium(m, width=700, height=450)

    # 💰 SURCHARGE TABLE
    surcharge_options = {}
    for base, coords in shopper_bases.items():
        dist = geodesic((lat, lon), coords).km
        surcharge_options[base] = calculate_surcharge(dist)

    surcharge_df = pd.DataFrame(
        [{"Preferred Shopper Base": k, "Surcharge (SLL)": v}
         for k, v in sorted(surcharge_options.items(), key=lambda x: x[1])]
    )

    st.dataframe(surcharge_df)

    preferred_base = st.selectbox("Preferred Shopper Base", surcharge_df["Preferred Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    if st.button(txt["submit"]):

        tracking_id = str(uuid.uuid4())[:8]

        row = {
            "Requester": name,
            "Requester Faculty/Department": faculty,
            "Requester Year/Level": year,
            "Requester Contact": contact,
            "Requester Location": campus,
            "Requester Coordinates": f"{lat},{lon}",
            "Campus": campus,
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
            "Rating": ""
        }

        save_to_gsheet(row)
        st.success(f"{txt['success']} ID: {tracking_id}")

# =====================================================
# 🛵 SHOPPER
# =====================================================
else:

    df = load_data()
    available_df = df[df["Assigned Shopper"] == "Unassigned"]

    st.subheader(txt["available"])

    if available_df.empty:
        st.info(txt["no_requests"])
    else:
        st.dataframe(available_df)

        track_id = st.text_input("Enter Requester Name to Accept")

        if st.button(txt["accept"]):

            if track_id in df["Requester"].values:

                cell = sheet.find(track_id)

                sheet.update_cell(cell.row, df.columns.get_loc("Assigned Shopper") + 1, "Accepted")
                sheet.update_cell(cell.row, df.columns.get_loc("Status") + 1, "Assigned")

                st.success(txt["assigned"] + track_id)
            else:
                st.error(txt["invalid"])
