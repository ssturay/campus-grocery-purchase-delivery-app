import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
from opencage.geocoder import OpenCageGeocode
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import folium
from streamlit_folium import st_folium

# ====================
# Simple login
# ====================
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

# ====================
# OpenCage Geocoder
# ====================
OPENCAGE_API_KEY = st.secrets["OPENCAGE_API_KEY"]
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

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
# Google Sheets functions using gspread.service_account_from_dict
# ====================
def get_google_sheet(sheet_name="GroceryApp"):
    creds_dict = st.secrets["google_credentials"]
    gc = gspread.service_account_from_dict(creds_dict)
    sheet = gc.open(sheet_name).sheet1
    return sheet

def load_requests():
    try:
        sheet = get_google_sheet()
        df = get_as_dataframe(sheet)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.warning("⚠️ Could not load Google Sheet. Using empty dataframe.")
        return pd.DataFrame(columns=[
            "Requester", "Requester Faculty/Department", "Requester Year/Level",
            "Requester Contact", "Requester Location", "Requester Coordinates",
            "Campus", "Item", "Qty", "Max Price (SLL)", "Expected Delivery Time",
            "Preferred Shopper Base", "Surcharge (SLL)", "Assigned Shopper",
            "Shopper Name", "Shopper Faculty/Department", "Shopper Year/Level",
            "Shopper Contact", "Shopper Location", "Shopper Coordinates",
            "Timestamp", "Status", "Rating", "Tracking ID"
        ])

def save_requests(df):
    sheet = get_google_sheet()
    sheet.clear()
    set_with_dataframe(sheet, df)

# ====================
# Initialize session
# ====================
if "requests" not in st.session_state:
    st.session_state.requests = load_requests()

# ====================
# Campus & Shopper Data
# ====================
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

campus_list = list(campus_coordinates.keys())

def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return int(math.ceil(surcharge / 100.0) * 100)

# ====================
# UI Language
# ====================
lang_options = {
    "English": {"title": "🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱",
                "user_role": "You are a:", "requester": "Requester (On Campus)",
                "submit": "✅ Submit Request", "request_submitted": "Your request has been submitted!",
                "campus_select": "🏫 Select your Campus:"},
    "Krio": {"title": "🛍️🚚 Kampos Gɔsri Buy an Delivri Ap (CamPDApp) 🇸🇱",
             "user_role": "U na:", "requester": "Pipul woi wan buy (Kampos pipul)",
             "submit": "✅ Sen request", "request_submitted": "Dn sen u request!",
             "campus_select": "🏫 Selekt u Kampos:"}
}

selected_language = st.sidebar.selectbox("Language", ["English", "Krio"])
txt = lang_options[selected_language]

st.set_page_config(page_title=txt["title"])
st.title(txt["title"])

user_type = st.sidebar.radio(txt["user_role"], [txt["requester"]])

# ====================
# Requester Flow
# ====================
if user_type == txt["requester"]:
    st.subheader("📝 " + txt["submit"])

    name = st.text_input("Your Name")
    contact = st.text_input("📞 Contact Number")
    faculty = st.text_input("Department/Faculty")
    year = st.text_input("Year/Level")
    campus = st.selectbox(txt["campus_select"], campus_list)

    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    # Lock coordinates to campus
    lat, lon = campus_coordinates.get(campus, (None, None))

    # Map
    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
        st_folium(m, width=700, height=450)
    else:
        st.warning("⚠️ Campus coordinates not found.")

    # Surcharge calculation
    surcharge_options = {base: calculate_surcharge(geodesic((lat, lon), coords).km)
                         for base, coords in shopper_bases.items()}

    surcharge_df = pd.DataFrame([
        {"Shopper Base": k, "Estimated Surcharge (SLL)": v}
        for k, v in sorted(surcharge_options.items(), key=lambda x: x[1])
    ])
    st.markdown("### Estimated Surcharges")
    st.dataframe(surcharge_df)

    preferred_base = st.selectbox("Preferred Shopper Base", surcharge_df["Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    all_filled = all([name.strip(), contact.strip(), faculty.strip(), year.strip(),
                      item.strip(), qty > 0, max_price >= 0, campus])

    if all_filled:
        if st.button(txt["submit"]):
            # Generate tracking ID
            tracking_id = f"CG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            new_row = {
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
                "Rating": None,
                "Tracking ID": tracking_id
            }

            st.session_state.requests = pd.concat(
                [st.session_state.requests, pd.DataFrame([new_row])],
                ignore_index=True
            )

            save_requests(st.session_state.requests)
            st.success(f"{txt['request_submitted']} Tracking ID: {tracking_id}")
