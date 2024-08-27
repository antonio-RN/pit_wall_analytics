import streamlit as st
import fastf1 as ff1
import datetime as dt
import pandas as pd
import numpy as np
import altair as alt
from annotated_text import annotated_text

#ff1.Cache.clear_cache()
#st.cache_data.clear()
ff1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"

# Function definition
def convert_time_string(timedelta_raw):
    if pd.notna(timedelta_raw):
        hours, rem = divmod(timedelta_raw.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        milliseconds = timedelta_raw.microseconds // 1000 
        return str(f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}")
    else:
        return pd.NaT
    
#@st.cache_data
def load_data_session(year, event, session, laps=False, telemetry=False, weather=False):
    ff1_event = ff1.get_event(year=year, gp=event)
    ff1_session = ff1_event.get_session(session)
    ff1_session.load(laps=laps, telemetry=telemetry, weather=weather)
    return ff1_session

def convert_time_string_general(timedelta_raw):
    if pd.notna(timedelta_raw):
        days = timedelta_raw.days
        hours = timedelta_raw.seconds // 3600
        return str(f"{days} day(s), {hours} hour(s)")
    else:
        return pd.NaT
    
def convert_time_float(timedelta_raw):
    if pd.notna(timedelta_raw):
        milliseconds = timedelta_raw.microseconds // 1000 
        return float(timedelta_raw.seconds)+milliseconds*0.001
    else:
        return pd.NaT

# Page layout
st.set_page_config(
    page_title="PitStop strategy",
    layout="wide"
)
st.title("PitStop strategy")
tab_Home, tab_Results, tab_Laps, tab_Telemetry = st.tabs(["Home", "Results", "Laps", "Telemetry"])

## Tab HOME
colH1, colH2 = tab_Home.columns(2)
colH1.write("""
        Welcome to _PitStop strategy_ app. Your one-stop-shop for Formula 1 results, qualifying data, and in-depth analysis. 
        Explore past races and qualifying sessions, visualize performance with our summarizing graphs, 
        or dive into the details of each lap and car telemetry.
         
        
        Navigate through the tabs ahead one by one, choose the GP and session you want to know more about and select the 
        driver(s) and lap(s) to compare head to head.
         """)

# Info next event
select_event_schedule = ff1.get_event_schedule(dt.datetime.now(dt.timezone.utc).year, include_testing=False)
select_event_schedule= select_event_schedule.assign(
    Session1_UTC=lambda df: df.loc[:,"Session1DateUtc"].map(lambda ele: ele.tz_localize("utc")),
    Session2_UTC=lambda df: df.loc[:,"Session2DateUtc"].map(lambda ele: ele.tz_localize("utc")),
    Session3_UTC=lambda df: df.loc[:,"Session3DateUtc"].map(lambda ele: ele.tz_localize("utc")),
    Session4_UTC=lambda df: df.loc[:,"Session4DateUtc"].map(lambda ele: ele.tz_localize("utc")),
    Session5_UTC=lambda df: df.loc[:,"Session5DateUtc"].map(lambda ele: ele.tz_localize("utc")),
)
next_event = select_event_schedule.loc[select_event_schedule["Session5_UTC"] > dt.datetime.now(dt.timezone.utc),:].iloc[0]
time_to_next_event = next_event.at["Session5_UTC"] - dt.datetime.now(dt.timezone.utc)

colH3, colH4 = colH2.columns(2)
colH3.metric(
    "Time to next race",
    convert_time_string_general(time_to_next_event)
)
colH3.metric(
    "Grand Prix",
    next_event.at["EventName"]
)
colH4.metric(
    "Country",
    next_event.at["Country"]
)
colH4.metric(
    "Location",
    next_event.at["Location"]
)

## Tab RESULTS
# Input from user (year)
colR1, colR2 = tab_Results.columns(2)
colR3, colR4, colR5 = colR1.columns(3)
st.session_state.sel_year = colR3.selectbox(
    "Season", options=range(2018, dt.datetime.now(dt.timezone.utc).year+1)[::-1], index=0
)

# Update info selected schedule, input from user (GP)
if st.session_state.sel_year != dt.datetime.now(dt.timezone.utc).year:
    select_event_schedule = ff1.get_event_schedule(st.session_state.sel_year, include_testing=False).sort_values("RoundNumber", ascending=False)
rest_GPs = select_event_schedule.loc[select_event_schedule["Session5_UTC"] < dt.datetime.now(dt.timezone.utc),:]
st.session_state.sel_GP = colR4.selectbox(
    "Grand Prix", options=rest_GPs.sort_values("RoundNumber", ascending=False).loc[:,"EventName"], index=0
)
select_session = load_data_session(st.session_state.sel_year, st.session_state.sel_GP, "Race", laps=True)

# Update info selected schedule, input from user (GP session)
list_available_sessions = select_event_schedule[select_event_schedule["EventName"] == st.session_state.sel_GP].loc[
    :,["Session1", "Session2", "Session3", "Session4", "Session5"]
].iloc[0].to_list()[::-1]
session_options = ["Qualifying", "Sprint", "Race"]
if (len(select_session.results)<1) | (len(select_session.results.loc[:,"Position"].unique())<5) |  (len(select_session.laps)<1):
    session_options.remove("Race")

list_select_sessions = [session for session in list_available_sessions if session in session_options]
st.session_state.sel_GP_session = colR5.selectbox(
        "Session", options=list_select_sessions, index=0
)

# Load data with Laps info
select_session = load_data_session(st.session_state.sel_year, st.session_state.sel_GP, st.session_state.sel_GP_session, laps=True)
select_session_results = select_session.results.copy()

# Data formatting  
if (st.session_state.sel_GP_session == "Qualifying"):
    select_session_results = select_session_results.assign(
        Q1_str=lambda df: df.loc[:,"Q1"].map(convert_time_string),
        Q2_str=lambda df: df.loc[:,"Q2"].map(convert_time_string),
        Q3_str=lambda df: df.loc[:,"Q3"].map(convert_time_string)
    )
    results_Q_col = ["Position", "DriverNumber", "BroadcastName", "TeamName", "Q1_str", "Q2_str", "Q3_str"]
    results_Q_view = {"BroadcastName":"Driver", "DriverNumber":"Number", "TeamName":"Team", "Q1_str":"Q1", "Q2_str":"Q2", "Q3_str":"Q3"}
    st.session_state.results = select_session_results.loc[:,results_Q_col].rename(columns=results_Q_view)
    
elif ((st.session_state.sel_GP_session == "Race") | (st.session_state.sel_GP_session =="Sprint")):
    select_session_results.loc[:,"Time_str"] = select_session_results.apply(
        lambda s: convert_time_string(s["Time"]) if s["Position"]!="1" else pd.NaT,
        axis=1
    )
    results_R_col = ["Position", "Status", "DriverNumber", "BroadcastName", "TeamName", "Time_str", "Points"]
    results_R_view = {"DriverNumber":"Number", "BroadcastName":"Driver", "TeamName":"Team", "Time_str":"Leader"}
    st.session_state.results = select_session_results.loc[:,results_R_col].rename(columns=results_R_view)

# Results display and input from user (driver selected)
results_display = colR1.dataframe(
        st.session_state.results,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="results_display"
    )

# Selected session info display
colR6, colR7 = colR2.columns(2)
colR6.metric("Event name", select_session.event.at["EventName"])
colR6.metric("Country", select_session.event.at["Country"])
colR6.metric("Location", select_session.event.at["Location"])
colR7.metric("Championship round", select_session.event.at["RoundNumber"])
colR7.metric("Race date", select_session.event.at["Session5Date"].strftime("%d/%m/%Y"))
colR7.metric("Race format", 
            {"conventional": "Conventional",
            "sprint_qualifying": "Sprint Qualifying",
            "sprint_shootout": "Sprint Shootout",
            "sprint": "Sprint"
            }[select_session.event.at["EventFormat"]]
)

## Data wrangling
# Fuel correction estimation
n_laps = int(max(select_session.laps.loc[:,"LapNumber"]))
time_fuel_lap = (110+1)/n_laps*0.03

df_fuel_correction = pd.DataFrame({
    "LapNumber": [float(num) for num in range(1,1+n_laps)]
    }).assign(
        FuelCorr=lambda s: round((n_laps-s.loc[:,"LapNumber"])*time_fuel_lap,3)
    )

# Driver / team color schema
df_color_schema = select_session.results.loc[:,["Abbreviation", "TeamName", "TeamColor"]]
df_color_schema.loc[:,"TeamColor"] = df_color_schema.loc[:,"TeamColor"].map(lambda ele: "#"+ele)

# Position vs lap dataframe for charts (only "Race")
df_laps_position = select_session.laps.loc[:,["LapNumber", "Driver", "Position", "Team"]]

# Lap time distribution vs team dataframe for charts
df_total_laps = select_session.laps.pick_wo_box().pick_quicklaps().loc[:,["Driver", "Team", "LapNumber", "Stint", "Compound", "LapTime"]]
df_total_laps.loc[:,"LapTime_Q"] = df_total_laps.loc[:,"LapTime"].map(convert_time_float).drop(columns=["LapTime"])
df_total_laps = df_total_laps.merge(df_fuel_correction, on="LapNumber", how="left")
df_total_laps.loc[:,"LapTime_Q_corr"] = df_total_laps.apply(lambda df: df.loc["LapTime_Q"]-df.loc["FuelCorr"], axis=1).drop(columns=["FuelCorr"])
df_total_laps  = df_total_laps.merge(
    df_total_laps.loc[:,["Team", "LapTime_Q"]].groupby("Team").median().reset_index(), on="Team", suffixes=["", "_median"]
    )

# Lap time gap to P1 vs driver dataframe for charts (only "Qualifying")
df_best_laps = df_total_laps.loc[:,["Driver", "Team", "LapTime_Q"]].groupby("Driver").min().sort_values("LapTime_Q").reset_index()
df_best_laps = df_best_laps.assign(
    Gap=lambda df: df.loc[:,"LapTime_Q"] - df.loc[df.index[0],"LapTime_Q"]
    )

## Charts
tab_Results.divider()
colR8, colR9 = tab_Results.columns(2)

# Chart #1: Position vs lap (only "Race")
if ((st.session_state.sel_GP_session == "Race") | (st.session_state.sel_GP_session =="Sprint")):
    alt_R1_base = alt.Chart(df_laps_position, title="Race position").mark_line().encode(
        alt.X("LapNumber:Q").scale(domain=[1,n_laps]).title("Lap").title("Lap number"),
        alt.Y("Position:Q").scale(domain=[20,1]).axis(tickCount=20, orient="left"),
        color=alt.Color("Driver:N").scale(domain=df_color_schema.loc[:,"Abbreviation"], range=df_color_schema.loc[:,"TeamColor"]),
        tooltip= ["Driver", alt.Tooltip("LapNumber", title="Lap number"), "Position"]
    ).properties(
        width=600,
        height=600
    )
    alt_R1_top = alt_R1_base.mark_point().encode(
        alt.X("LapNumber:Q").scale(domain=[1,n_laps]).title("Lap").title("Lap number"),
        alt.Y("Position:Q").scale(domain=[20,1]).axis(tickCount=20, orient="right", title=""),
        color=alt.Color("Driver:N").scale(domain=df_color_schema.loc[:,"Abbreviation"], range=df_color_schema.loc[:,"TeamColor"]),
    )
    alt_R1 = alt.layer(alt_R1_base, alt_R1_top)
    colR8.altair_chart(alt_R1)
else:
# Chart #2: Lap time gap to P1 vs driver (only "Qualifying")
    alt_R2 = alt.Chart(df_best_laps).mark_bar(clip=True).encode(
        y=alt.Y("Driver:N").sort(),
        x=alt.X("Gap:Q").scale(domain=(0,df_best_laps.iloc[-1,-1]*1.005)).axis(tickMinStep=0.1),
        color=alt.Color("Team:N").scale(domain=df_color_schema.loc[:,"TeamName"].unique(), range=df_color_schema.loc[:,"TeamColor"].unique()),
        tooltip=["Driver", "Gap"]
    ).properties(
        width=600,
        height=600
    )
    colR8.altair_chart(alt_R2)

# Chart #3: Lap time distribution vs team
alt_R3 = alt.Chart(df_total_laps, title="Lap time distribution (s)").mark_boxplot().encode(
    x=alt.X("Team:N",sort=df_total_laps.sort_values("LapTime_Q_median", ascending=True).loc[:,"Team"].unique()),
    y=alt.Y("LapTime_Q:Q").scale(zero=False).title("Lap time (s)").title("Lap time (s)"),
    color=alt.Color("Team:N").scale(domain=df_color_schema.loc[:,"TeamName"].unique(), range=df_color_schema.loc[:,"TeamColor"].unique()),
).properties(
    width=600,
    height=600
)
colR9.altair_chart(alt_R3)

## Tab LAPS
# Load data with Laps from selected driver(s)
if len(results_display.selection["rows"]):

# Driver #1
    st.session_state.sel_driver_1 = st.session_state.results.loc[st.session_state.results.index[results_display.selection["rows"][0]],"Number"]
    select_laps_1 = select_session.laps.pick_driver(st.session_state.sel_driver_1)
# Driver #2 (if exists)
    try:
        st.session_state.sel_driver_2 = st.session_state.results.loc[st.session_state.results.index[results_display.selection["rows"][1]],"Number"]
        select_laps_2 = select_session.laps.pick_driver(st.session_state.sel_driver_2)

# Data formatting  
        select_laps_2 = select_laps_2.assign(
            Sector1Time_str=lambda df: df.loc[:,"Sector1Time"].map(convert_time_string),
            Sector2Time_str=lambda df: df.loc[:,"Sector2Time"].map(convert_time_string),
            Sector3Time_str=lambda df: df.loc[:,"Sector3Time"].map(convert_time_string),
            LapTime_str=lambda df: df.loc[:,"LapTime"].map(convert_time_string)
        )
    except:
        pass

    select_laps_1 = select_laps_1.assign(
        Sector1Time_str=lambda df: df.loc[:,"Sector1Time"].map(convert_time_string),
        Sector2Time_str=lambda df: df.loc[:,"Sector2Time"].map(convert_time_string),
        Sector3Time_str=lambda df: df.loc[:,"Sector3Time"].map(convert_time_string),
        LapTime_str=lambda df: df.loc[:,"LapTime"].map(convert_time_string)
    )

    colL1, colL2 = tab_Laps.columns(2)

    laps_L_col = ["LapNumber", "Stint", "Compound", "Sector1Time_str", "Sector2Time_str", "Sector3Time_str", "LapTime_str", "IsPersonalBest"]
    laps_L_view = {
        "LapNumber":"Lap", "Sector1Time_str": "Sector 1", "Sector2Time_str":"Sector 2",
        "Sector3Time_str":"Sector 3", "LapTime_str":"Lap time", "IsPersonalBest":"Personal best"}
    st.session_state.laps_1 = select_laps_1.loc[:,laps_L_col].rename(columns=laps_L_view)

# Laps display (driver #1) and input from user (laps selected)
    laps_display_1 = colL1.dataframe(
        st.session_state.laps_1,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="laps_display_1"
    )

# Selected driver #1 info display
    colL3, colL4 = colL2.columns(2)
    colL3.metric(
        "Driver",
        select_session.results.loc[select_session.results.loc[:,"DriverNumber"]==st.session_state.sel_driver_1,"BroadcastName"].iloc[0]
    )
    colL3.metric(
        "Final position",
        int(select_session.results.loc[select_session.results.loc[:,"DriverNumber"]==st.session_state.sel_driver_1,"Position"].iloc[0])
    )
    colL3.metric(
        "Number of pit stops",
        int(select_laps_1.loc[select_laps_1.index[-1],"Stint"]-1)
    )
    best_personal_1 = select_laps_1.loc[select_laps_1["IsPersonalBest"]==True,"LapTime"].iloc[-1]
    colL4.metric(
        f"Best personal lap",
        convert_time_string(best_personal_1)
    )
    best_sectors_index_1 = select_laps_1.loc[:,["Sector1Time", "Sector2Time", "Sector3Time"]].apply(np.argmin, axis=0)
    best_sectors_1 = [
        select_laps_1.loc[select_laps_1.index[best_sectors_index_1.iat[0]],"Sector1Time"],
        select_laps_1.loc[select_laps_1.index[best_sectors_index_1.iat[1]],"Sector2Time"],
        select_laps_1.loc[select_laps_1.index[best_sectors_index_1.iat[2]],"Sector3Time"]
    ]
    best_sectors_1.append(np.sum(best_sectors_1))
    diff_fictional_personal_best_1 = best_personal_1 - best_sectors_1[-1]
    colL4.metric(
        f"Best potential personal lap",
        convert_time_string(best_sectors_1[-1]),
        delta=f"-{convert_time_string(diff_fictional_personal_best_1)}",
        delta_color="inverse"
    )
    select_laps_start_stint_1 = select_laps_1[
        (~select_laps_1.loc[:,"PitOutTime"].isna()) | (select_laps_1.loc[:,"LapNumber"] == 1)
    ]
    tyre_strategy_1 = select_laps_start_stint_1["Compound"].apply(
        lambda item: item[0]
    )
    colL4.metric(
        "Tyre strategy",
        " - ".join(tyre_strategy_1)
    )

# Laps display (driver #1) and input from user (laps selected)
    try:
        st.session_state.laps_2 = select_laps_2.loc[:,laps_L_col].rename(columns=laps_L_view)

        colL11, colL22 = tab_Laps.columns(2)
        laps_display_2 = colL11.dataframe(
            st.session_state.laps_2,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row",
            key="laps_display_2"
        )

# Selected driver #2 info display        
        colL33, colL44 = colL22.columns(2)
        colL33.metric(
            "Driver",
            select_session.results.loc[select_session.results.loc[:,"DriverNumber"]==st.session_state.sel_driver_2,"BroadcastName"].iloc[0]
        )
        colL33.metric(
            "Final position",
            int(select_session.results.loc[select_session.results.loc[:,"DriverNumber"]==st.session_state.sel_driver_2,"Position"].iloc[0])
        )
        colL33.metric(
            "Number of pit stops",
            int(select_laps_2.loc[select_laps_2.index[-1],"Stint"]-1)
        )

        best_personal_2 = select_laps_2.loc[select_laps_2["IsPersonalBest"]==True,"LapTime"].iloc[-1]
        colL44.metric(
            f"Best personal lap",
            convert_time_string(best_personal_2)
        )
        best_sectors_index_2 = select_laps_2.loc[:,["Sector1Time", "Sector2Time", "Sector3Time"]].apply(np.argmin, axis=0)
        best_sectors_2 = [
            select_laps_2.loc[select_laps_2.index[best_sectors_index_2.iat[0]],"Sector1Time"],
            select_laps_2.loc[select_laps_2.index[best_sectors_index_2.iat[1]],"Sector2Time"],
            select_laps_2.loc[select_laps_2.index[best_sectors_index_2.iat[2]],"Sector3Time"]
        ]
        best_sectors_2.append(np.sum(best_sectors_2))
        diff_fictional_personal_best_2 = best_personal_2 - best_sectors_2[-1]
        colL44.metric(
            f"Best potential personal lap",
            convert_time_string(best_sectors_2[-1]),
            delta=f"-{convert_time_string(diff_fictional_personal_best_2)}",
            delta_color="inverse"
        )
        select_laps_start_stint_2 = select_laps_2[
            (~select_laps_2.loc[:,"PitOutTime"].isna()) | (select_laps_2.loc[:,"LapNumber"] == 1)
        ]
        tyre_strategy_2 = select_laps_start_stint_2["Compound"].apply(
            lambda item: item[0]
        )
        colL44.metric(
            "Tyre strategy",
            " - ".join(tyre_strategy_2)
        )
        select_laps = pd.concat([select_laps_1,select_laps_2])
    except:
        select_laps = select_laps_1.copy()

## Data wrangling
# Tire compound color schema
    compound_list = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"]
    compound_color = ["red", "yellow", "grey", "green", "blue"]

# Data formatting 
    df_select_laps_1 = select_laps_1.pick_wo_box().pick_quicklaps().loc[:,["Driver", "Team", "LapNumber", "Stint", "Compound", "LapTime"]]
    try:
        df_select_laps_2 = select_laps_2.pick_wo_box().pick_quicklaps().loc[:,["Driver", "Team", "LapNumber", "Stint", "Compound", "LapTime"]]
        df_select_laps = pd.concat([df_select_laps_1,df_select_laps_2])
    except:
        df_select_laps = df_select_laps_1.copy()
    df_select_laps = df_select_laps.merge(df_fuel_correction, on="LapNumber", how="left")
    df_select_laps.loc[:,"LapTime_Q"] = df_select_laps.loc[:,"LapTime"].map(convert_time_float).drop(columns=["LapTime"])
    df_select_laps.loc[:,"LapTime_Q_corr"] = df_select_laps.apply(lambda df: df.loc["LapTime_Q"]-df.loc["FuelCorr"], axis=1).drop(columns=["FuelCorr"])
    
## Charts
    tab_Laps.divider()

# Chart #1: Lap time vs lap (only with 2 drivers selected)
    if len(results_display.selection["rows"])>1:
        colL5, colL6 = tab_Laps.columns(2)
        alt_L1_base = alt.Chart(df_select_laps, title="Lap times (s) per stint").mark_point(
            filled=True,
            size=100
        ).encode(
            alt.X("LapNumber").title("Lap"),
            alt.Y("LapTime_Q:Q").scale(zero=False).title("Lap time (s)"),
            color=alt.Color("Driver").scale(domain=df_select_laps.loc[:,"Driver"].unique(), range=["blue", "cyan"]),
            tooltip= [
                alt.Tooltip("LapNumber", title="Lap number"),
                "Driver",
                alt.Tooltip("LapTime_Q", title="Lap time (s)")]
        ).properties(
            width=550,
            height=550
        )
        alt_L1_top = alt_L1_base.transform_regression(
            on="LapNumber",
            regression="LapTime_Q",
            method="linear",
            groupby=["Driver", "Stint"]
        ).mark_line().encode()
        
        if ((st.session_state.sel_GP_session == "Race") | (st.session_state.sel_GP_session =="Sprint")):
            alt_L1 = alt.layer(alt_L1_base, alt_L1_top)
            colL5.altair_chart(alt_L1)

        else:
            colL5.altair_chart(alt_L1_base)

# Chart #2: Lap time distribution (per driver)
        alt_L2 = alt.Chart(df_select_laps, title="Lap time distribution (s)").mark_boxplot().encode(
            x=alt.X("Driver:N",sort=df_select_laps.loc[:,["Driver", "LapTime_Q"]].groupby("Driver").median().sort_values("LapTime_Q", ascending=True).reset_index().loc[:,"Driver"].unique()),
            y=alt.Y("LapTime_Q:Q").scale(zero=False).title("Lap time (s)"),
            color=alt.Color("Driver:N").scale(domain=df_select_laps.loc[:,"Driver"].unique(), range=["blue", "cyan"])
        ).properties(
            width=550,
            height=550
        )
        colL6.altair_chart(alt_L2)    
    else:

# Chart #3: Lap time vs lap (per compound, only with 1 driver selected) 
        alt_L3_left = alt.Chart(df_select_laps, title="Lap times (s) per stint").mark_point(
            filled=True, 
            size=100
        ).encode(
            alt.X("LapNumber").title("Lap"),
            alt.Y("LapTime_Q:Q").scale(zero=False).title("Lap time (s)"),
            color=alt.Color("Compound:N").legend(None).scale(
                domain=compound_list, range=compound_color
            ),
            shape=alt.Shape("Stint:O").legend(None),
            tooltip= [
                alt.Tooltip("LapNumber", title="Lap number"),
                "Stint",
                alt.Tooltip("LapTime_Q", title="Lap time (s)")]
        ).properties(
            width=550,
            height=550
        )
# Chart #4: Fuel-corrected lap time vs lap (per compound, only with 1 driver selected)
        alt_L3_right_1 = alt.Chart(df_select_laps, title="Fuel-corrected lap times (s) per stint").mark_point(
            filled=True, 
            size=100
        ).encode(
            alt.X("LapNumber").title("Lap"),
            alt.Y("LapTime_Q_corr:Q").scale(zero=False).title("Fuel-corrected lap time (s)"),
            color=alt.Color("Compound:N").legend(title="Compound", values=df_select_laps.loc[:,"Compound"].unique()).scale(
                domain=compound_list, range=compound_color
            ),
            shape=alt.Shape("Stint:O").legend(title="Stint"),
            tooltip= [
                alt.Tooltip("LapNumber", title="Lap number"),
                "Stint",
                alt.Tooltip("LapTime_Q_corr", title="Lap time (s)")]
        ).properties(
            width=550,
            height=550
        )

        alt_L3_right_2 = alt_L3_right_1.transform_regression(
            on="LapNumber", regression="LapTime_Q_corr", groupby=["Stint"]
        ).mark_line().encode(
            color=alt.Color("Stint:O").legend(None),
            )
        if ((st.session_state.sel_GP_session == "Race") | (st.session_state.sel_GP_session =="Sprint")):
            alt_L3 = alt.hconcat(
                alt_L3_left, 
                alt.layer(alt_L3_right_1, alt_L3_right_2).resolve_scale(color="independent")
                ).resolve_scale(y="shared").resolve_legend(color="independent", shape="independent")

            tab_Laps.altair_chart(alt_L3)
        else:
            tab_Laps.altair_chart(alt_L3_left)
else:
    tab_Laps.write("Please, select a driver or two in the Results tab to display here the complete set of laps.")

## Tab TELEMETRY
# Laps selected logic
driver_selected = [False, False]
laps_selected = [0, 0]
try:
    laps_selected[0] = len(laps_display_1.selection["rows"])
    driver_selected[0] = True
except:
    pass
try:
    laps_selected[1] = len(laps_display_2.selection["rows"])
    driver_selected[1] = True
except:
    pass

## Data wrangling
# Telemetry data resampling and interpolation, delta time calculation
def inter_tel_data(s_distance, original_telem, driver, lap_n):
    df_telem = pd.DataFrame({
        "Distance": s_distance,
        "X (m)": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"X"]/10),
        "Y (m)": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"Y"]/10),
        "Z (m)": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"Z"]/10),
        "Speed": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"Speed"]),
        "RPM": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"RPM"]),
        "nGear": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"nGear"]),
        "Throttle": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"Throttle"]),
        "Brake": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"Brake"]),
        "Time": np.interp(x=s_distance, xp=original_telem.loc[:,"Distance"], fp=original_telem.loc[:,"Time"].map(convert_time_float)),
        "Driver": [driver for x in s_distance],
        "LapN": [lap_n for x in s_distance]
    })
    if lap_n == 1:
        df_telem.loc[:,"Delta"] = [0 for x in s_distance]
    return df_telem

