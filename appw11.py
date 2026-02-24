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
        "name": "Your Name",
        "contact": "📞 Your Contact Number",
        "faculty": "Department/Faculty",
        "year": "Year/Level",
        "campus": "🏫 Select your Campus",
        "submit": "✅ Submit Request",
        "success": "Your request has been submitted!",
        "available": "🛒 Available Requests to Deliver",
        "accept": "📦 Accept This Request",
        "no_requests": "No requests available.",
        "invalid": "Invalid Tracking ID",
        "assigned": "You've been assigned to deliver request #",
        "item": "Item",
        "qty": "Quantity",
        "price": "Max Price (SLL)",
        "time": "Expected Delivery Time",
        "preferred_base": "Preferred Shopper Base",
        "surcharge_table": "Estimated Surcharges"
    },
    "Krio": {
        "title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap (CamPDApp) 🇸🇱",
        "user_role": "U na:",
        "requester": "Pipul woi wan buy (Kampos)",
        "shopper": "Shopa (Donton)",
        "name": "U Name",
        "contact": "📞 U Kontak",
        "faculty": "Fakulti/Dept",
        "year": "Yia/Lɛvɛl",
        "campus": "🏫 Selekt u Kampos",
        "submit": "✅ Sen Request",
        "success": "Don sen u request!",
        "available": "🛒 Request woi de fɔ delivri",
        "accept": "📦 Accept dis request",
        "no_requests": "No request rynna.",
        "invalid": "Tracking ID no correct",
        "assigned": "U don accept request #",
        "item": "Item",
        "qty": "Kwantity",
        "price": "Max Price (SLL)",
        "time": "Tɛm fɔ delivri",
        "preferred_base": "Shoppa base woi u want",
        "surcharge_table": "Estimated Sɔchaj"
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
    sheet = client.open("GroceryApp").sheet1
    return sheet

sheet = connect_to_gsheet()

@st.cache_data(ttl=10)
def load_data():
    try:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def save_to_gsheet(row_dict):
    sheet.append_row(list(row_dict.values()))

# =========================
# 🔑 LOGIN SYSTEM
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
# 🌍 PAGE CONFIG
# =========================
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

if "requests" not in st.session_state:
    st.session_state.requests = load_data()

# =========================
# 👤 USER TYPE
# =========================
user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# =====================================================
# 🧑‍🎓 REQUESTER FLOW
# =====================================================
if user_type == txt["requester"]:

    name = st.text_input(txt["name"])
    contact = st.text_input(txt["contact"])
    faculty = st.text_input(txt["faculty"])
    year = st.text_input(txt["year"])
    campus = st.selectbox(txt["campus"], list(campus_coordinates.keys()))

    item = st.text_input(txt["item"])
    qty = st.number_input(txt["qty"], min_value=1, value=1)
    max_price = st.number_input(txt["price"], min_value=0, value=20000)
    delivery_time = st.time_input(txt["time"])

    lat, lon = campus_coordinates[campus]

    # 🗺️ MAP
    m = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
    st_folium(m, width=700, height=450)

    # 💰 SURCHARGE TABLE
    surcharge_options = {}
    for base_name, (b_lat, b_lon) in shopper_bases.items():
        dist = geodesic((lat, lon), (b_lat, b_lon)).km
        surcharge_options[base_name] = calculate_surcharge(dist)

    surcharge_df = pd.DataFrame(
        [{"Shopper Base": k, "Estimated Surcharge (SLL)": v}
         for k, v in sorted(surcharge_options.items(), key=lambda x: x[1])]
    )

    st.markdown(f"### {txt['surcharge_table']}")
    st.dataframe(surcharge_df)

    preferred_base = st.selectbox(txt["preferred_base"], surcharge_df["Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    if st.button(txt["submit"]):

        tracking_id = str(uuid.uuid4())[:8]

        new_row = {
            "Tracking ID": tracking_id,
            "Requester": name,
            "Faculty": faculty,
            "Year": year,
            "Contact": contact,
            "Campus": campus,
            "Coordinates": f"{lat},{lon}",
            "Item": item,
            "Qty": qty,
            "Max Price": max_price,
            "Delivery Time": delivery_time.strftime("%H:%M"),
            "Preferred Base": preferred_base,
            "Surcharge": selected_surcharge,
            "Assigned Shopper": "Unassigned",
            "Status": "Pending",
            "Timestamp": datetime.utcnow().isoformat()
        }

        save_to_gsheet(new_row)

        st.session_state.requests = pd.concat(
            [st.session_state.requests, pd.DataFrame([new_row])],
            ignore_index=True
        )

        st.success(f"{txt['success']} Tracking ID: {tracking_id}")

# =====================================================
# 🛵 SHOPPER FLOW
# =====================================================
else:

    df = load_data()

    available_df = df[df["Assigned Shopper"] == "Unassigned"]

    st.subheader(txt["available"])

    if available_df.empty:
        st.info(txt["no_requests"])
    else:
        st.dataframe(available_df[[
            "Tracking ID", "Requester", "Item", "Qty", "Campus", "Preferred Base", "Surcharge", "Status"
        ]])

        track_id_input = st.text_input("Tracking ID")

        if st.button(txt["accept"]):

            if track_id_input in available_df["Tracking ID"].values:

                cell = sheet.find(track_id_input)

                sheet.update_cell(cell.row, df.columns.get_loc("Assigned Shopper") + 1, "Accepted")
                sheet.update_cell(cell.row, df.columns.get_loc("Status") + 1, "Assigned")

                st.success(f"{txt['assigned']}{track_id_input}")
            else:
                st.error(txt["invalid"])
