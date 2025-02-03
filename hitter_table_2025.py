import streamlit as st
import pandas as pd

# Load datasets
fall_csv = "filtered_fall_trackman.csv"
winter_csv = "WINTER_ALL_trackman.csv"
spring_csv = "Spring Intrasquads MASTER.csv"

def load_data():
    fall_df = pd.read_csv(fall_csv)
    winter_df = pd.read_csv(winter_csv)
    spring_df = pd.read_csv(spring_csv)
    
    # Add a season column for filtering
    fall_df["Season"] = "Fall"
    winter_df["Season"] = "Winter"
    spring_df["Season"] = "Spring Preseason"
    
    # Combine all data
    df = pd.concat([fall_df, winter_df, spring_df], ignore_index=True)
    
    # Filter for specified teams
    df = df[df['BatterTeam'].isin(["OLE_REB", "OLE_PRA", "OLE_BULL"])]
    
    # Convert Date column to datetime, handling different formats
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', format='%Y-%m-%d')
    df['Date'] = df['Date'].fillna(pd.to_datetime(df['Date'], errors='coerce', format='%m/%d/%y'))
    
    return df

df = load_data()

# Sidebar filters
st.sidebar.title("Filters")
season_options = ["All", "Fall", "Winter", "Spring Preseason"]
selected_season = st.sidebar.selectbox("Select Season", season_options, index=0)

def filter_season(df, season):
    if season != "All":
        return df[df["Season"] == season]
    return df

df = filter_season(df, selected_season)

# Date range selection
date_min = df['Date'].min()
date_max = df['Date'].max()
selected_dates = st.sidebar.date_input(
    "Select Date Range",
    [date_min, date_max],
    min_value=date_min,
    max_value=date_max
)

if isinstance(selected_dates, list) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
    df = df[(df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))]

# Group data by Batter and calculate stats
pa_counts = df[df['PitchofPA'] == 1].groupby('Batter').size().reset_index(name='PA')
pitch_counts = df.groupby('Batter').size().reset_index(name='TotalPitches')
hitters_df = pd.merge(pitch_counts, pa_counts, on='Batter', how='left')

# Additional stats calculations
sacrifice_counts = df[df['PlayResult'] == 'Sacrifice'].groupby('Batter').size().reset_index(name='Sacrifice')
error_counts = df[df['PlayResult'] == 'Error'].groupby('Batter').size().reset_index(name='Error')
hbp_counts = df[df['PitchCall'] == 'HitByPitch'].groupby('Batter').size().reset_index(name='HBP')
hitters_df = pd.merge(hitters_df, sacrifice_counts, on='Batter', how='left').fillna(0)
hitters_df = pd.merge(hitters_df, error_counts, on='Batter', how='left').fillna(0)
hitters_df = pd.merge(hitters_df, hbp_counts, on='Batter', how='left').fillna(0)

# Hits breakdown
hit_conditions = df['PlayResult'].isin(['Single', 'Double', 'Triple', 'HomeRun'])
hit_counts = df[hit_conditions].groupby('Batter').size().reset_index(name='Hits')
hitters_df = pd.merge(hitters_df, hit_counts, on='Batter', how='left').fillna(0)

# Specific hit types
hitters_df['1B'] = df[df['PlayResult'] == 'Single'].groupby('Batter').size().reset_index(name='1B')['1B']
hitters_df['2B'] = df[df['PlayResult'] == 'Double'].groupby('Batter').size().reset_index(name='2B')['2B']
hitters_df['3B'] = df[df['PlayResult'] == 'Triple'].groupby('Batter').size().reset_index(name='3B')['3B']
hitters_df['HR'] = df[df['PlayResult'] == 'HomeRun'].groupby('Batter').size().reset_index(name='HR')['HR']
hitters_df = hitters_df.fillna(0)

# Calculate at-bats (AB)
bip_counts = df[df['PitchCall'] == 'InPlay'].groupby('Batter').size().reset_index(name='BIP')
k_counts = df[df['KorBB'] == 'Strikeout'].groupby('Batter').size().reset_index(name='K')
hitters_df = pd.merge(hitters_df, bip_counts, on='Batter', how='left').fillna(0)
hitters_df = pd.merge(hitters_df, k_counts, on='Batter', how='left').fillna(0)
hitters_df['AB'] = hitters_df['BIP'] + hitters_df['K'] - hitters_df['Sacrifice']

# Calculate advanced stats
hitters_df['TotalBases'] = hitters_df['1B'] + (2 * hitters_df['2B']) + (3 * hitters_df['3B']) + (4 * hitters_df['HR'])
hitters_df['SLG'] = hitters_df['TotalBases'] / hitters_df['AB']
hitters_df['OPS'] = hitters_df['OBP'] + hitters_df['SLG']

# Exit Velocity Stats
inplay_data = df[df['PitchCall'] == 'InPlay']
ev_stats = inplay_data.groupby('Batter').agg(
    EV=('ExitSpeed', 'mean'),
    EV_90th=('ExitSpeed', lambda x: x.quantile(0.9)),
    maxEV=('ExitSpeed', 'max')
).reset_index()
hitters_df = pd.merge(hitters_df, ev_stats, on='Batter', how='left').fillna(0)

# Display the DataFrame
st.title("Hitter Performance Table")
st.dataframe(hitters_df.style.set_sticky())