# Load data with Telemetry from selected laps & data formatting
if driver_selected[0]:
    if driver_selected[1]:
        if laps_selected[0]:
            select_session = load_data_session(st.session_state.sel_year, st.session_state.sel_GP, st.session_state.sel_GP_session, laps=True, telemetry=True)
            st.session_state.sel_telem_1 = st.session_state.sel_driver_1
            select_laps_1 = select_session.laps.pick_driver(st.session_state.sel_telem_1)
            select_lap_1 = select_laps_1.pick_laps(laps_display_1.selection["rows"][0]+1)
            df_telemetry_laps = select_lap_1.get_telemetry()
            s_distance = range(0,round(df_telemetry_laps.loc[df_telemetry_laps.index[-1],"Distance"]+4),4)
            s_driver_1 = select_session.results.loc[select_session.results["DriverNumber"]==st.session_state.sel_telem_1,"Abbreviation"].iloc[0]
            df_telemetry_laps_inter = inter_tel_data(s_distance, df_telemetry_laps, s_driver_1, 1)
            if laps_selected[1]:
                st.session_state.sel_telem_2 = st.session_state.sel_driver_2
                select_laps_2 = select_session.laps.pick_driver(st.session_state.sel_telem_2)
                select_lap_2 = select_laps_2.pick_laps(laps_display_2.selection["rows"][0]+1)
                df_telemetry_laps_2 = select_lap_2.get_telemetry()
                s_driver_2 = select_session.results.loc[select_session.results["DriverNumber"]==st.session_state.sel_telem_2,"Abbreviation"].iloc[0]
                df_telemetry_laps_inter_2 = inter_tel_data(s_distance, df_telemetry_laps_2, s_driver_2, 2)
                df_telemetry_laps_inter_2.loc[:,"Delta"] = [df_telemetry_laps_inter_2.iloc[i].at["Time"] - df_telemetry_laps_inter.iloc[i].at["Time"] for i,_ in enumerate(s_distance)]
                df_telemetry_laps_inter = pd.concat([df_telemetry_laps_inter, df_telemetry_laps_inter_2])
            elif laps_selected[0]>1:
                    select_lap_2 = select_laps_1.pick_laps(laps_display_1.selection["rows"][1]+1)
                    df_telemetry_laps_2 = select_lap_2.get_telemetry()
                    s_driver_2 = s_driver_1
                    df_telemetry_laps_inter_2 = inter_tel_data(s_distance, df_telemetry_laps_2, s_driver_2, 2)
                    df_telemetry_laps_inter_2.loc[:,"Delta"] = [df_telemetry_laps_inter_2.iloc[i].at["Time"] - df_telemetry_laps_inter.iloc[i].at["Time"] for i,_ in enumerate(s_distance)]
                    df_telemetry_laps_inter = pd.concat([df_telemetry_laps_inter, df_telemetry_laps_inter_2])
        else:
            if laps_selected[1]:
                select_session = load_data_session(st.session_state.sel_year, st.session_state.sel_GP, st.session_state.sel_GP_session, laps=True, telemetry=True)
                st.session_state.sel_telem_1 = st.session_state.sel_driver_2
                select_laps_1 = select_session.laps.pick_driver(st.session_state.sel_telem_1)
                select_lap_1 = select_laps_1.pick_laps(laps_display_2.selection["rows"][0]+1)
                df_telemetry_laps = select_lap_1.get_telemetry()
                s_distance = range(0,round(df_telemetry_laps.loc[df_telemetry_laps.index[-1],"Distance"]+4),4)
                s_driver_1 = select_session.results.loc[select_session.results["DriverNumber"]==st.session_state.sel_telem_1,"Abbreviation"].iloc[0]
                df_telemetry_laps_inter = inter_tel_data(s_distance, df_telemetry_laps, s_driver_1, 1)
                if laps_selected[1]>1:
                    select_lap_2 = select_laps_1.pick_laps(laps_display_2.selection["rows"][1]+1)
                    df_telemetry_laps_2 = select_lap_2.get_telemetry()
                    s_driver_2 = s_driver_1
                    df_telemetry_laps_inter_2 = inter_tel_data(s_distance, df_telemetry_laps_2, s_driver_2, 2)
                    df_telemetry_laps_inter_2.loc[:,"Delta"] = [df_telemetry_laps_inter_2.iloc[i].at["Time"] - df_telemetry_laps_inter.iloc[i].at["Time"] for i,_ in enumerate(s_distance)]
                    df_telemetry_laps_inter = pd.concat([df_telemetry_laps_inter, df_telemetry_laps_inter_2])
            else:
                tab_Telemetry.write("Please, select a lap or two in the Laps tab to display here the telemetry.")
    else:
        if laps_selected[0]:
            select_session = load_data_session(st.session_state.sel_year, st.session_state.sel_GP, st.session_state.sel_GP_session, laps=True, telemetry=True)
            st.session_state.sel_telem_1 = st.session_state.sel_driver_1
            select_laps_1 = select_session.laps.pick_driver(st.session_state.sel_telem_1)
            select_lap_1 = select_laps_1.pick_laps(laps_display_1.selection["rows"][0]+1)
            df_telemetry_laps = select_lap_1.get_telemetry()
            s_distance = range(0,round(df_telemetry_laps.loc[df_telemetry_laps.index[-1],"Distance"]+4),4)
            s_driver_1 = select_session.results.loc[select_session.results["DriverNumber"]==st.session_state.sel_telem_1,"Abbreviation"].iloc[0]
            df_telemetry_laps_inter = inter_tel_data(s_distance, df_telemetry_laps, s_driver_1, 1)
            if laps_selected[0]>1:
                select_lap_2 = select_laps_1.pick_laps(laps_display_1.selection["rows"][1]+1)
                df_telemetry_laps_2 = select_lap_2.get_telemetry()
                s_driver_2 = s_driver_1
                df_telemetry_laps_inter_2 = inter_tel_data(s_distance, df_telemetry_laps_2, s_driver_2, 2)
                df_telemetry_laps_inter_2.loc[:,"Delta"] = [df_telemetry_laps_inter_2.iloc[i].at["Time"] - df_telemetry_laps_inter.iloc[i].at["Time"] for i,_ in enumerate(s_distance)]
                df_telemetry_laps_inter = pd.concat([df_telemetry_laps_inter, df_telemetry_laps_inter_2])
        else:
            tab_Telemetry.write("Please, select a lap or two in the Laps tab to display here the telemetry.")
