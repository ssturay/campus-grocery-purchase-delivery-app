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
# LOGIN WITH ROLES
# =========================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_role = None

    if st.session_state.authenticated:
        return True

    with st.form("Login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            # Admin login
            if u == st.secrets["admin"]["username"] and p == st.secrets["admin"]["password"]:
                st.session_state.authenticated = True
                st.session_state.user_role = "Admin"
                st.success("Admin login successful!")
            # Regular user login
            elif u == st.secrets["credentials"]["username"] and p == st.secrets["credentials"]["password"]:
                st.session_state.authenticated = True
                st.session_state.user_role = "User"
                st.success("Login successful!")
            else:
                st.error("Invalid credentials")

    if not st.session_state.authenticated:
        st.stop()

login()

# =========================
# LANGUAGE OPTIONS
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
# CAMPUSES & SHOPPER BASES
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
# ADMIN DASHBOARD
# =========================
if st.session_state.user_role == "Admin":
    st.subheader("📊 Admin Dashboard - All Requests")
    df = st.session_state.requests

    st.dataframe(df)

    st.subheader("Filter by Status")
    status_filter = st.multiselect("Status", df["Status"].unique(), default=df["Status"].unique())
    filtered_df = df[df["Status"].isin(status_filter)]
    st.dataframe(filtered_df)

    st.subheader("Map View of Requests")
    if not filtered_df.empty:
        avg_lat = filtered_df.apply(lambda row: campus_coordinates.get(row["Campus"], (0,0))[0], axis=1).mean()
        avg_lon = filtered_df.apply(lambda row: campus_coordinates.get(row["Campus"], (0,0))[1], axis=1).mean()
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)
        for _, row in filtered_df.iterrows():
            campus = row["Campus"]
            lat, lon = campus_coordinates.get(campus, (0,0))
            folium.Marker([lat, lon], popup=f"{row['Tracking ID']} - {row['Item']}").add_to(m)
        st_folium(m, width=700, height=400)

    st.subheader("Export Data")
    if st.button("Download CSV"):
        csv_data = filtered_df.to_csv(index=False)
        st.download_button("Download CSV", csv_data, "all_requests.csv", "text/csv")

    st.stop()  # Stop further app execution for admin

# =========================
# USER ROLE (Requester / Shopper)
# =========================
user_type = st.sidebar.radio("You are a:", ["Requester", "Shopper"])
