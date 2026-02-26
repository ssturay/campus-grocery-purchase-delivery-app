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
# LANGUAGE TOGGLE
# =========================
language = st.sidebar.selectbox("Language / Lanɡwij", ["English", "Krio"])

def t(en, kr):
    return en if language == "English" else kr

# =========================
# GOOGLE SHEET CONNECTION
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
    df = st.session_state.requests.copy()
    # Convert all values to string to avoid InvalidJSONError
    df = df.fillna("").astype(str)
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

# =========================
# SESSION INIT
# =========================
if "requests" not in st.session_state:
    st.session_state.requests = pd.DataFrame(columns=[
        "Tracking ID","Requester","Requester Contact","Campus",
        "Item","Qty","Max Price (SLL)","Expected Delivery Time",
        "Preferred Shopper Base","Surcharge (SLL)",
        "Assigned Shopper","Shopper Name",
        "Timestamp","Status","Rating",
        "Accepted Time","Delivered Time","Delivery Duration (mins)",
        "Platform Fee (SLL)","Payment Type"
    ])
    load_requests_from_gsheet()

# =========================
# LOGIN (GENERAL)
# =========================
def login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.subheader(t("User Login", "Usa Login"))
    with st.form("Login"):
        u = st.text_input(t("Username", "Usa nem"))
        p = st.text_input(t("Password", "Paswod"), type="password")
        if st.form_submit_button(t("Login", "Login")):
            if u == st.secrets["credentials"]["username"] and p == st.secrets["credentials"]["password"]:
                st.session_state.authenticated = True
                st.success(t("Login successful!", "Login don wok!"))
            else:
                st.error(t("Invalid credentials", "Login no correct"))
    if not st.session_state.authenticated:
        st.stop()

login()

# =========================
# ADMIN LOGIN
# =========================
def admin_login():
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    if st.session_state.admin_authenticated:
        return True
    st.warning(t("Admin access only", "Na admin nomo get akses"))
    with st.form("Admin Login"):
        u = st.text_input(t("Admin Username", "Admin nem"))
        p = st.text_input(t("Admin Password", "Admin paswod"), type="password")
        if st.form_submit_button(t("Login as Admin", "Login lek Admin")):
            if u == st.secrets["admin_credentials"]["username"] and p == st.secrets["admin_credentials"]["password"]:
                st.session_state.admin_authenticated = True
                st.success(t("Admin login successful!", "Admin login don wok!"))
            else:
                st.error(t("Invalid admin credentials", "Admin login no correct"))
    if not st.session_state.admin_authenticated:
        st.stop()

# =========================
# APP TITLE
# =========================
st.title(
    "🛍️🚚 Campus Grocery Purchase & Delivery App (CamPDApp) 🇸🇱"
    if language == "English"
    else "🛍️🚚 Kampus Makit Bay & Dilivri Ap (CamPDApp) 🇸🇱"
)

# =========================
# ROLE SELECTOR
# =========================
user_type = st.sidebar.radio(
    t("You are a:", "Yu na:"),
    [t("Requester", "Pesin we dae oda"), t("Shopper", "Pesin we dae bay"), "Admin"]
)

