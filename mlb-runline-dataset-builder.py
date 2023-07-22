# -*- coding: utf-8 -*-
"""
Created 2023

@author: Quant Galore
"""

from datetime import datetime, timedelta

import pandas as pd
import statsapi
import requests
import numpy as np
import sqlalchemy
import mysql.connector

Short_Long_Names = pd.read_csv("short_long_mlb_names.csv")

def name_converter(short_name):
    
    long_name = Short_Long_Names[Short_Long_Names["short_name"] == short_name]["long_name"]
    
    if len(long_name) < 1 :
        
        return np.nan
    else:
    
        return long_name.iloc[0]

API_KEY = "your prop-odds.com api key"

# =============================================================================
# Start 
# =============================================================================

# First, we call the schedule API to get a list of all games played from the start of the season, up to yesterday.

begin_date = "2023-03-30"
ending_date = (datetime.today() - timedelta(days = 1)).strftime("%Y-%m-%d")

Schedule = statsapi.schedule(start_date = begin_date, end_date = ending_date)
Schedule_DataFrame = pd.json_normalize(Schedule)

date_range = pd.date_range(start = begin_date, end = ending_date)

odds_list = []

# The spread market represents the "runline" bet

market = "spread"

for date in date_range:

    date = date.strftime("%Y-%m-%d")
    url = f"https://api.prop-odds.com/beta/games/mlb?date={date}&tz=America/Chicago&api_key={API_KEY}"
    games_url = f"https://api.prop-odds.com/beta/games/mlb?date={date}&api_key={API_KEY}"
    
    
    games = pd.json_normalize(requests.get(games_url).json()["games"])
    
    if len(games) < 1:
        
        continue
    
    for game_id in games["game_id"]:
        
        Game = games[games["game_id"] == game_id]
        
        sportsbook = []
    
        odds_url = f"https://api.prop-odds.com/beta/odds/{game_id}/{market}?api_key={API_KEY}"
        odds = requests.get(odds_url).json()
        
        if len(odds) < 2:
            continue
        
        else:
            
            # DraftKings generally offers the best odds, so for uniformity, we only include odds sourced from DraftKings
            
            for book in odds["sportsbooks"]:
                
                if book["bookie_key"] == "draftkings":
                    sportsbook = book
                else:
                    continue
                
            if len(sportsbook) < 1:
                
                continue
                
            odds_data = pd.json_normalize(sportsbook["market"]["outcomes"])
            
            # The runline (-1.5) refers to the favorite winning by 2 or more points, so we have to first pull who the favorite is
            
            moneyline_url = f"https://api.prop-odds.com/beta/odds/{game_id}/moneyline?api_key={API_KEY}"
            moneyline_odds = requests.get(moneyline_url).json()
            
            if len(moneyline_odds) < 2:
                continue
            
            else:
                
                for moneyline_book in moneyline_odds["sportsbooks"]:
                    
                    if moneyline_book["bookie_key"] == "draftkings":
                        moneyline_sportsbook = moneyline_book
                    else:
                        continue
                    
                if len(moneyline_sportsbook) < 1:
                    
                    continue
            
            moneyline_odds_data = pd.json_normalize(moneyline_sportsbook["market"]["outcomes"])
            
            if moneyline_odds_data["odds"].max() < 0:
                continue
            
            moneyline_favorite = moneyline_odds_data[moneyline_odds_data["odds"] < 0].sort_values(by = "timestamp", ascending = True).head(1)["name"].iloc[0]
            moneyline_underdog = moneyline_odds_data[moneyline_odds_data["odds"] > 0].sort_values(by = "timestamp", ascending = True).head(1)["name"].iloc[0]
            
            # We sort by earliest available pre-game odds first, since the API may occasionally include odds that were set mid-game.
            
            favorite = odds_data[(odds_data["handicap"] == -1.5) & (odds_data["name"] == moneyline_favorite)].sort_values(by = "timestamp", ascending = True).head(1)
            underdog = odds_data[(odds_data["handicap"] == 1.5) & (odds_data["name"] == moneyline_underdog)].sort_values(by = "timestamp", ascending = True).head(1)
            
            if len(favorite) < 1:
                continue
            elif len(underdog) < 1:
                continue
            
            team_1_favorite = favorite["name"].drop_duplicates().iloc[0]
            team_2_underdog = underdog["name"].drop_duplicates().iloc[0]
            
            team_1_favorite_odds = favorite["odds"].iloc[0]
            team_2_underdog_odds = underdog["odds"].iloc[0]
            
            odds_dataframe = pd.DataFrame([[team_1_favorite, team_1_favorite_odds, team_2_underdog, team_2_underdog_odds]],
                                          columns = ["team_1", "team_1_spread_odds", "team_2", "team_2_spread_odds"])
                
            full_odds_dataframe = pd.concat([Game.reset_index(drop = True), odds_dataframe], axis = 1)
            
            if len(full_odds_dataframe) > 1:
                continue
            
            odds_list.append(full_odds_dataframe)
            
