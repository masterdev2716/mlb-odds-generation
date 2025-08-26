import requests
import csv
import json
import os
import argparse
from datetime import datetime, timedelta
from config import SPORTSDATA_API_KEY, SPORTSDATA_BASE_URL

# ... existing code ...

def main():
    """
    Main function to fetch MLB odds data and save to CSV
    """
    print("MLB Odds Data Fetcher")
    print("=" * 50)
    
    # Load team runs data first
    print("Loading team runs data...")
    team_runs_data = load_team_runs_data()
    
    # Load team scores data
    print("Loading team scores data...")
    team_scores_data = load_team_scores_data()
    
    # Show some sample team runs data for verification
    if team_runs_data:
        print(f"\nSample team runs data loaded:")
        sample_count = 0
        for team_pair, runs in team_runs_data.items():
            if sample_count < 5:  # Show first 5 team pairs
                print(f"  {team_pair}: {runs['team_a_score']:.1f} vs {runs['team_b_score']:.1f}")
                print(f"    Prediction Over/Under: {runs['prediction_overunder']}")
                sample_count += 1
            else:
                break
        print(f"  ... and {len(team_runs_data) - 5} more team pairs")
    else:
        print("No team runs data loaded!")
    
    print("\nPrediction Odds Calculation:")
    print("  - Based on 60% historical head-to-head performance")
    print("  - Combined with 40% current team scoring capability")
    print("  - Converted to MLB moneyline format (e.g., -150, +200)")
    print("  - Negative odds = favorite, Positive odds = underdog")
    
    # Show some sample team scores data for verification
    if team_scores_data:
        print(f"\nSample team scores data loaded:")
        sample_count = 0
        for team_name, score in team_scores_data.items():
            if sample_count < 5:  # Show first 5 teams
                print(f"  {team_name}: {score:.1f}")
                sample_count += 1
            else:
                break
        print(f"  ... and {len(team_scores_data) - 5} more teams")
    else:
        print("No team scores data loaded!")
    
    # Parse target date from CLI
    parser = argparse.ArgumentParser(description="Fetch MLB odds data and save to CSV")
    parser.add_argument("-d", "--date", help="Target date YYYY-MM-DD or 'today'/'yesterday'")
    args = parser.parse_args()

    explicit_date = args.date is not None

    if args.date:
        arg_lower = args.date.lower()
        if arg_lower == "today":
            target_dt = datetime.now()
            date_str = target_dt.strftime("%Y-%m-%d")
        elif arg_lower == "yesterday":
            target_dt = datetime.now() - timedelta(days=1)
            date_str = target_dt.strftime("%Y-%m-%d")
        else:
            try:
                target_dt = datetime.strptime(args.date, "%Y-%m-%d")
                date_str = target_dt.strftime("%Y-%m-%d")
            except ValueError:
                print("Invalid --date format. Use YYYY-MM-DD or 'today'/'yesterday'.")
                return
    else:
        target_dt = datetime.now() - timedelta(days=1)
        date_str = target_dt.strftime("%Y-%m-%d")
    
    print(f"\nFetching odds data for: {date_str}")
    
    # Fetch the odds data
    odds_data = fetch_mlb_odds_by_date(date_str)
    
    if odds_data:
        print(f"Successfully fetched data for {len(odds_data)} games")
        
        # Parse the data
        parsed_games = parse_odds_data(odds_data)
        
        if parsed_games:
            # Save to CSV with team runs data and team scores data
            filename = f"mlb_odds_with_runs_{date_str}.csv"
            save_to_csv(parsed_games, filename, team_runs_data, team_scores_data)
            
            # Display sample data
            print("\nSample data from first game:")
            if parsed_games:
                sample_game = parsed_games[0]
                away_runs, home_runs, prediction_odds, prediction_overunder = get_team_runs(sample_game['AwayTeam'], sample_game['HomeTeam'], team_runs_data, team_scores_data)
                away_score = get_team_score(sample_game['AwayTeam'], team_scores_data)
                home_score = get_team_score(sample_game['HomeTeam'], team_scores_data)
                print(f"  GameID: {sample_game['GameID']}")
                print(f"  DateTime: {sample_game['DateTime']}")
                print(f"  AwayTeam: {sample_game['AwayTeam']} (Runs: {away_runs:.1f}, Score: {away_score:.1f})")
                print(f"  HomeTeam: {sample_game['HomeTeam']} (Runs: {home_runs:.1f}, Score: {home_score:.1f})")
                print(f"  Prediction Odds: {format_odds_range(prediction_odds)}, Over/Under: {prediction_overunder}")
        else:
            print("No games data to parse")
    else:
        print("Failed to fetch odds data")
        
        if not explicit_date:
            # Try with a different date (maybe today's games)
            today = datetime.now()
            today_str = today.strftime("%Y-%m-%d")
            print(f"\nTrying to fetch data for today: {today_str}")
            
            odds_data = fetch_mlb_odds_by_date(today_str)
            if odds_data:
                print(f"Successfully fetched data for {len(odds_data)} games")
                parsed_games = parse_odds_data(odds_data)
                if parsed_games:
                    filename = f"mlb_odds_with_runs_{today_str}.csv"
                    save_to_csv(parsed_games, filename, team_runs_data, team_scores_data)
            else:
                print("No data available for today either")
        else:
            print("No data available for the requested date")

if __name__ == "__main__":
    main() 