import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Google Sheets Authentication ---
@st.cache_resource  # Cache to avoid repeated auth
def connect_to_gsheet():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=creds)
    return service

# --- Load Data from Google Sheets ---
@st.cache_data(ttl=600)  # Refresh every 10 mins
def load_data():
    service = connect_to_gsheet()
    sheet_id = st.secrets["private_gsheets"]["sheet_id"]
    range_name = "Sheet1!A1:K100"  # Adjust range
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()
    rows = result.get("values", [])
    df = pd.DataFrame(rows[1:], columns=rows[0])  # First row = headers
    return df

# --- UI Setup ---
st.set_page_config(layout="wide")
st.title("🚛 Freight & TAT Dashboard (Live from Google Sheets)")

# Load data (hidden from users)
df = load_data()

# Convert numeric columns
df["Freight Value"] = pd.to_numeric(df["Freight Value"])
df["TAT Value"] = pd.to_numeric(df["TAT Value"])

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")
selected_zone = st.sidebar.multiselect(
    "Select Zone", 
    df["ZONE"].unique(), 
    default=df["ZONE"].unique()[0]
)
selected_vehicle = st.sidebar.multiselect(
    "Vehicle Type", 
    df["Vehicle Type Corrected"].unique()
)
agg_method = st.sidebar.radio(
    "Aggregation", 
    ["Average", "Sum", "Max"], 
    horizontal=True
)

# --- Apply Filters ---
filtered_df = df.copy()
if selected_zone:
    filtered_df = filtered_df[filtered_df["ZONE"].isin(selected_zone)]
if selected_vehicle:
    filtered_df = filtered_df[filtered_df["Vehicle Type Corrected"].isin(selected_vehicle)]

# --- Dynamic Aggregation ---
if agg_method == "Average":
    agg_df = filtered_df.groupby("Month").mean(numeric_only=True).reset_index()
elif agg_method == "Sum":
    agg_df = filtered_df.groupby("Month").sum(numeric_only=True).reset_index()
else:
    agg_df = filtered_df.groupby("Month").max(numeric_only=True).reset_index()

# --- Interactive Charts ---
tab1, tab2, tab3 = st.tabs(["📊 Freight", "⏱️ TAT", "📈 Trends"])

with tab1:
    fig_freight = px.bar(
        agg_df, 
        x="Month", 
        y="Freight Value",
        title=f"{agg_method} Freight Value",
        color_discrete_sequence=["#4CAF50"]
    )
    st.plotly_chart(fig_freight, use_container_width=True)

with tab2:
    fig_tat = px.line(
        agg_df,
        x="Month",
        y="TAT Value",
        title=f"{agg_method} TAT Over Time",
        markers=True
    )
    st.plotly_chart(fig_tat, use_container_width=True)

with tab3:
    fig_trends = px.area(
        agg_df,
        x="Month",
        y=["Freight Value", "TAT Value"],
        title="Freight vs TAT Trend"
    )
    st.plotly_chart(fig_trends, use_container_width=True)

# --- Hide Raw Data ---
if st.checkbox("👁️ Show raw data (admin only)", False):
    st.dataframe(filtered_df)
else:
    st.info("🔒 Raw data hidden. Only aggregated results shown.")