full_odds = pd.concat(odds_list).reset_index(drop = True).rename(columns = {"away_team":"away_name",
                                                                            "home_team":"home_name",
                                                                            "start_timestamp":"game_datetime"})

Merged_DataFrame = pd.merge(Schedule_DataFrame, full_odds, on = ["game_datetime", "away_name", "home_name"])

Merged_DataFrame["team_1"] = Merged_DataFrame["team_1"].apply(name_converter)
Merged_DataFrame["team_2"] = Merged_DataFrame["team_2"].apply(name_converter)

Featured_Merged_DataFrame = Merged_DataFrame[["game_datetime","away_name","home_name","away_score","home_score", "team_1", "team_1_spread_odds", "team_2", "team_2_spread_odds", "venue_name", "winning_team"]].copy().set_index("game_datetime")

# "team_1" always represents the favorite

# If the favorite was the home team, then home score - away score gives us the spread -- vice versa if the favorite is the away team

team_1_away_wins = Featured_Merged_DataFrame[Featured_Merged_DataFrame["away_name"] == Featured_Merged_DataFrame["team_1"]].copy()
team_1_away_wins["spread"] = team_1_away_wins["away_score"].astype(int) - team_1_away_wins["home_score"].astype(int)

team_1_home_wins = Featured_Merged_DataFrame[Featured_Merged_DataFrame["home_name"] == Featured_Merged_DataFrame["team_1"]].copy()
team_1_home_wins["spread"] = team_1_home_wins["home_score"].astype(int) - team_1_home_wins["away_score"].astype(int)

spread_dataframe = pd.concat([team_1_away_wins, team_1_home_wins], axis = 0)

def spread_converter(spread):
    
    if spread >= 2:
        
        return 1
    else:
        return 0


# If the favorite won the game by 2 or more points, we assign a 1
# If the favorite wins by less than 2 points, or if the underdog wins, we assign a 0

spread_dataframe["spread"] = spread_dataframe["spread"].apply(spread_converter)

Featured_Spread_DataFrame = spread_dataframe[["team_1", "team_1_spread_odds", "team_2", "team_2_spread_odds", "venue_name", "spread"]].copy().reset_index().set_index("game_datetime")

# To weed out any errors in the data set, we ensure to only include data where the odds are between -200 to +200
# The odds for these bets are almost never set outside of that range, so we exclude them.

Featured_Spread_DataFrame = Featured_Spread_DataFrame[(abs(Featured_Spread_DataFrame["team_1_spread_odds"]) < 200) & (abs(Featured_Spread_DataFrame["team_2_spread_odds"]) < 200)]
Featured_Spread_DataFrame = Featured_Spread_DataFrame[Featured_Spread_DataFrame["team_1"] != Featured_Spread_DataFrame["team_2"]]
Featured_Spread_DataFrame.index = pd.to_datetime(Featured_Spread_DataFrame.index).tz_convert("America/Chicago")

# We initialize our sqlalchemy engine, then submit the data to the database

engine = sqlalchemy.create_engine('mysql+mysqlconnector://username:password@database-host-name:3306/database-name')

Featured_Spread_DataFrame.to_sql("baseball_spread", con = engine, if_exists = "append")

# If you make a mistake, or wish to re-build te dataset, you can drop the table and start over

with engine.connect() as conn:
    result = conn.execute(sqlalchemy.text('DROP TABLE baseball_spread'))
