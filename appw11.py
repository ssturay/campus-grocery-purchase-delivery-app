import streamlit as st
import pandas as pd
import math
from datetime import datetime
from geopy.distance import geodesic
from opencage.geocoder import OpenCageGeocode
import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from google.oauth2.service_account import Credentials
import folium
from streamlit_folium import st_folium
import uuid

# ------------------ LOGIN ------------------
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

if not login():
    st.stop()

# ------------------ API ------------------
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

# ------------------ GOOGLE SHEETS ------------------
def get_google_sheet(sheet_name="GroceryApp"):
    scope = ["https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    return sheet

def load_requests():
    sheet = get_google_sheet()
    df = get_as_dataframe(sheet)
    df = df.dropna(how='all')
    return df

def save_requests(df):
    try:
        sheet = get_google_sheet()
        sheet.clear()
        set_with_dataframe(sheet, df)
    except Exception as e:
        st.error(f"⚠️ Failed to save request: {e}")

# ------------------ SESSION INIT ------------------
if "requests" not in st.session_state:
    try:
        st.session_state.requests = load_requests()
    except Exception:
        st.session_state.requests = pd.DataFrame(columns=[
            "Tracking ID","Requester","Requester Faculty/Department","Requester Year/Level",
            "Requester Contact","Requester Location","Requester Coordinates",
            "Campus","Item","Qty","Max Price (SLL)","Expected Delivery Time",
            "Preferred Shopper Base","Surcharge (SLL)","Assigned Shopper",
            "Shopper Name","Shopper Faculty/Department","Shopper Year/Level",
            "Shopper Contact","Shopper Location","Shopper Coordinates",
            "Timestamp","Status","Rating"
        ])

# ------------------ LANG ------------------
lang_options = {
    "English": {
        "title":"🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱",
        "user_role":"You are a:",
        "requester":"Requester (On Campus)",
        "shopper":"Shopper (Downtown)",
        "name":"Your Name",
        "location_prompt":"📍 Your Campus or Address",
        "submit":"✅ Submit Request",
        "request_submitted":"Your request has been submitted!",
        "available_requests":"🛒 Available Requests to Deliver",
        "accept_request":"📦 Accept This Request",
        "assigned_success":"You've been assigned to deliver request #",
        "no_requests":"No requests available.",
        "campus_select":"🏫 Select your Campus:"
    },
    "Krio": {
        "title":"🛍️🚚 Kampos Gɔsri Buy an Delivri Ap (CamPDApp) 🇸🇱",
        "user_role":"U na:",
        "requester":"Pipul woi wan buy (Kampos pipul)",
        "shopper":"Shopa (Donton)",
        "name":"U Name",
        "location_prompt":"📍 U Kampos or adres",
        "submit":"✅ Sen request",
        "request_submitted":"Dn sen u request!",
        "available_requests":"🛒 Request woi de fɔ delivri",
        "accept_request":"📦 Accept dis request",
        "assigned_success":"U don accept fɔ delivr d request #",
        "no_requests":"No request rynna.",
        "campus_select":"🏫 Selekt u Kampos:"
    }
}

selected_language = st.sidebar.selectbox("Language", ["English","Krio"])
txt = lang_options[selected_language]

# ------------------ SHOPPER BASES ------------------
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

# ------------------ HELPER ------------------
def calculate_surcharge(distance_km):
    base_fee = 1
    per_km_fee = 2
    surcharge = base_fee + (per_km_fee * distance_km)
    return max(100, int(math.ceil(surcharge / 100.0) * 100))  # minimum 100

campus_list = ["FBC","IPAM","COMAHS","Njala FT","MMTU","Limkokwing","UNIMTECH","IAMTECH",
               "FTC","LICCSAL","IMAT","Bluecrest","UNIMAK","EBKUST","Others"]

st.set_page_config(page_title=txt["title"])
st.title(txt["title"])
user_type = st.sidebar.radio(txt["user_role"], [txt["requester"], txt["shopper"]])

# ------------------ REQUESTER FLOW ------------------
if user_type == txt["requester"]:
    st.subheader(txt["submit"])
    name = st.text_input(txt["name"])
    requester_contact = st.text_input("📞 Your Contact Number")
    requester_faculty = st.text_input("Department/Faculty")
    requester_year = st.text_input("Year/Level")
    requester_campus = st.selectbox(txt["campus_select"], campus_list)
    item = st.text_input("Item")
    qty = st.number_input("Quantity", min_value=1, value=1)
    max_price = st.number_input("Max Price (SLL)", min_value=0, value=20000)
    delivery_time = st.time_input("Expected Delivery Time")

    # Use campus name to auto geocode
    lat, lon = geocode_location(requester_campus)
    location_name = requester_campus

    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=15)
        folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
        st_folium(m, width=700, height=450)
    else:
        st.warning("⚠️ Location not found.")

    # Surcharge calculation per shopper base
    surcharge_options = {}
    for base_name, (base_lat, base_lon) in shopper_bases.items():
        dist = geodesic((lat, lon), (base_lat, base_lon)).km
        surcharge_options[base_name] = calculate_surcharge(dist)
    surcharge_df = pd.DataFrame([
        {"Shopper Base": k,"Estimated Surcharge (SLL)": v}
        for k,v in sorted(surcharge_options.items(), key=lambda x:x[1])
    ])
    st.markdown("### Estimated Surcharges")
    st.dataframe(surcharge_df)
    preferred_base = st.selectbox("Preferred Shopper Base", surcharge_df["Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    all_filled = all([name.strip(), requester_contact.strip(), requester_faculty.strip(),
                      requester_year.strip(), item.strip()])
    if all_filled and st.button(txt["submit"]):
        tracking_id = str(uuid.uuid4())[:8].upper()  # short tracking ID
        new_row = {
            "Tracking ID": tracking_id,
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
            "Status": "Pending",
            "Rating": None
        }
        st.session_state.requests = pd.concat([st.session_state.requests, pd.DataFrame([new_row])],
                                              ignore_index=True)
        save_requests(st.session_state.requests)
        st.success(txt["request_submitted"])

