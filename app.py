import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

SHEET_NAME = "NCS Tutoring Sessions"

scopes = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scopes
)
client = gspread.authorize(creds)
spreadsheet = client.open(SHEET_NAME)
sessions_ws = spreadsheet.worksheet("Sessions")
signups_ws = spreadsheet.worksheet("Signups")

st.set_page_config(page_title="NCS Tutoring Sign-Up", layout="centered")
st.title("📅 NCS Tutoring Sign-Up")

tab1, tab2 = st.tabs(["Sign Up", "Summary"])

# ---- Load sessions ----
sessions_records = sessions_ws.get_all_records()
sessions_df = pd.DataFrame(sessions_records)

if not sessions_df.empty:
    sessions_df["DateParsed"] = pd.to_datetime(sessions_df["Date"], format="%m/%d/%y", errors="coerce")

today = pd.Timestamp(datetime.now().date())

# ---- TAB 1: Sign Up ----
with tab1:
    st.subheader("Upcoming Sessions")

    if sessions_df.empty:
        st.info("No upcoming sessions have been added yet.")
    else:
        upcoming = sessions_df[sessions_df["DateParsed"] >= today].sort_values("DateParsed")

        if upcoming.empty:
            st.info("No upcoming sessions right now, check back soon.")
        else:
            tutor_first = st.text_input("Your first name")
            tutor_last = st.text_input("Your last name")

            st.markdown("Click a session below to sign up:")

            for _, row in upcoming.iterrows():
                label = f"{row['Date']} at {row['Time']} ({row['Duration (minutes)']} min)"
                if st.button(f"Sign up: {label}", key=f"{row['Date']}_{row['Time']}"):
                    if tutor_first and tutor_last:
                        tutor_name = f"{tutor_first.strip().title()} {tutor_last.strip().title()}"
                        signups_ws.append_row([
                            row["Date"], row["Time"], tutor_name, row["Duration (minutes)"]
                        ])
                        st.success(f"Signed up for {label}!")
                    else:
                        st.error("Enter your first and last name before signing up.")

# ---- TAB 2: Summary ----
with tab2:
    st.subheader("Program Summary")

    signup_records = signups_ws.get_all_records()

    if not signup_records:
        st.info("No sign-ups yet.")
    else:
        df = pd.DataFrame(signup_records)
        df["Duration (minutes)"] = pd.to_numeric(df["Duration (minutes)"], errors="coerce")
        df["DateParsed"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", errors="coerce")

        past = df[df["DateParsed"] < today]
        future = df[df["DateParsed"] >= today]

        st.markdown("## Completed Hours (sessions that have passed)")
        if past.empty:
            st.info("No completed sessions yet.")
        else:
            col1, col2 = st.columns(2)
            col1.metric("Completed Sessions", len(past))
            col2.metric("Total Hours", f"{past['Duration (minutes)'].sum() / 60:.1f}")

            tutor_summary = (
                past.groupby("Tutor")["Duration (minutes)"].sum() / 60
            ).round(1).sort_values(ascending=False).reset_index()
            tutor_summary.columns = ["Tutor", "Hours"]
            tutor_summary.insert(0, "Rank", range(1, len(tutor_summary) + 1))
            st.dataframe(tutor_summary, use_container_width=True, hide_index=True,
                         height=min(35 * (len(tutor_summary) + 1), 600))

        st.divider()
        st.markdown("## Upcoming Sign-Ups (not yet counted)")
        if future.empty:
            st.info("No upcoming sign-ups yet.")
        else:
            st.dataframe(future[["Date", "Time", "Tutor", "Duration (minutes)"]],
                         use_container_width=True, hide_index=True)