else:
    tab_Telemetry.write("Please, select a lap or two in the Laps tab to display here the telemetry.")

colT1, colT2 = tab_Telemetry.columns([0.85, 0.15])

# Function definition for lap info display
def show_metrics_lap_1(index=0, isFirst=True): 
    if isFirst:
        color_back = "#0000FF"
        color_text = "#FFFFFF"
    else:
        color_back = "#00FFFF"
        color_text = "#000000"
    with colT2:
        annotated_text((select_session.results.loc[select_session.results.loc[:,"DriverNumber"]==st.session_state.sel_telem_1,"BroadcastName"].iloc[0], "", color_back, color_text))
        st.metric(
            "Lap number",
            int(select_lap_1.at[select_lap_1.index[0],"LapNumber"])
        )
        st.metric(
            "Compound",
            select_lap_1.at[select_lap_1.index[0], "Compound"]
        )
        st.metric(
            "Lap time",
            convert_time_string(select_lap_1.at[select_lap_1.index[0], "LapTime"])
        )
        st.metric(
            "Personal best",
            convert_time_string(best_personal_1),
            delta=f"-{convert_time_string(select_lap_1.at[select_lap_1.index[0], "LapTime"]-best_personal_1)}",
            delta_color="inverse"
        )
        pass

def show_metrics_lap_2(index=0, isFirst=True):
    if isFirst:
        color_back = "#0000FF"
        color_text = "#FFFFFF"
    else:
        color_back = "#00FFFF"
        color_text = "#000000"
    with colT2:
        annotated_text((select_session.results.loc[select_session.results.loc[:,"DriverNumber"]==st.session_state.sel_telem_2,"BroadcastName"].iloc[0], "", color_back, color_text))
        st.metric(
            "Lap number",
            int(select_lap_2.at[select_lap_2.index[0], "LapNumber"])
        )
        st.metric(
            "Compound",
            select_lap_2.at[select_lap_2.index[0], "Compound"]
        )
        st.metric(
            "Lap time",
            convert_time_string(select_lap_2.at[select_lap_2.index[0], "LapTime"])
        )
        st.metric(
            "Personal best",
            convert_time_string(best_personal_2),
            delta=f"-{convert_time_string(select_lap_2.loc[select_lap_2.index[0], "LapTime"]-best_personal_2)}",
            delta_color="inverse"
        )
    pass