# ------------------ SHOPPER FLOW ------------------
elif user_type == txt["shopper"]:
    st.subheader(txt["available_requests"])
    df = st.session_state.requests
    available_df = df[df["Assigned Shopper"]=="Unassigned"]

    if available_df.empty:
        st.info(txt["no_requests"])
    else:
        display_df = available_df[["Tracking ID","Requester","Item","Qty",
                                   "Campus","Preferred Shopper Base","Surcharge (SLL)","Status"]].reset_index(drop=True)
        selected_index = st.selectbox("Select a request to accept", options=display_df.index,
                                      format_func=lambda i: f"{display_df.loc[i,'Tracking ID']} | {display_df.loc[i,'Requester']} | {display_df.loc[i,'Item']} | {display_df.loc[i,'Qty']} pcs | {display_df.loc[i,'Surcharge (SLL)']} SLL")

        # Show requester location on map
        tracking_id = display_df.loc[selected_index, "Tracking ID"]
        requester_coords = available_df.loc[available_df["Tracking ID"]==tracking_id,"Requester Coordinates"].values[0]
        if requester_coords:
            lat, lon = map(float, requester_coords.split(","))
            m = folium.Map(location=[lat, lon], zoom_start=15)
            folium.Marker([lat, lon], tooltip="Requester Location").add_to(m)
            st_folium(m, width=700, height=450)

        if st.button(txt["accept_request"]):
            st.session_state.requests.loc[st.session_state.requests["Tracking ID"]==tracking_id, "Assigned Shopper"] = "Accepted"
            save_requests(st.session_state.requests)
            st.success(f"{txt['assigned_success']}{tracking_id}")
