import requests
import csv
import json
import os
import argparse
from datetime import datetime, timedelta
from config import SPORTSDATA_API_KEY, SPORTSDATA_BASE_URL

def load_team_runs_data():
    """
    Load team runs data from mlb_2024_head_to_head.csv
    Returns a dictionary mapping team pairs to their average runs, prediction odds, and prediction over/under
    """
    team_runs = {}
    head_to_head_file = "data/mlb_2024_head_to_head.csv"
    
    if not os.path.exists(head_to_head_file):
        print(f"Warning: {head_to_head_file} not found. Team runs data will be empty.")
        return team_runs
    
    try:
        with open(head_to_head_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            current_team_pair = None
            current_team_a_score = None
            current_team_b_score = None
            current_prediction_odds = None
            current_prediction_overunder = None
            
            for row in reader:
                # Check if this is a new team pair (has Team Pair value)
                if row['Team Pair'] and row['Team Pair'].strip():
                    # Save previous team pair data if we have it
                    if current_team_pair and current_team_a_score is not None and current_team_b_score is not None:
                        team_runs[current_team_pair] = {
                            'team_a_score': current_team_a_score,
                            'team_b_score': current_team_b_score,
                            'prediction_odds': current_prediction_odds,
                            'prediction_overunder': current_prediction_overunder
                        }
                    
                    # Start new team pair
                    current_team_pair = row['Team Pair'].strip()
                    current_team_a_score = float(row['TeamA Score']) if row['TeamA Score'] else None
                    current_team_b_score = float(row['TeamB Score']) if row['TeamB Score'] else None
                    current_prediction_odds = 0.0  # Default to 0.0 since this column doesn't exist in original file
                    current_prediction_overunder = row['Prediction_OverUnder'] if row['Prediction_OverUnder'] else None
            
            # Don't forget to save the last team pair
            if current_team_pair and current_team_a_score is not None and current_team_b_score is not None:
                team_runs[current_team_pair] = {
                    'team_a_score': current_team_a_score,
                    'team_b_score': current_team_b_score,
                    'prediction_odds': current_prediction_odds,
                    'prediction_overunder': current_prediction_overunder
                }
        
        print(f"Loaded team runs data for {len(team_runs)} team pairs")
        return team_runs
        
    except Exception as e:
        print(f"Error loading team runs data: {e}")
        return team_runs

def get_team_runs(team_a, team_b, team_runs_data, team_scores_data):
    """
    Get the team runs data for a specific team pair and calculate prediction odds
    Returns calculated prediction odds based on team performance data
    """
    # Try to find the team pair in the data
    team_pair = f"{team_a} vs vs vs {team_b}"
    
    if team_pair in team_runs_data:
        data = team_runs_data[team_pair]
        team_a_runs = data['team_a_score']
        team_b_runs = data['team_b_score']
    else:
        # Try reverse order
        reverse_pair = f"{team_b} vs vs vs {team_a}"
        if reverse_pair in team_runs_data:
            data = team_runs_data[reverse_pair]
            team_a_runs = data['team_b_score']  # Note: swapped order
            team_b_runs = data['team_a_score']  # Note: swapped order
        else:
            # If not found, return 0.0 for both teams
            team_a_runs = 0.0
            team_b_runs = 0.0
    
    # Get current team scores
    team_a_score = get_team_score(team_a, team_scores_data)
    team_b_score = get_team_score(team_b, team_scores_data)
    
    # Calculate winning probability for team A (away team)
    win_probability = calculate_winning_probability(team_a_runs, team_b_runs, team_a_score, team_b_score)
    
    # Convert to MLB odds format
    prediction_odds = convert_to_mlb_odds(win_probability)
    
    # Get prediction over/under if available
    prediction_overunder = None
    if team_pair in team_runs_data:
        prediction_overunder = team_runs_data[team_pair]['prediction_overunder']
    elif reverse_pair in team_runs_data:
        prediction_overunder = team_runs_data[reverse_pair]['prediction_overunder']
    
    return (team_a_runs, team_b_runs, prediction_odds, prediction_overunder)

def load_team_scores_data():
    """
    Load team scores data from mlb_2024_teams_score.csv
    Returns a dictionary mapping team names to their scores
    """
    team_scores = {}
    team_scores_file = "data/mlb_2024_teams_score.csv"
    
    if not os.path.exists(team_scores_file):
        print(f"Warning: {team_scores_file} not found. Team scores data will be empty.")
        return team_scores
    
    try:
        with open(team_scores_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                team_name = row['Team'].strip()
                team_score = float(row['Team_Score']) if row['Team_Score'] else 0.0
                team_scores[team_name] = team_score
        
        print(f"Loaded team scores data for {len(team_scores)} teams")
        return team_scores
        
    except Exception as e:
        print(f"Error loading team scores data: {e}")
        return team_scores

def get_team_score(team_name, team_scores_data):
    """
    Get the team score for a specific team
    Returns 0.0 if no data is found
    """
    return team_scores_data.get(team_name, 0.0)

def fetch_mlb_odds_by_date(date_str):
    """
    Fetch MLB odds data for a specific date from sportsdata.io API
    """
    url = f"{SPORTSDATA_BASE_URL}/GamesByDate/{date_str}"
    headers = {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_API_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def parse_odds_data(odds_data):
    """
    Parse the odds data and extract only the required fields
    """
    parsed_games = []
    
    if not odds_data:
        return parsed_games
    
    for game in odds_data:
        try:
            # Extract only the required fields
            game_info = {
                'GameID': game.get('GameID'),
                'DateTime': game.get('DateTime'),
                'AwayTeam': game.get('AwayTeam'),
                'HomeTeam': game.get('HomeTeam')
            }
            
            parsed_games.append(game_info)
            
        except Exception as e:
            print(f"Error parsing game {game.get('GameID', 'Unknown')}: {e}")
            continue
    
    return parsed_games

def save_to_csv(games_data, filename, team_runs_data, team_scores_data):
    """
    Save the parsed odds data to a CSV file in the format matching the uploaded image
    """
    if not games_data:
        print("No data to save")
        return
    
    # Create results folder if it doesn't exist
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        print(f"Created results directory: {results_dir}")
    
    # Full path for the CSV file
    full_path = os.path.join(results_dir, filename)
    
    try:
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Write header with new columns
            csvfile.write("GameID,DateTime,Away/Home Team,Team Runs,Team Score,Prediction Odds,Prediction OverUnder\n")
            
            # Write data in the format matching the uploaded image
            for game in games_data:
                away_team = game['AwayTeam']
                home_team = game['HomeTeam']
                
                # Get team runs data and prediction data
                away_runs, home_runs, prediction_odds, prediction_overunder = get_team_runs(away_team, home_team, team_runs_data, team_scores_data)
                
                # Get team scores data
                away_score = get_team_score(away_team, team_scores_data)
                home_score = get_team_score(home_team, team_scores_data)
                
                # First row: GameID, DateTime, AwayTeam, AwayTeam Runs, AwayTeam Score, Prediction Odds, Prediction OverUnder
                away_runs_str = f"{away_runs:.1f}" if away_runs is not None else "0.0"
                away_score_str = f"{away_score:.1f}" if away_score is not None else "0.0"
                prediction_odds_str = format_odds_range(prediction_odds) if prediction_odds is not None else "0 - 18"
                prediction_overunder_str = prediction_overunder if prediction_overunder else ""
                csvfile.write(f"{game['GameID']},{game['DateTime']},{away_team},{away_runs_str},{away_score_str},{prediction_odds_str},{prediction_overunder_str}\n")
                
                # Second row: empty GameID, empty DateTime, HomeTeam, HomeTeam Runs, HomeTeam Score, mirrored Prediction Odds, empty Prediction OverUnder
                home_runs_str = f"{home_runs:.1f}" if home_runs is not None else "0.0"
                home_score_str = f"{home_score:.1f}" if home_score is not None else "0.0"
                mirrored_odds_str = invert_odds_range(prediction_odds_str)
                csvfile.write(f",,{home_team},{home_runs_str},{home_score_str},{mirrored_odds_str},\n")
        
        print(f"Data successfully saved to {full_path}")
        print(f"Total games saved: {len(games_data)}")
        
        # Print some sample data for verification
        print("\nSample data verification:")
        for i, game in enumerate(games_data[:3]):  # Show first 3 games
            away_team = game['AwayTeam']
            home_team = game['HomeTeam']
            away_runs, home_runs, prediction_odds, prediction_overunder = get_team_runs(away_team, home_team, team_runs_data, team_scores_data)
            away_score = get_team_score(away_team, team_scores_data)
            home_score = get_team_score(home_team, team_scores_data)
            print(f"  Game {i+1}: {away_team} vs {home_team}")
            print(f"    {away_team} runs: {away_runs:.1f}, score: {away_score:.1f}")
            print(f"    {home_team} runs: {home_runs:.1f}, score: {home_score:.1f}")
            print(f"    Prediction Odds: {prediction_odds:.1f}, Over/Under: {prediction_overunder}")
        
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def calculate_winning_probability(away_runs, home_runs, away_score, home_score):
    """
    Calculate winning probability for away team based on:
    - Historical runs between teams (70% weight)
    - Current team scoring capability (30% weight)
    Returns probability between 0.1 and 0.9
    """
    # If no historical data, use only team scores
    if away_runs == 0 and home_runs == 0:
        total_score = away_score + home_score
        if total_score == 0:
            return 0.5  # Default to 50/50
        return max(min(away_score / total_score, 0.9), 0.1)
    
    # Calculate historical win probability
    total_runs = away_runs + home_runs
    if total_runs == 0:
        historical_prob = 0.5
    else:
        historical_prob = away_runs / total_runs
    
    # Calculate current score probability
    total_score = away_score + home_score
    if total_score == 0:
        score_prob = 0.5
    else:
        score_prob = away_score / total_score
    
    # Weighted average: 60% historical, 40% current
    final_prob = (0.6 * historical_prob) + (0.4 * score_prob)
    
    # Ensure probability is between 0.1 and 0.9
    return max(min(final_prob, 0.9), 0.1)

def convert_to_mlb_odds(win_probability):
    """
    Convert winning probability to MLB moneyline odds format
    Returns positive odds for underdogs, negative for favorites
    """
    if win_probability >= 0.5:
        # Favorite (negative odds)
        # Formula: (probability / (1 - probability)) * -100
        odds = (win_probability / (1 - win_probability)) * -100
        return max(round(odds), -1000)  # Cap at -1000
    else:
        # Underdog (positive odds)
        # Formula: ((1 - probability) / probability) * 100
        odds = ((1 - win_probability) / win_probability) * 100
        return min(round(odds), 1000)  # Cap at +1000

def format_odds_range(odds_value, scale=18):
    """
    Format a single MLB moneyline odds value into a range using a scale.
    Examples:
      111 -> "111 to 129"   (111 to 111+18)
     -103 -> "-103 to -121" (-103 to -103-18)
    """
    base = int(odds_value)
    if base >= 0:
        return f"{base} to {base + scale}"
    else:
        return f"{base} to {base - scale}"

def invert_odds_range(odds_range_str):
    """
    Invert the signs of an odds range string like "111 to 129" <-> "-111 to -129".
    Returns the original string if parsing fails.
    """
    try:
        parts = odds_range_str.split(" to ")
        if len(parts) != 2:
            return odds_range_str
        a = int(parts[0])
        b = int(parts[1])
        return f"{-a} to {-b}"
    except Exception:
        return odds_range_str

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