# =========================
# ADMIN DASHBOARD
# =========================
if user_type == "Admin":
    admin_login()
    st.title(t("Admin Dashboard", "Admin Dashbod"))

    df = st.session_state.requests
    if df.empty:
        st.info(t("No requests yet.", "Natin no dae yet."))
        st.stop()

    total_requests = len(df)
    pending = len(df[df["Status"]=="Pending"])
    assigned = len(df[df["Status"]=="Assigned"])
    delivered = len(df[df["Status"]=="Delivered"])
    total_surcharge = df["Surcharge (SLL)"].astype(float).sum()
    total_platform_fee = df["Platform Fee (SLL)"].astype(float).sum()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric(t("Total Requests", "Ol oda"), total_requests)
    col2.metric(t("Pending", "Stil dae"), pending)
    col3.metric(t("Assigned", "Don tek"), assigned)
    col4.metric(t("Delivered", "Don dɔn"), delivered)
    col5.metric(t("Total Surcharge", "Ol Surcharge (SLL)"), total_surcharge)
    col6.metric(t("Platform Fee", "Platform Fee (SLL)"), total_platform_fee)

    status_filter = st.selectbox(
        t("Filter by Status", "Filta wit Status"),
        [t("All", "Ol"), "Pending", "Assigned", "Delivered"]
    )
    filtered_df = df if status_filter==t("All","Ol") else df[df["Status"]==status_filter]
    st.dataframe(filtered_df)

    st.subheader(t("Update Any Request", "Change eni oda"))
    update_id = st.text_input(t("Tracking ID", "Trak ID"))
    new_status = st.selectbox(t("New Status", "New Status"), ["Pending","Assigned","Delivered"])
    if st.button(t("Update Status", "Update Status")):
        if update_id in df["Tracking ID"].values:
            idx = df.index[df["Tracking ID"]==update_id][0]
            st.session_state.requests.at[idx,"Status"] = new_status
            save_requests_to_gsheet()
            st.success(t("Status updated!", "Status don change!"))
        else:
            st.error(t("Invalid Tracking ID", "Trak ID no correct"))
    st.stop()

# =========================
# CAMPUS & SHOPPER BASES
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
    return int(math.ceil(surcharge/100.0)*100)

# =========================
# REQUESTER FLOW
# =========================
if user_type == t("Requester","Pesin we dae oda"):
    st.subheader(t("Submit Request","Put oda"))

    name = st.text_input(t("Your Name","Yu nem"))
    contact = st.text_input(t("Contact","Nomba"))
    campus = st.selectbox(t("Campus","Kampus"), list(campus_coordinates.keys()))
    item = st.text_input(t("Item","Wetin yu wan bay"))
    qty = st.number_input(t("Quantity","Ow moch"), min_value=1, value=1)
    max_price = st.number_input(t("Max Price (SLL)","Max moni"), min_value=0, value=20000)
    delivery_time = st.time_input(t("Expected Delivery Time","Ten we yu wan am"))

    # Payment Type
    payment_type = st.selectbox(t("Payment Type","Fom fo pay"),
                                [t("Cash on Delivery","Moni cash"),
                                 t("Mobile Money","Mobile moni"),
                                 t("Card","Card")])

    lat, lon = campus_coordinates[campus]
    m = folium.Map(location=[lat, lon], zoom_start=14)
    folium.Marker([lat, lon], tooltip=t("Campus","Kampus")).add_to(m)
    for base_name,(base_lat,base_lon) in shopper_bases.items():
        folium.Marker([base_lat,base_lon], tooltip=base_name, icon=folium.Icon(color='green')).add_to(m)
    st_folium(m,width=700,height=400)

    surcharge_options = {}
    for base_name,(base_lat,base_lon) in shopper_bases.items():
        dist = geodesic((lat,lon),(base_lat,base_lon)).km
        surcharge_options[base_name] = calculate_surcharge(dist)

    surcharge_df = pd.DataFrame([{"Shopper Base":k, t("Estimated Surcharge (SLL)","Moni fo dilivri"):v}
                                 for k,v in sorted(surcharge_options.items(), key=lambda x:x[1])])
    st.dataframe(surcharge_df)

    preferred_base = st.selectbox(t("Preferred Shopper Base","Udat pesin fo bay"), surcharge_df["Shopper Base"])
    selected_surcharge = surcharge_options[preferred_base]

    if st.button(t("Submit Request","Send oda")):
        tracking_id = str(uuid.uuid4())[:8]
        platform_fee = int(selected_surcharge*0.10)
        new_row = {
            "Tracking ID":tracking_id,
            "Requester":name,
            "Requester Contact":contact,
            "Campus":campus,
            "Item":item,
            "Qty":qty,
            "Max Price (SLL)":max_price,
            "Expected Delivery Time":delivery_time.strftime("%H:%M"),
            "Preferred Shopper Base":preferred_base,
            "Surcharge (SLL)":selected_surcharge,
            "Assigned Shopper":"Unassigned",
            "Shopper Name":"",
            "Timestamp":datetime.utcnow().isoformat(),
            "Status":"Pending",
            "Rating":"",
            "Accepted Time":"",
            "Delivered Time":"",
            "Delivery Duration (mins)":"",
            "Platform Fee (SLL)":platform_fee,
            "Payment Type":payment_type
        }
        st.session_state.requests = pd.concat([st.session_state.requests,pd.DataFrame([new_row])],ignore_index=True)
        save_requests_to_gsheet()
        st.success(f"{t('Tracking ID','Trak ID')}: {tracking_id}")

