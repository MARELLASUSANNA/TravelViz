# app.py
import streamlit as st
import json
import bcrypt
import os
from PIL import Image
from base64 import b64encode
from datetime import datetime, date
from typing import Optional, Tuple
from collections import defaultdict
import pandas as pd
import plotly.express as px
import pydeck as pdk

# ---------------------- Page Config ----------------------
st.set_page_config(
    page_title="TravelViz",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------- Files & Folders ----------------------
if not os.path.exists("profile_pics"):
    os.makedirs("profile_pics")

USERS_FILE = "users.json"
TRIPS_FILE = "trips.json"

# ---------------------- Persistence Helpers ----------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            try:
                data = json.load(f)
                for user in list(data.keys()):
                    if isinstance(data[user], str):
                        data[user] = {
                            "password": data[user],
                            "profile_pic": None,
                            "role": "user",
                            "bio": "",
                            "favorite_destination": "",
                            "goals": ""
                        }
                    data[user].setdefault("role", "user")
                    data[user].setdefault("profile_pic", None)
                    data[user].setdefault("bio", "")
                    data[user].setdefault("favorite_destination", "")
                    data[user].setdefault("goals", "")
                return data
            except json.JSONDecodeError:
                return {}
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_trips():
    if os.path.exists(TRIPS_FILE):
        with open(TRIPS_FILE, "r") as f:
            try:
                data = json.load(f)
                for uname, trs in list(data.items()):
                    new_trs = []
                    for t in trs:
                        t.setdefault("destination", "")
                        t.setdefault("start_date", "")
                        t.setdefault("end_date", "")
                        t.setdefault("notes", "")
                        t.setdefault("expenses", [])
                        t.setdefault("checklist", [])
                        t.setdefault("lat", None)
                        t.setdefault("lon", None)
                        new_trs.append(t)
                    data[uname] = new_trs
                return data
            except json.JSONDecodeError:
                return {}
    return {}

def save_trips(trips):
    with open(TRIPS_FILE, "w") as f:
        json.dump(trips, f, indent=2)

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# ---------------------- Badges ----------------------
def get_user_badge(trip_count: int) -> Tuple[str, int, Optional[int]]:
    tiers = [
        ("New Traveler", 0),
        ("Explorer", 1),
        ("Adventurer", 3),
        ("Globetrotter", 6),
        ("World Citizen", 10),
    ]
    current_badge = tiers[0][0]
    level_index = 0
    next_threshold = tiers[1][1]

    for i in range(len(tiers)):
        name, threshold = tiers[i]
        if trip_count >= threshold:
            current_badge = name
            level_index = i
            next_threshold = tiers[i + 1][1] if i + 1 < len(tiers) else None
        else:
            break
    return current_badge, level_index, next_threshold

# ---------------------- Styling ----------------------
def add_custom_css(dark_mode):
    bg_color = "#0e1117" if dark_mode else "#f7fafc"
    text_color = "#eaecee" if dark_mode else "#0f172a"
    input_bg = "#1c1f26" if dark_mode else "#ffffff"
    input_text = "#f1f5f9" if dark_mode else "#0f172a"
    placeholder = "#9ca3af" if dark_mode else "#64748b"
    card_bg = "rgba(255,255,255,0.05)" if dark_mode else "#ffffff"
    card_shadow = "0 6px 24px rgba(0,0,0,0.35)" if dark_mode else "0 6px 24px rgba(0,0,0,0.12)"
    sub_text = "#bdbdbd" if dark_mode else "#475569"

    st.markdown(f"""
    <style>
    html, body, [data-testid="stAppViewContainer"] {{
        background: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
    }}
    /* Sidebar */
    [data-testid="stSidebar"] > div:first-child {{
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 45%, #7c3aed 100%);
        color: white !important;
    }}
    [data-testid="stSidebar"] * {{ color: white !important; }}

    /* Form labels */
    label, .stTextInput label, .stTextArea label, .stSelectbox label {{
        color: {text_color} !important;
        font-weight: 600 !important;
    }}

    /* Input fields */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border-radius: 10px !important;
    }}

    /* Placeholder text */
    ::placeholder {{
        color: {placeholder} !important;
        opacity: 0.8;
    }}

    /* Buttons */
    .stButton>button {{
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600 !important;
        border: 0 !important;
        background: linear-gradient(90deg, #22c55e, #06b6d4) !important;
        color: white !important;
        box-shadow: 0 8px 20px rgba(6, 182, 212, 0.35) !important;
    }}

    .tv-card {{
        background: {card_bg};
        border-radius: 18px;
        padding: 18px 18px 16px 18px;
        box-shadow: {card_shadow};
    }}

    .tv-footer {{ text-align:center; margin-top: 36px; padding: 16px 6px; color: {sub_text}; }}
    </style>
    """, unsafe_allow_html=True)


# ---------------------- Helpers ----------------------
def display_profile_card(username, profile_img_path, badge_name="Traveler"):
    if profile_img_path and os.path.exists(profile_img_path):
        with open(profile_img_path, "rb") as img_file:
            img_base64 = b64encode(img_file.read()).decode()
        img_src = f"data:image/png;base64,{img_base64}"
    else:
        img_src = f"https://i.pravatar.cc/100?u={username}"

    st.markdown(f"""
    <div class="profile-card" style="background:rgba(255,255,255,0.08);padding:20px;border-radius:12px;text-align:center;">
        <img src="{img_src}" style="border-radius:50%;width:90px;height:90px;margin-bottom:10px;"/>
        <h3>{username}</h3>
        <span class="badge">🏅 {badge_name}</span>
    </div>
    """, unsafe_allow_html=True)

def stat_card(title: str, value: str, emoji: str = "📌"):
    st.markdown(f"""
    <div class="tv-card">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
            <div style="font-size:1.25rem">{emoji}</div>
            <div style="font-weight:700; opacity:.85">{title}</div>
        </div>
        <div style="font-size:1.6rem; font-weight:800; line-height:1.1;">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def hero(title: str, subtitle: str):
    st.markdown(f"""
    <div class="tv-hero" style="text-align:center;padding:30px;background:linear-gradient(135deg,#0ea5e9,#7c3aed);border-radius:18px;">
        <h1 style="color:white;">{title}</h1>
        <p style="color:white;opacity:.85;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def chatbot_response(user_input):
    responses = {
        "hello": "Hello! Welcome to TravelViz. How can I help you today?",
        "what is travelviz": "TravelViz is your travel insights dashboard — track destinations, explore data, and plan trips!",
        "features": "We have login/signup, dashboard, insights, trip planner, interactive map, profile management, and an admin panel.",
        "bye": "Safe travels! 🌍✈",
    }
    for key in responses:
        if key in user_input.lower():
            return responses[key]
    return "I'm not sure about that, but I can tell you more about TravelViz!"

def parse_date_str(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def trigger_reminders(username: str, trips_dict: dict):
    today = date.today()
    for t in trips_dict.get(username, []):
        d = parse_date_str(t.get("start_date", ""))
        if d is None: continue
        days_left = (d - today).days
        if 0 <= days_left <= 3:
            st.toast(f"⏰ Reminder: Your trip to {t.get('destination','(unknown)')} starts in {days_left} day(s)!")

# ---------------------- Minimal fallback coords ----------------------
FALLBACK_CENTROIDS = {
    "france": (46.2, 2.2),
    "paris": (48.85, 2.35),
    "india": (20.59, 78.96),
    "usa": (37.09, -95.71),
    "japan": (36.20, 138.25),
    "tokyo": (35.67, 139.65),
}
def fallback_coords_for_destination(dest: str):
    key = dest.strip().lower()
    for k, v in FALLBACK_CENTROIDS.items():
        if k in key:
            return v
    return None

# ---------------------- Session ----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = "user"
    st.session_state.dark_mode = False

users = load_users()
trips = load_trips()

# ---------------------- Sidebar ----------------------
with st.sidebar:
    st.markdown("### ✈ TravelViz")
    st.caption("Plan • Track • Visualize")
    st.markdown("---")

    if st.session_state.logged_in:
        st.write(f"*User:* {st.session_state.username}")
        st.write(f"*Role:* {st.session_state.role}")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = "user"
            st.rerun()

    dark_mode = st.toggle("🌙 Dark Mode", key="dark_mode_toggle")
    st.session_state.dark_mode = dark_mode

    st.markdown("---")

    if not st.session_state.logged_in:
        menu = st.selectbox("Menu", ["Login", "Sign Up"])
    else:
        options = ["Home", "Dashboard", "Insights", "Trip Planner", "Map", "Edit Profile", "Settings", "Contact", "Chatbot"]
        if st.session_state.role == "admin":
            options.append("Admin Panel")
        menu = st.selectbox("Navigate", options)

# Inject CSS
add_custom_css(st.session_state.dark_mode)

# ---------------------- PAGES ----------------------
# (Sign Up, Login, Home, Dashboard, Insights, Trip Planner, Map, Edit Profile, Settings, Contact, Chatbot, Admin Panel) 
# ---- FULL IMPLEMENTATION CONTINUES EXACTLY AS BEFORE ----


# ---------------------- SIGN UP ----------------------
if not st.session_state.logged_in and menu == "Sign Up":
    hero("Create your TravelViz account", "Join and start building your travel story.")
    st.markdown("")

    with st.container():
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            new_user = st.text_input("Username", key="signup_user")
            new_pass = st.text_input("Password", type='password', key="signup_pass")
            profile_image = st.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"])
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("Sign Up"):
                if new_user in users:
                    st.warning("Username already exists.")
                elif new_user == "" or new_pass == "":
                    st.warning("Please enter both username and password.")
                else:
                    img_filename = None
                    if profile_image:
                        img_filename = f"profile_pics/{new_user}.png"
                        Image.open(profile_image).save(img_filename)
                    users[new_user] = {
                        "password": hash_password(new_pass),
                        "profile_pic": img_filename,
                        "role": "user",
                        "bio": "",
                        "favorite_destination": "",
                        "goals": ""
                    }
                    save_users(users)
                    st.success("Account created successfully! You can now login.")
                    st.balloons()
        with col_b:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            st.markdown("*Why TravelViz?*")
            st.markdown("- Plan trips with checklists")
            st.markdown("- Track expenses easily")
            st.markdown("- Visualize your journeys on a map")
            st.markdown("- Earn badges as you explore")
            st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- LOGIN ----------------------
elif not st.session_state.logged_in and menu == "Login":
    hero("Welcome back 👋", "Log in to continue your adventures.")
    st.markdown("")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type='password', key="login_pass")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Login"):
        if username in users and check_password(password, users[username]['password']):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = users[username].get("role", "user")
            st.success(f"Welcome, {username} 👋")
            trigger_reminders(username, trips)
            st.balloons()
            st.rerun()
        else:
            st.error("Invalid credentials.")

# ---------------------- HOME ----------------------
elif st.session_state.logged_in and menu == "Home":
    username = st.session_state.username
    profile_img_path = users[username].get('profile_pic')

    user_trips = trips.get(username, [])
    badge_name, _, next_threshold = get_user_badge(len(user_trips))

    display_profile_card(username, profile_img_path, badge_name)

    # Hero
    hero("🌍 TravelViz", "Track destinations • Explore data • Plan smarter journeys")

    # Quick stats
    upcoming_count = 0
    today = date.today()
    for t in user_trips:
        d = parse_date_str(t.get("start_date", ""))
        if d and d >= today:
            upcoming_count += 1

    total_trips = len(user_trips)
    remaining = max(0, (next_threshold - total_trips) if next_threshold is not None else 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        stat_card("Trips Logged", f"{total_trips}", "🧳")
    with col2:
        stat_card("Upcoming Trips", f"{upcoming_count}", "📅")
    with col3:
        stat_card("Next Badge Progress", f"{'Maxed 🎉' if next_threshold is None else f'{remaining} to go'}", "🏅")

    trigger_reminders(username, trips)

    # Profile summary
    u = users.get(username, {})
    st.markdown("")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    st.subheader("👤 Your Profile")
    colA, colB = st.columns(2)
    with colA:
        st.markdown(f"*Badge:* :medal: {badge_name}")
        st.markdown(f"*Trips Logged:* {len(user_trips)}")
        if next_threshold is not None:
            st.markdown(f"*Next Badge In:* {remaining} trip(s)")
        else:
            st.markdown("*Badge Status:* World Citizen 🎉")
    with colB:
        st.markdown(f"*Favorite Destination:* {u.get('favorite_destination','') or '—'}")
        st.markdown(f"*Bio:* {u.get('bio','') or '—'}")
        st.markdown(f"*Travel Goals:* {u.get('goals','') or '—'}")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- DASHBOARD ----------------------
elif st.session_state.logged_in and menu == "Dashboard":
    username = st.session_state.username
    profile_img_path = users[username].get('profile_pic')

    user_trips = trips.get(username, [])
    badge_name, _, _ = get_user_badge(len(user_trips))
    display_profile_card(username, profile_img_path, badge_name)

    st.header("📊 TravelViz Dashboard")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    st.markdown("""
    <iframe title="global tourism" width="100%" height="520"
    src="https://app.powerbi.com/view?r=eyJrIjoiZjNmMmViOGUtMDYyNi00NTFkLTkzNTMtN2JkYWQyM2FjN2VkIiwidCI6IjdkOTk1NThlLTFhMjMtNDVlMi04NzNhLTM4ODNjMjc4NjNmOCJ9"
    frameborder="0" allowFullScreen="true"></iframe>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- INSIGHTS ----------------------
elif st.session_state.logged_in and menu == "Insights":
    st.header("📈 Insights & Data")

    username = st.session_state.username
    user_trips = trips.get(username, [])

    # Summary metrics
    total_trips = len(user_trips)
    dest_counts = defaultdict(int)
    for t in user_trips:
        dest_counts[t.get("destination","").strip()] += 1
    most_visited = max(dest_counts.items(), key=lambda x: x[1])[0] if dest_counts else "—"

    # Total expenses across all trips
    total_expenses = 0.0
    expenses_rows = []
    for t in user_trips:
        trip_name = t.get("destination","(unknown)")
        trip_date = parse_date_str(t.get("start_date","")) or date.today()
        trip_total = 0.0
        for e in t.get("expenses", []):
            amt = float(e.get("amount", 0) or 0)
            trip_total += amt
            expenses_rows.append({
                "destination": trip_name,
                "date": trip_date,
                "category": e.get("category",""),
                "amount": amt
            })
        total_expenses += trip_total

    col1, col2, col3 = st.columns(3)
    with col1: stat_card("Total Trips", f"{total_trips}", "🧭")
    with col2: stat_card("Most Visited", most_visited, "📍")
    with col3: stat_card("Total Expenses", f"${total_expenses:,.2f}", "💳")

    st.markdown("")

    # Expenses over trips (bar chart)
    if expenses_rows:
        st.subheader("💸 Expenses per Trip")
        exp_df = pd.DataFrame(expenses_rows)
        per_trip = exp_df.groupby("destination", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        fig_bar = px.bar(
            per_trip, x="destination", y="amount",
            labels={"amount":"Total Amount (USD)","destination":"Trip"},
            title="Expenses per Trip"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # expenses over time (line) — cumulative by date
        st.subheader("📈 Expenses Over Time (Cumulative)")
        daily = exp_df.groupby("date", as_index=False)["amount"].sum().sort_values("date")
        daily["cumulative"] = daily["amount"].cumsum()
        fig_line = px.line(daily, x="date", y="cumulative", markers=True, title="Cumulative Expenses Over Time")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No expenses recorded yet. Add expenses in Trip Planner to see charts.")

    st.markdown("---")

    # World map of visited destinations (pydeck)
    st.subheader("🗺 Visited Destinations Map")
    map_rows = []
    for t in user_trips:
        dest = t.get("destination","")
        lat = t.get("lat")
        lon = t.get("lon")
        if lat is None or lon is None:
            coords = fallback_coords_for_destination(dest)
            if coords:
                lat, lon = coords
        try:
            lat_f = float(lat) if lat is not None else None
            lon_f = float(lon) if lon is not None else None
        except Exception:
            lat_f, lon_f = None, None
        if lat_f is not None and lon_f is not None:
            map_rows.append({"destination": dest, "lat": lat_f, "lon": lon_f, "start_date": t.get("start_date","")})

    if map_rows:
        map_df = pd.DataFrame(map_rows)
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position=["lon", "lat"],
            get_fill_color=[255, 140, 0],
            get_radius=50000,
            radius_scale=20,
            pickable=True
        )
        center = [map_df["lon"].mean(), map_df["lat"].mean()]
        view_state = pdk.ViewState(latitude=center[1], longitude=center[0], zoom=1.5, pitch=0)
        deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text":"{destination}\n{start_date}"})
        st.pydeck_chart(deck)
    else:
        st.info("No geocoded trips to show on map. When adding a trip, specify latitude & longitude (optional) or use a recognizable destination name (e.g., 'Paris').")

    st.caption("Tip: Add *Latitude* & *Longitude* in Trip Planner for precise map pins.")

# ---------------------- TRIP PLANNER ----------------------
elif st.session_state.logged_in and menu == "Trip Planner":
    username = st.session_state.username
    user_trips = trips.get(username, [])

    st.header("🗓 Plan Your Trip")
    with st.container():
        col_left, col_right = st.columns([2,1])
        with col_left:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            destination = st.text_input("Destination")
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            notes = st.text_area("Notes")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_right:
            st.markdown('<div class="tv-card">', unsafe_allow_html=True)
            st.markdown("*Optional Coordinates*")
            col_lat, col_lon = st.columns(2)
            with col_lat:
                lat_input = st.text_input("Latitude", key="trip_lat")
            with col_lon:
                lon_input = st.text_input("Longitude", key="trip_lon")
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button("💾 Save Trip"):
        if destination:
            lat_val = None
            lon_val = None
            try:
                lat_val = float(lat_input) if lat_input not in (None, "") else None
                lon_val = float(lon_input) if lon_input not in (None, "") else None
            except Exception:
                lat_val, lon_val = None, None

            new_trip = {
                "destination": destination,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "notes": notes,
                "expenses": [],
                "checklist": [],
                "lat": lat_val,
                "lon": lon_val
            }
            user_trips.append(new_trip)
            trips[username] = user_trips
            save_trips(trips)
            st.success(f"Trip to {destination} saved!")
            trigger_reminders(username, trips)
            st.rerun()
        else:
            st.warning("Please enter a destination.")

    # Display Trips
    if user_trips:
        st.subheader("📋 Your Trips")
        df = pd.DataFrame([{
            "Destination": t["destination"],
            "Start Date": t["start_date"],
            "End Date": t["end_date"],
            "Notes": t["notes"]
        } for t in user_trips])
        st.markdown('<div class="tv-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        badge_name, _, next_threshold = get_user_badge(len(user_trips))
        st.markdown(
            f"*Current Badge:* :medal: {badge_name} • *Trips:* {len(user_trips)}"
            + (f" • *Next in:* {max(0, next_threshold-len(user_trips))} trip(s)" if next_threshold is not None else " • *Max badge achieved!*")
        )

        trigger_reminders(username, trips)

        for i, trip in enumerate(user_trips):
            st.markdown("---")
            top1, top2, top3 = st.columns([5,2,1])
            with top1:
                st.markdown(f"### ✈ {trip['destination']}  \n`{trip['start_date']} → {trip['end_date']}`")
            with top2:
                d = parse_date_str(trip.get("start_date",""))
                if d:
                    days_left = (d - date.today()).days
                    if days_left >= 0:
                        st.caption(f"⏳ Starts in *{days_left}* day(s)")
                    else:
                        st.caption("✅ Trip started/finished")
            with top3:
                if st.button("🗑 Delete Trip", key=f"del_trip_{i}"):
                    user_trips.pop(i)
                    trips[username] = user_trips
                    save_trips(trips)
                    st.rerun()

            # Checklist
            with st.expander(f"✅ Travel Checklist — {trip['destination']}"):
                ci1, ci2 = st.columns([4,1])
                with ci1:
                    new_item_text = st.text_input("Add checklist item", key=f"chk_add_{i}")
                with ci2:
                    if st.button("Add", key=f"chk_btn_{i}"):
                        if new_item_text.strip():
                            trip["checklist"].append({"text": new_item_text.strip(), "done": False})
                            trips[username] = user_trips
                            save_trips(trips)
                            st.rerun()
                        else:
                            st.warning("Please type an item first.")

                if trip["checklist"]:
                    for j, item in enumerate(trip["checklist"]):
                        colX, colY, colZ = st.columns([6, 2, 1])
                        with colX:
                            new_done = st.checkbox(item["text"], value=item.get("done", False), key=f"chk_item_{i}_{j}")
                            if new_done != item.get("done", False):
                                item["done"] = new_done
                                trips[username] = user_trips
                                save_trips(trips)
                        with colY:
                            edited = st.text_input("Update item text", value=item["text"], key=f"edit_text_{i}_{j}")
                            if st.button("Save", key=f"save_text_{i}_{j}"):
                                item["text"] = edited.strip() or item["text"]
                                trips[username] = user_trips
                                save_trips(trips)
                                st.success("Item updated.")
                                st.rerun()
                        with colZ:
                            if st.button("🗑", key=f"del_chk_{i}_{j}"):
                                trip["checklist"].pop(j)
                                trips[username] = user_trips
                                save_trips(trips)
                                st.rerun()
                else:
                    st.info("No checklist items yet. Add one above.")

            # Expenses management
            with st.expander(f"💰 Manage Expenses — {trip['destination']}"):
                category = st.selectbox("Category", ["Flights", "Hotels", "Food", "Activities", "Misc"], key=f"cat_{i}")
                desc = st.text_input("Description", key=f"desc_{i}")
                amount = st.number_input("Amount", min_value=0.0, step=0.01, key=f"amt_{i}")
                if st.button("Add Expense", key=f"add_exp_{i}"):
                    if desc and amount > 0:
                        trip["expenses"].append({
                            "category": category,
                            "description": desc,
                            "amount": amount
                        })
                        trips[username] = user_trips
                        save_trips(trips)
                        st.rerun()
                    else:
                        st.warning("Enter a description and amount.")

                if trip["expenses"]:
                    exp_df = pd.DataFrame(trip["expenses"])
                    st.dataframe(exp_df, use_container_width=True)
                    for j, exp in enumerate(trip["expenses"]):
                        colA, colB, colC = st.columns([2,2,1])
                        with colA:
                            st.write(f"{exp['category']}** - {exp['description']}")
                        with colB:
                            st.write(f"${exp['amount']:.2f}")
                        with colC:
                            if st.button("✏ Edit", key=f"edit_exp_{i}_{j}"):
                                new_cat = st.selectbox(
                                    "Edit Category",
                                    ["Flights", "Hotels", "Food", "Activities", "Misc"],
                                    index=["Flights", "Hotels", "Food", "Activities", "Misc"].index(exp["category"]),
                                    key=f"new_cat_{i}_{j}"
                                )
                                new_desc = st.text_input("Edit Description", value=exp["description"], key=f"new_desc_{i}_{j}")
                                new_amt = st.number_input("Edit Amount", min_value=0.0, step=0.01, value=exp["amount"], key=f"new_amt_{i}_{j}")
                                if st.button("Save Changes", key=f"save_edit_{i}_{j}"):
                                    exp["category"] = new_cat
                                    exp["description"] = new_desc
                                    exp["amount"] = new_amt
                                    trips[username] = user_trips
                                    save_trips(trips)
                                    st.success("Expense updated!")
                                    st.rerun()
                            if st.button("🗑 Delete", key=f"del_exp_{i}_{j}"):
                                trip["expenses"].pop(j)
                                trips[username] = user_trips
                                save_trips(trips)
                                st.rerun()
    else:
        st.info("No trips planned yet. Add one above.")

# ---------------------- MAP (menu) ----------------------
elif st.session_state.logged_in and menu == "Map":
    st.header("🗺 Interactive Map - Your Visits")
    username = st.session_state.username
    user_trips = trips.get(username, [])

    map_rows = []
    for t in user_trips:
        dest = t.get("destination","")
        lat = t.get("lat")
        lon = t.get("lon")
        if lat is None or lon is None:
            coords = fallback_coords_for_destination(dest)
            if coords:
                lat, lon = coords
        try:
            lat_f = float(lat) if lat is not None else None
            lon_f = float(lon) if lon is not None else None
        except Exception:
            lat_f, lon_f = None, None
        if lat_f is not None and lon_f is not None:
            map_rows.append({"destination": dest, "lat": lat_f, "lon": lon_f, "start_date": t.get("start_date","")})

    if map_rows:
        map_df = pd.DataFrame(map_rows)
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position=["lon", "lat"],
            get_fill_color=[40, 160, 255],
            get_radius=50000,
            radius_scale=20,
            pickable=True
        )
        center = [map_df["lon"].mean(), map_df["lat"].mean()]
        view_state = pdk.ViewState(latitude=center[1], longitude=center[0], zoom=1.5, pitch=0)
        deck = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text":"{destination}\n{start_date}"})
        st.pydeck_chart(deck)
    else:
        st.info("No geocoded trips to show. Add lat/lon when creating a trip or use a common destination name.")

# ---------------------- EDIT PROFILE ----------------------
elif st.session_state.logged_in and menu == "Edit Profile":
    username = st.session_state.username
    profile_img_path = users[username].get('profile_pic')

    user_trips = trips.get(username, [])
    badge_name, _, next_threshold = get_user_badge(len(user_trips))
    display_profile_card(username, profile_img_path, badge_name)

    st.header("✏ Edit Profile")
    col1, col2 = st.columns([1,2])

    with col1:
        st.markdown('<div class="tv-card">', unsafe_allow_html=True)
        new_profile_image = st.file_uploader("Upload New Profile Picture", type=["png", "jpg", "jpeg"])
        if st.button("Update Profile Picture"):
            if new_profile_image:
                img_filename = f"profile_pics/{username}.png"
                Image.open(new_profile_image).save(img_filename)
                users[username]['profile_pic'] = img_filename
                save_users(users)
                st.success("Profile Picture Updated!")
                st.rerun()
            else:
                st.warning("Please upload an image.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="tv-card">', unsafe_allow_html=True)
        st.markdown("#### 🧭 Profile Customization")
        bio = st.text_area("Bio", value=users[username].get("bio", ""), placeholder="Tell us about your travel style...")
        fav_dest = st.text_input("Favorite Destination", value=users[username].get("favorite_destination", ""), placeholder="e.g., Kyoto, Santorini, Banff")
        goals = st.text_area("Travel Goals", value=users[username].get("goals", ""), placeholder="e.g., Visit 3 new countries this year")

        if st.button("💾 Save Profile"):
            users[username]["bio"] = bio.strip()
            users[username]["favorite_destination"] = fav_dest.strip()
            users[username]["goals"] = goals.strip()
            save_users(users)
            st.success("Profile details saved!")

        st.markdown("#### 🏅 Your Travel Badge")
        st.markdown(f"*Current Badge:* {badge_name}")
        st.markdown(f"*Trips Logged:* {len(user_trips)}")
        if next_threshold is not None:
            remaining = max(0, next_threshold - len(user_trips))
            st.progress(0 if next_threshold == 0 else min(1.0, len(user_trips) / max(1, next_threshold)))
            st.caption(f"{remaining} more trip(s) to reach the next badge.")
        else:
            st.caption("You’ve reached the top badge — World Citizen! 🎉")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- SETTINGS ----------------------
elif st.session_state.logged_in and menu == "Settings":
    st.header("⚙ Settings")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    new_pass = st.text_input("New Password", type="password")
    if st.button("Update Password"):
        if new_pass:
            users[st.session_state.username]['password'] = hash_password(new_pass)
            save_users(users)
            st.success("Password updated successfully!")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- CONTACT ----------------------
elif st.session_state.logged_in and menu == "Contact":
    st.header("📞 Contact Us")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    st.write("For any queries, reach us at: support@travelviz.com")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- CHATBOT ----------------------
elif st.session_state.logged_in and menu == "Chatbot":
    st.header("🤖 TravelViz Chatbot")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    user_message = st.text_input("Ask me about the project:")
    if st.button("Send"):
        if user_message:
            bot_reply = chatbot_response(user_message)
            st.text_area("Bot:", value=bot_reply, height=100)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- ADMIN PANEL ----------------------
elif st.session_state.logged_in and menu == "Admin Panel" and st.session_state.role == "admin":
    st.header("🛠 Admin Panel")
    st.subheader("Registered Users:")
    st.markdown('<div class="tv-card">', unsafe_allow_html=True)
    for user in users:
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            st.write(f"👤 {user} ({users[user].get('role')})")
        with col2:
            if st.button(f"Switch as {user}", key=f"switch_{user}"):
                st.session_state.username = user
                st.session_state.role = users[user].get("role", "user")
                st.rerun()
        with col3:
            if st.button(f"Reset Pic {user}", key=f"reset_{user}"):
                users[user]['profile_pic'] = None
                save_users(users)
                st.success(f"Profile picture reset for {user}")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------- Footer ----------------------
st.markdown("""
<div class="tv-footer">
    🚀 Built with ❤ using Streamlit • TravelViz © 2025
</div>
""", unsafe_allow_html=True)