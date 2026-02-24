import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
import folium
from streamlit_folium import st_folium
import uuid
from google.oauth2.service_account import Credentials
import gspread

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
        "contact": "Your Contact",
        "faculty": "Department/Faculty",
        "year": "Year/Level",
        "location_prompt": "📍 Your Campus",
        "item": "Item",
        "qty": "Quantity",
        "max_price": "Max Price (SLL)",
        "delivery_time": "Expected Delivery Time",
        "submit": "✅ Submit Request",
        "request_submitted": "Your request has been submitted!",
        "available_requests": "🛒 Available Requests",
        "accept_request": "📦 Accept Request",
        "assigned_success": "You've accepted request: ",
        "assigned_error": "Invalid Tracking ID",
        "no_requests": "No requests available.",
        "campus_select": "🏫 Select your Campus:",
        "status_pending": "Pending",
        "status_assigned": "Assigned",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled"
    },
    "Krio": {
        "title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap 🇸🇱",
        "user_role": "U na:",
        "requester": "Pipul woi wan buy",
        "shopper": "Shopa",
        "name": "U Name",
        "contact": "U Contact",
        "faculty": "Department/Faculty",
        "year": "Year/Level",
        "location_prompt": "📍 U Kampos",
        "item": "Item",
        "qty": "Quantity",
        "max_price": "Max Price (SLL)",
        "delivery_time": "Expected Delivery Time",
        "submit": "✅ Sen Request",
        "request_submitted": "Dn sen u request!",
        "available_requests": "🛒 Request woi de",
        "accept_request": "📦 Accept dis request",
        "assigned_success": "U don accept: ",
        "assigned_error": "Tracking ID no correct",
        "no_requests": "No request rynna.",
        "campus_select": "🏫 Selekt u Kampos:",
        "status_pending": "Wetin de wait",
        "status_assigned": "Don take",
        "status_delivered": "Don deliver",
        "status_cancelled": "Kansul"
    }
}

selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

# =========================
# 🔐 LOGIN
# =========================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    with st.form("Login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if (
                username == st.secrets["credentials"]["username"]
                and password == st.secrets["credentials"]["password"]
            ):
                st.session_state.authenticated = True
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")

    if not st.session_state.authenticated:
        st.stop()
    return True

login()

# =========================
# 📍 CAMPUS & SHOPPER DATA
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
    return int(math.ceil((base_fee + per_km_fee * distance_km) / 100.0) * 100)

# =========================
# 🔐 GOOGLE SHEETS
# =========================
SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def connect_to_gsheet():
    try:
        creds_dict = dict(st.secrets["google"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    except KeyError:
        st.error("❌ Google credentials missing in secrets!")
        st.stop()
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
# 🧑‍🎓 USER TYPE
# =========================
user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# =========================
# REQUESTER FLOW
# =========================
if user_type == txt["requester"]:

    st.subheader(txt["submit"])
    name = st.text_input(txt["name"])
    contact = st.text_input(txt["contact"])
    faculty = st.text_input(txt["faculty"])
    year = st.text_input(txt["year"])
    campus = st.selectbox(txt["campus_select"], list(campus_coordinates.keys()))
    item = st.text_input(txt["item"])
    qty = st.number_input(txt["qty"], min_value=1, value=1)
    max_price = st.number_input(txt["max_price"], min_value=0, value=20000)
    delivery_time = st.time_input(txt["delivery_time"])

    lat, lon = campus_coordinates[campus]

    # 🗺️ Map showing requester location
    m = folium.Map(location=[lat, lon], zoom_start=16)
    folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
    st_folium(m, width=700, height=450)

    # 💰 Surcharge calculation
    surcharge_options = {}
    for base, coords in shopper_bases.items():
        dist = geodesic((lat, lon), coords).km
        surcharge_options[base] = calculate_surcharge(dist)

    surcharge_df = pd.DataFrame([
        {"Preferred Shopper Base": k, "Surcharge (SLL)": v}
        for k, v in sorted(surcharge_options.items(), key=lambda x: x[1])
    ])
    st.dataframe(surcharge_df)

    preferred_base = st.selectbox("Preferred Shopper Base", surcharge_df["Preferred Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    if st.button(txt["submit"]):
        tracking_id = str(uuid.uuid4())[:8]
        row = {
            "Tracking ID": tracking_id,
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
            "Status": txt["status_pending"],
            "Rating": ""
        }
        save_to_gsheet(row)
        st.success(f"{txt['request_submitted']} Tracking ID: {tracking_id}")

# =========================
# SHOPPER FLOW
# =========================
else:
    df = load_data()
    available_df = df[df["Assigned Shopper"] == "Unassigned"]
    st.subheader(txt["available_requests"])

    if available_df.empty:
        st.info(txt["no_requests"])
    else:
        st.dataframe(available_df)
        track_id = st.text_input("Enter Tracking ID to Accept")

        if st.button(txt["accept_request"]):
            if track_id in df["Tracking ID"].values:
                cell = sheet.find(track_id)
                sheet.update_cell(cell.row, df.columns.get_loc("Assigned Shopper") + 1, "Accepted")
                sheet.update_cell(cell.row, df.columns.get_loc("Status") + 1, txt["status_assigned"])
                st.success(txt["assigned_success"] + track_id)
            else:
                st.error(txt["assigned_error"])
