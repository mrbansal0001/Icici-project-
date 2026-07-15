import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
import pgeocode
import time

# 1. Page Config
st.set_page_config(page_title="ICICI Affluence Radar 2.0", layout="wide")

# Customizing the theme a bit to match ICICI brand colors
st.markdown("""
    <style>
    .css-1d391kg { padding-top: 1rem; }
    h1 { color: #8F181B; }  /* Deep ICICI Red */
    </style>
""", unsafe_allow_html=True)

st.title("🎯 ICICI Bank Affluence Radar 2.0")
st.markdown("Identify High-Net-Worth (HNW) Micro-Markets for Premium Product Sales using Geospatial Intelligence.")

# 2. Load Data & Geocode
@st.cache_data
def load_and_geocode_data():
    df = pd.read_csv("final_master_dataset_scored.csv")
    df['pincode'] = df['pincode'].astype(str).str.strip()
    
    # Initialize pgeocode for India
    nomi = pgeocode.Nominatim('in')
    
    # Query all pincodes at once (vectorized)
    geo_data = nomi.query_postal_code(df['pincode'].tolist())
    
    # Merge geo columns back into our dataset
    df['latitude'] = geo_data['latitude']
    df['longitude'] = geo_data['longitude']
    df['state'] = geo_data['state_name']
    df['city'] = geo_data['county_name']
    
    # Fill NAs in geo data with "Unknown" or drop them for the map
    df['state'] = df['state'].fillna('Unknown')
    df['city'] = df['city'].fillna('Unknown')
    
    # Create a clean version for the map (must have valid coordinates)
    df_map = df.dropna(subset=['latitude', 'longitude'])
    
    return df, df_map

with st.spinner('Loading geographical data across India...'):
    df, df_map = load_and_geocode_data()

# 3. Sidebar Filters
st.sidebar.header("🔍 Global Filters")

all_states = sorted([s for s in df['state'].unique() if s != 'Unknown'])
selected_state = st.sidebar.selectbox("Select State:", ["All of India"] + all_states)

tier_filter = st.sidebar.multiselect(
    "Filter by Affluence Tier:", 
    options=["Platinum", "Gold", "Silver", "Standard"], 
    default=["Platinum", "Gold"]
)

# Apply Filters
if selected_state != "All of India":
    filtered_df = df[(df['state'] == selected_state) & (df["Affluence_Tier"].isin(tier_filter))]
    filtered_map_df = df_map[(df_map['state'] == selected_state) & (df_map["Affluence_Tier"].isin(tier_filter))]
else:
    filtered_df = df[df["Affluence_Tier"].isin(tier_filter)]
    filtered_map_df = df_map[df_map["Affluence_Tier"].isin(tier_filter)]

# 4. KPIs
st.header("Overview")
col1, col2, col3, col4 = st.columns(4)

total_filtered = len(filtered_df)
total_platinum = len(filtered_df[filtered_df["Affluence_Tier"] == "Platinum"])
total_gold = len(filtered_df[filtered_df["Affluence_Tier"] == "Gold"])
avg_score = filtered_df["Affluence_Score"].mean() if not filtered_df.empty else 0

col1.metric("Pincodes Found", f"{total_filtered:,}")
col2.metric("Platinum (Top 2%)", f"{total_platinum:,}")
col3.metric("Gold (Top 10%)", f"{total_gold:,}")
col4.metric("Average Affluence Score", f"{avg_score:.1f}")

st.divider()

# 5. 3D Map (PyDeck)
st.header("🗺️ 3D Affluence Hotspots Map")
st.write("Visualize the wealth density across your selected region. Higher spikes mean a higher concentration of affluent pincodes.")