if (driver_selected[0] & (laps_selected[0]>0)) | (driver_selected[1] & (laps_selected[1]>0)):
    T_view = {"Distance":"Distance (m)", "Time":"Time (s)", "Speed":"Speed (km/h)", "nGear":"Gear", "Throttle":"Throttle (%)", "Delta":"Delta (s)"}
    df_Telemetry = df_telemetry_laps_inter.rename(columns=T_view)

# Calculate fastest driver per minisectors
    try:
        minisectors = select_session.get_circuit_info().marshal_sectors.loc[:,"Distance"].sort_values().reset_index().drop(columns=["index"])
        list_minisectors = [df_Telemetry.loc[df_Telemetry["Distance (m)"]<minisectors.loc[minisectors.index[x],"Distance"],["LapN", "Time (s)"]].groupby("LapN").max().loc[:,"Time (s)"] for x in minisectors.index]
        df_minisectors = pd.DataFrame(list_minisectors).T
        df_minisectors.columns = minisectors.index.to_list()
        df_delta_minisectors = df_minisectors.apply(
            lambda s: s - s.shift(), axis=1
        )
        df_delta_minisectors.loc[:,0] = df_minisectors.loc[:,0]
        df_delta_minisectors = df_delta_minisectors.join(
        pd.Series([
            convert_time_float(select_lap_1.loc[select_lap_1.index[0], "LapTime"]) - df_delta_minisectors.iloc[0,:].sum(),
            convert_time_float(select_lap_2.loc[select_lap_2.index[0], "LapTime"]) - df_delta_minisectors.iloc[1,:].sum()
            ], index=[1,2], name=df_delta_minisectors.columns[-1]+1)
        )
        df_delta_minisectors = df_delta_minisectors.T
        df_delta_minisectors.loc[:,"faster"] = df_delta_minisectors.apply(lambda s: s.iloc[0]<s.iloc[1], axis=1)
        distances = [0] + minisectors.loc[:,"Distance"].to_list() + [float(df_Telemetry.loc[:,"Distance (m)"].max())]
        faster = pd.cut(df_telemetry_laps_inter.loc[:,"Distance"], bins=distances, labels=df_delta_minisectors.loc[:,"faster"], right=False, ordered=False)
        faster.name = "Faster"
        df_telemetry_laps_inter = df_telemetry_laps_inter.join(faster)
    except:
        pass