# =========================
# SHOPPER FLOW
# =========================
elif user_type == t("Shopper","Pesin we dae bay"):
    st.subheader(t("Available Requests","Oda we dae"))

    shopper_name = st.text_input(t("Your Name","Yu nem"))

    df = st.session_state.requests

    # Show only unassigned jobs
    available_df = df[df["Assigned Shopper"]=="Unassigned"]

    if available_df.empty:
        st.info(t("No requests available.","Natin no dae fo tek."))
    else:
        st.dataframe(available_df)

        track_id_input = st.text_input(t("Tracking ID","Trak ID"))

        if st.button(t("Accept Request","Tek dis oda")):
            if track_id_input in available_df["Tracking ID"].values:
                idx = df.index[df["Tracking ID"]==track_id_input][0]

                st.session_state.requests.at[idx,"Assigned Shopper"]="Accepted"
                st.session_state.requests.at[idx,"Shopper Name"]=shopper_name
                st.session_state.requests.at[idx,"Status"]="Assigned"
                st.session_state.requests.at[idx,"Accepted Time"]=datetime.utcnow().isoformat()

                save_requests_to_gsheet()
                st.success(t("Assigned!","Yu don tek am!"))

                st.experimental_rerun()

    # =========================
    # MY DELIVERIES (FIXED)
    # =========================
    st.subheader(t("My Deliveries","Mi dilivri dem"))

    df = st.session_state.requests
    my_jobs = df[df["Shopper Name"]==shopper_name]

    if my_jobs.empty:
        st.info(t("You have not accepted any deliveries yet.","Yu neva tek oda yet."))
    else:
        st.dataframe(my_jobs)

        update_id = st.text_input(t("Tracking ID to update","Trak ID fo change"))
        new_status = st.selectbox(t("Status","Status"),["Assigned","Delivered"])

        if st.button(t("Update Status","Update Status")):
            if update_id in my_jobs["Tracking ID"].values:
                idx = df.index[df["Tracking ID"]==update_id][0]

                st.session_state.requests.at[idx,"Status"]=new_status

                if new_status=="Delivered":
                    st.session_state.requests.at[idx,"Delivered Time"]=datetime.utcnow().isoformat()

                    accepted_time_str = st.session_state.requests.at[idx,"Accepted Time"]
                    if accepted_time_str:
                        accepted_time = datetime.fromisoformat(accepted_time_str)
                        duration = (datetime.utcnow()-accepted_time).total_seconds()/60
                        st.session_state.requests.at[idx,"Delivery Duration (mins)"]=int(duration)

                save_requests_to_gsheet()
                st.success(t("Updated!","Don change!"))

    # =========================
    # SHOPPER PERFORMANCE
    # =========================
    st.subheader(t("My Performance","Mi wok performans"))

    completed_jobs = my_jobs[my_jobs["Status"]=="Delivered"]

    if not completed_jobs.empty:
        avg_rating = pd.to_numeric(completed_jobs["Rating"], errors="coerce").mean()

        col1, col2 = st.columns(2)
        col1.metric(t("Completed Deliveries","Oda dem we yu don don"), len(completed_jobs))
        col2.metric(t("Average Rating ⭐","Avaraj rate ⭐"),
                    f"{avg_rating:.2f}" if not math.isnan(avg_rating) else "N/A")
    else:
        st.info(t("No completed deliveries yet.","Yu neva don dilivri yet."))