if not filtered_map_df.empty:
    # Set the viewport location based on data
    view_state = pdk.ViewState(
        longitude=filtered_map_df["longitude"].mean(),
        latitude=filtered_map_df["latitude"].mean(),
        zoom=4 if selected_state == "All of India" else 6,
        pitch=45,
        bearing=0,
    )
    
    # Hexagon Layer for 3D mapping
    layer = pdk.Layer(
        "HexagonLayer",
        data=filtered_map_df,
        get_position=["longitude", "latitude"],
        radius=15000 if selected_state == "All of India" else 5000,
        elevation_scale=1000 if selected_state == "All of India" else 300,
        elevation_range=[0, 3000],
        pickable=True,
        extruded=True,
        color_range=[
            [255, 255, 204],
            [255, 237, 160],
            [254, 217, 118],
            [254, 178, 76],
            [253, 141, 60],
            [240, 59, 32],
            [189, 0, 38]
        ],
        coverage=1,
    )
    
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Concentration of Wealth Targets in this area"},
        map_style="mapbox://styles/mapbox/dark-v10",
    )
    
    st.pydeck_chart(r)
else:
    st.warning("No data available for the selected filters to display on the map.")

st.divider()

# 6. Deep Dive / Profiler
st.header("📍 Pincode Profiler")
pincode_input = st.text_input("Enter a specific Pincode to Profile (e.g. 122002):", "")

if pincode_input:
    pin_data = df[df['pincode'] == pincode_input.strip()]
    if pin_data.empty:
        st.warning("Pincode not found in our dataset.")
    else:
        row = pin_data.iloc[0]
        
        location_str = f"{row['city']}, {row['state']}" if row['state'] != "Unknown" else "Location Unknown"
        st.subheader(f"Profile for Pincode: {row['pincode']} ({location_str})")
        
        tier_color = "black"
        if row['Affluence_Tier'] == "Platinum":
            tier_color = "#E5E4E2" 
        elif row['Affluence_Tier'] == "Gold":
            tier_color = "#FFD700" 
        elif row['Affluence_Tier'] == "Silver":
            tier_color = "#C0C0C0" 
            
        st.markdown(f"### Tier: <span style='color:black; background-color:{tier_color}; padding:5px 10px; border-radius:5px;'>{row['Affluence_Tier']}</span>  |  **Score:** {row['Affluence_Score']}/100", unsafe_allow_html=True)
        st.write("")
        
        c1, c2 = st.columns([1.5, 1])
        
        with c1:
            pillars = ['Financial Penetration', 'Commercial Vibrancy', 'Lifestyle Premium', 'Infrastructure Scale']
            values = [row['Financial_Penetration'], row['Commercial_Vibrancy'], row['Lifestyle_Premium'], row['Infrastructure_Scale']]
            
            pillars.append(pillars[0])
            values.append(values[0])
            
            radar_df = pd.DataFrame(dict(r=values, theta=pillars))
            
            fig = px.line_polar(radar_df, r='r', theta='theta', line_close=True,
                                title=f"Wealth Drivers (Percentiles)")
            fig.update_traces(fill='toself', line_color='#F16122') 
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.markdown("#### Key Underlying Signals (Raw Counts)")
            st.write(f"- **Golf Courses:** {int(row['Golf_Course_Count'])}")
            st.write(f"- **Premium Stores:** {int(row['premium_store_count'])}")
            st.write(f"- **Corporate Hubs:** {int(row['Total_Corporate_Hubs'])}")
            st.write(f"- **Investment Advisors:** {int(row['Investment_Advisor_Count'])}")
            st.write(f"- **Mutual Fund Distributors:** {int(row['MF_Distributor_Count'])}")
            st.write(f"- **Hospitals (NABH):** {int(row['nabh_hospital_count'])}")
            st.write(f"- **EV Charging Stations:** {int(row['ev_charging_station_count'])}")
            st.write(f"- **Total Retail Branches:** {int(row['Total_Retail_Branches'])}")
            st.write(f"- **Retail Pvt/Pub Ratio:** {row['Retail_Private_to_Public_Ratio']:.2f}x")
            
st.divider()

# 7. Lead Generation Table
st.header("📋 Lead Generation Targets")
st.write("Extract your targeted list of wealthy pincodes for the region selected above.")

if not filtered_df.empty:
    st.dataframe(
        filtered_df[['pincode', 'city', 'state', 'Affluence_Score', 'Affluence_Tier', 'Financial_Penetration', 'Commercial_Vibrancy', 'Lifestyle_Premium', 'Infrastructure_Scale']],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No targets found for the selected filters.")