## Charts
# Chart #1: Composition chart with car data vs distance  
    alt_T1 = alt.Chart(df_Telemetry).mark_line().encode(
        alt.X("Distance (m):Q").title("Lap distance (m)"),
        alt.Y(alt.repeat("row"), type="quantitative"),
        alt.Color("LapN:N").scale(domain=[1,2], range=["blue", "cyan"]).legend(None),
        tooltip=[
            "Driver",
            alt.Tooltip(field="Distance (m)",formatType="number", format="d"),
            alt.Tooltip(field=alt.repeat("row"), formatType="number", format=".1f")
                ]
    ).properties(
        height=200, 
        width=950
    ).repeat(
        row=["Speed (km/h)", "Delta (s)", "Throttle (%)", "Brake", "RPM", "Gear"]
    ).resolve_scale(x="shared").interactive()
    colT1.altair_chart(alt_T1, use_container_width=True)

# Chart #2: Car speed vs car position (XYZ coordinates)
    alt_T2 = alt.Chart(df_Telemetry, title="Vehicle speed (km/h)").mark_point().encode(
        x=alt.X("X (m)").axis(None),
        y=alt.Y("Y (m)").axis(None),
        color=alt.Color("Speed (km/h)").scale(scheme="lightgreyred"),
        tooltip=alt.Tooltip(field="Speed (km/h)", formatType="number", format="d")
    ).properties(
        height=500,
        width=600
    ).configure_axis(
            grid=False
        )
    colT3, colT4 = tab_Telemetry.columns(2)
    colT3.altair_chart(alt_T2)

# Chart #3: Fastest minisector vs car position (XYZ coordinates)

    alt_T3 = alt.Chart(df_telemetry_laps_inter, title="Lap dominance per minisector").mark_point(
    filled=True,
    size=50
).encode(
    x=alt.X("X (m)").axis(None),
    y=alt.Y("Y (m)").axis(None),
    color=alt.Color("Faster:N").scale(range=["blue", "cyan"]).legend(None),
    #tooltip=None
    ).properties(
        height=500,
        width=500
    ).configure_axis(
        grid=False
    )
    colT4.altair_chart(alt_T3)

# Selected laps info display
if driver_selected[0]:
    if driver_selected[1]:
        if laps_selected[0]:
            show_metrics_lap_1(0)
            if laps_selected[1]:
                colT2.divider()
                show_metrics_lap_2(0, False)
            elif laps_selected[0]>1:
                colT2.divider()
                show_metrics_lap_1(1, False)
        elif laps_selected[1]:
            show_metrics_lap_2(0)
            if laps_selected[1]>1:
                colT2.divider()
                show_metrics_lap_2(1, False)
    elif laps_selected[0]:
        show_metrics_lap_1(0)
        if laps_selected[0]>1:
            colT2.divider()
            show_metrics_lap_1(1, False)
