import requests
import json
import csv
import os
import random
from datetime import datetime
from config import SPORTSDATA_API_KEY, SPORTSDATA_BASE_URL

def fetch_2024_team_records(teams_data):
    """
    Fetch 2024 match records (runs/hits) for teams participating in matches on a given date
    
    Args:
        teams_data (list): List of dictionaries containing game information with:
            - GameID: Unique game identifier
            - DateTime: Game date and time
            - AwayTeam: Away team abbreviation
            - HomeTeam: Home team abbreviation
    
    Returns:
        dict: Dictionary with team records organized by game and team
    """
    
    # API endpoint for 2024 games
    url = f"{SPORTSDATA_BASE_URL}/Games/2024"
    headers = {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_API_KEY
    }
    
    try:
        print(f"Fetching 2024 games data from: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        games_2024 = response.json()
        print(f"Successfully fetched {len(games_2024)} games from 2024")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching 2024 games data: {e}")
        return None
    
    # Extract unique teams from the input data
    unique_teams = set()
    for game in teams_data:
        unique_teams.add(game['AwayTeam'])
        unique_teams.add(game['HomeTeam'])
    
    print(f"Teams to find records for: {', '.join(sorted(unique_teams))}")
    
    # Organize 2024 games by team
    team_games_2024 = {}
    for team in unique_teams:
        team_games_2024[team] = []
    
    # Filter 2024 games by teams we're interested in
    for game in games_2024:
        away_team = game.get('AwayTeam')
        home_team = game.get('HomeTeam')
        
        if away_team in unique_teams:
            team_games_2024[away_team].append({
                'GameID': game.get('GameID'),
                'DateTime': game.get('DateTime'),
                'Opponent': home_team,
                'IsAway': True,
                'Runs': game.get('AwayTeamRuns'),
                'Hits': game.get('AwayTeamHits'),
                'GameDate': game.get('DateTime')[:10] if game.get('DateTime') else None
            })
        
        if home_team in unique_teams:
            team_games_2024[home_team].append({
                'GameID': game.get('GameID'),
                'DateTime': game.get('DateTime'),
                'Opponent': away_team,
                'IsAway': False,
                'Runs': game.get('HomeTeamRuns'),
                'Hits': game.get('HomeTeamHits'),
                'GameDate': game.get('DateTime')[:10] if game.get('DateTime') else None
            })
    
    # Create the final result structure matching the image format
    result = []
    
    for game in teams_data:
        game_id = game['GameID']
        game_datetime = game['DateTime']
        away_team = game['AwayTeam']
        home_team = game['HomeTeam']
        
        # Find 2024 records for away team
        away_records = team_games_2024.get(away_team, [])
        
        # Find 2024 records for home team
        home_records = team_games_2024.get(home_team, [])
        
        # Create game entry with team records
        game_entry = {
            'GameID': game_id,
            'DateTime': game_datetime,
            'AwayTeam': away_team,
            'HomeTeam': home_team,
            'AwayTeamRecords': away_records,
            'HomeTeamRecords': home_records
        }
        
        result.append(game_entry)
    
    return result

def get_all_2024_head_to_head_matchups():
    """
    Get all head-to-head matchups between all teams for the entire 2024 season
    
    Returns:
        dict: Dictionary with team pairs as keys and their matchups as values
    """
    
    # API endpoint for 2024 games
    url = f"{SPORTSDATA_BASE_URL}/Games/2024"
    headers = {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_API_KEY
    }
    
    try:
        print("Fetching all 2024 games data to find all head-to-head matchups...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        games_data = response.json()
        print(f"Successfully fetched {len(games_data)} games from 2024")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching 2024 games data: {e}")
        return None
    
    # Dictionary to store all head-to-head matchups
    all_matchups = {}
    
    # Process each game
    for game in games_data:
        away_team = game.get('AwayTeam')
        home_team = game.get('HomeTeam')
        
        if not away_team or not home_team:
            continue
        
        # Create a unique key for the team pair (alphabetical order)
        team_pair = tuple(sorted([away_team, home_team]))
        team_pair_key = f"{team_pair[0]}_vs_{team_pair[1]}"
        
        if team_pair_key not in all_matchups:
            all_matchups[team_pair_key] = []
        
        # Add game information
        game_info = {
            'GameID': game.get('GameID'),
            'DateTime': game.get('DateTime'),
            'GameDate': game.get('DateTime')[:10] if game.get('DateTime') else None,
            'AwayTeam': away_team,
            'HomeTeam': home_team,
            'AwayTeamRuns': game.get('AwayTeamRuns'),
            'AwayTeamHits': game.get('AwayTeamHits'),
            'HomeTeamRuns': game.get('HomeTeamRuns'),
            'HomeTeamHits': game.get('HomeTeamHits'),
            'Venue': game.get('Venue', 'Unknown'),
            'Status': game.get('Status', 'Unknown')
        }
        
        all_matchups[team_pair_key].append(game_info)
    
    print(f"Found head-to-head matchups for {len(all_matchups)} team pairs")
    
    return all_matchups


def save_matchups(all_matchups, filename="mlb_2024_head_to_head.csv"):
    """
    Save matchups in the exact format shown in the uploaded image
    Format: Team Pair, GameID, GameDate, TeamA runs, TeamB runs, Home Team, Away Team, TeamA Score, TeamB Score
    
    Args:
        all_matchups (dict): Dictionary with team pairs and their matchups
        filename (str): Name of the CSV file to save
    """
    
    # Create data folder if it doesn't exist
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory: {data_dir}")
    
    # Full path for the CSV file
    full_path = os.path.join(data_dir, filename)
    
    try:
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header row matching the exact image format with TeamA Score, TeamB Score, and Prediction_OverUnder
            header = ["Team Pair", "GameID", "GameDate", "TeamA runs", "TeamB runs", "Home Team", "Away Team", "TeamA Score", "TeamB Score", "Prediction_OverUnder"]
            writer.writerow(header)
            
            # Write data rows
            for team_pair_key, matchups in all_matchups.items():
                # Sort matchups by date
                matchups.sort(key=lambda x: x['GameDate'] if x['GameDate'] else '')
                
                # Format team pair name (e.g., "LAD vs SD")
                team_pair_name = team_pair_key.replace('_', ' vs ')
                
                # Calculate total scores for this team pair with home/away adjustments
                team_a_total_score = 0
                team_b_total_score = 0
                game_count = len(matchups)
                
                # Extract the two teams from the pair
                teams_in_pair = team_pair_key.split('_')
                team_a = teams_in_pair[0]  # First team (e.g., "LAD")
                team_b = teams_in_pair[2]  # Second team (e.g., "SD")
                
                # Calculate total scores for all games in this pair with home/away multipliers
                for matchup in matchups:
                    if matchup['AwayTeam'] == team_a:
                        # TeamA was away team - multiply by 1.1
                        runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                        team_a_total_score += runs * 1.1
                        
                        # TeamB was home team - multiply by 0.9
                        runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                        team_b_total_score += runs * 0.9
                        
                    elif matchup['HomeTeam'] == team_a:
                        # TeamA was home team - multiply by 0.9
                        runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                        team_a_total_score += runs * 0.9
                        
                        # TeamB was away team - multiply by 1.1
                        runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                        team_b_total_score += runs * 1.1
                        
                    elif matchup['AwayTeam'] == team_b:
                        # TeamB was away team - multiply by 1.1
                        runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                        team_b_total_score += runs * 1.1
                        
                        # TeamA was home team - multiply by 0.9
                        runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                        team_a_total_score += runs * 0.9
                        
                    elif matchup['HomeTeam'] == team_b:
                        # TeamB was home team - multiply by 0.9
                        runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                        team_b_total_score += runs * 0.9
                        
                        # TeamA was away team - multiply by 1.1
                        runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                        team_a_total_score += runs * 1.1
                
                # Divide by game count to get average adjusted runs per game
                if game_count > 0:
                    team_a_total_score = round(team_a_total_score / game_count, 2)
                    team_b_total_score = round(team_b_total_score / game_count, 2)
                
                for i, matchup in enumerate(matchups):
                    # Convert date format from YYYY-MM-DD to M/D/YYYY
                    game_date = ""
                    if matchup['GameDate']:
                        try:
                            date_obj = datetime.strptime(matchup['GameDate'], '%Y-%m-%d')
                            game_date = date_obj.strftime('%-m/%-d/%Y')  # M/D/YYYY format
                        except:
                            game_date = matchup['GameDate']  # Keep original if conversion fails
                    
                    # Determine runs for TeamA and TeamB based on who they are in this game
                    team_a_runs = 0
                    team_b_runs = 0
                    
                    if matchup['AwayTeam'] == team_a:
                        # TeamA was away team
                        team_a_runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                        team_b_runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                    elif matchup['HomeTeam'] == team_a:
                        # TeamA was home team
                        team_a_runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                        team_b_runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                    elif matchup['AwayTeam'] == team_b:
                        # TeamB was away team
                        team_a_runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                        team_b_runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                    elif matchup['HomeTeam'] == team_b:
                        # TeamB was home team
                        team_a_runs = matchup['AwayTeamRuns'] if matchup['AwayTeamRuns'] is not None else 0
                        team_b_runs = matchup['HomeTeamRuns'] if matchup['HomeTeamRuns'] is not None else 0
                    
                    # For first game of a team pair, show the team pair name and scores
                    # For subsequent games, leave them blank (as shown in the image)
                    if i == 0:
                        team_pair_display = team_pair_name
                        team_a_score_display = team_a_total_score
                        team_b_score_display = team_b_total_score
                        # Prediction as total of TeamA and TeamB scores (no absolute error range)
                        prediction_overunder = round(team_a_total_score + team_b_total_score, 2)
                    else:
                        team_pair_display = ""
                        team_a_score_display = ""
                        team_b_score_display = ""
                        prediction_overunder = ""
                    
                    row = [
                        team_pair_display,  # Team Pair (only for first game)
                        matchup['GameID'],  # GameID
                        game_date,         # GameDate in M/D/YYYY format
                        team_a_runs,       # TeamA runs (first team in pair)
                        team_b_runs,       # TeamB runs (second team in pair)
                        matchup['HomeTeam'],  # Home Team
                        matchup['AwayTeam'],  # Away Team
                        team_a_score_display,  # TeamA Score (only for first game)
                        team_b_score_display,  # TeamB Score (only for first game)
                        prediction_overunder   # Prediction_OverUnder (only for first game)
                    ]
                    writer.writerow(row)
        
        print(f"Successfully saved matchups in image format to {full_path}")
        print(f"Format exactly matches the uploaded image structure with TeamA Score, TeamB Score, and Prediction_OverUnder")
        print(f"Columns: Team Pair, GameID, GameDate, TeamA runs, TeamB runs, Home Team, Away Team, TeamA Score, TeamB Score, Prediction_OverUnder")
        print(f"Scoring: Average adjusted runs per game with home/away multipliers (Home: ×0.9, Away: ×1.1)")
        print(f"Prediction_OverUnder: Total projected runs (TeamA Score + TeamB Score)")
        
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def get_head_to_head_matchups(team1, team2, year=2024):
    """
    Get all head-to-head matchups between two specific teams for a given year
    
    Args:
        team1 (str): First team abbreviation (e.g., 'TEX')
        team2 (str): Second team abbreviation (e.g., 'KC')
        year (int): Year to search for (default: 2024)
    
    Returns:
        list: List of head-to-head games between the two teams
    """
    
    # API endpoint for the specified year
    url = f"{SPORTSDATA_BASE_URL}/Games/{year}"
    headers = {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_API_KEY
    }
    
    try:
        print(f"Fetching {year} games data to find {team1} vs {team2} matchups...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        games_data = response.json()
        print(f"Successfully fetched {len(games_data)} games from {year}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {year} games data: {e}")
        return None
    
    # Find head-to-head matchups
    head_to_head_games = []
    
    for game in games_data:
        away_team = game.get('AwayTeam')
        home_team = game.get('HomeTeam')
        
        # Check if this is a matchup between the two teams (in either order)
        if (away_team == team1 and home_team == team2) or (away_team == team2 and home_team == team1):
            game_info = {
                'GameID': game.get('GameID'),
                'DateTime': game.get('DateTime'),
                'GameDate': game.get('DateTime')[:10] if game.get('DateTime') else None,
                'AwayTeam': away_team,
                'HomeTeam': home_team,
                'AwayTeamRuns': game.get('AwayTeamRuns'),
                'AwayTeamHits': game.get('AwayTeamHits'),
                'HomeTeamRuns': game.get('HomeTeamRuns'),
                'HomeTeamHits': game.get('HomeTeamHits'),
                'Venue': game.get('Venue', 'Unknown'),
                'Status': game.get('Status', 'Unknown')
            }
            head_to_head_games.append(game_info)
    
    print(f"Found {len(head_to_head_games)} head-to-head matchups between {team1} and {team2} in {year}")
    
    return head_to_head_games

def display_head_to_head_matchups(matchups, team1, team2, year=2024):
    """
    Display head-to-head matchups in a readable format
    
    Args:
        matchups (list): List of head-to-head games
        team1 (str): First team name
        team2 (str): Second team name
        year (int): Year of the matchups
    """
    
    if not matchups:
        print(f"No head-to-head matchups found between {team1} and {team2} in {year}")
        return
    
    print(f"\n" + "="*80)
    print(f"{year} HEAD-TO-HEAD MATCHUPS: {team1} vs {team2}")
    print("="*80)
    
    # Sort by date
    matchups.sort(key=lambda x: x['GameDate'] if x['GameDate'] else '')
    
    for i, game in enumerate(matchups, 1):
        print(f"\nGame {i}:")
        print(f"  Date: {game['GameDate']}")
        print(f"  Venue: {game['Venue']}")
        print(f"  Status: {game['Status']}")
        print(f"  {game['AwayTeam']} @ {game['HomeTeam']}")
        
        # Display runs and hits
        if game['AwayTeamRuns'] is not None and game['HomeTeamRuns'] is not None:
            print(f"  Final Score: {game['AwayTeam']} {game['AwayTeamRuns']} - {game['HomeTeam']} {game['HomeTeamRuns']}")
            print(f"  {game['AwayTeam']}: {game['AwayTeamRuns']} Runs, {game['AwayTeamHits']} Hits")
            print(f"  {game['HomeTeam']}: {game['HomeTeamRuns']} Runs, {game['HomeTeamHits']} Hits")
        else:
            print("  Score: Not available")
        
        print("-" * 50)
    
    # Summary statistics
    print(f"\nSummary for {year}:")
    print(f"  Total games: {len(matchups)}")
    
    # Count wins for each team
    team1_wins = 0
    team2_wins = 0
    
    for game in matchups:
        if game['AwayTeamRuns'] is not None and game['HomeTeamRuns'] is not None:
            if game['AwayTeam'] == team1:
                if game['AwayTeamRuns'] > game['HomeTeamRuns']:
                    team1_wins += 1
                else:
                    team2_wins += 1
            else:  # team1 is home team
                if game['HomeTeamRuns'] > game['AwayTeamRuns']:
                    team1_wins += 1
                else:
                    team2_wins += 1
    
    print(f"  {team1} wins: {team1_wins}")
    print(f"  {team2} wins: {team2_wins}")

def display_team_records(team_records):
    """
    Display the team records in a readable format
    
    Args:
        team_records (list): List of team records from fetch_2024_team_records
    """
    
    if not team_records:
        print("No team records to display")
        return
    
    print("\n" + "="*80)
    print("2024 TEAM RECORDS FOR GAMES ON SPECIFIED DATE")
    print("="*80)
    
    for game in team_records:
        print(f"\nGame ID: {game['GameID']}")
        print(f"Date/Time: {game['DateTime']}")
        print(f"Away Team: {game['AwayTeam']}")
        print(f"Home Team: {game['HomeTeam']}")
        print("-" * 50)
        
        # Display away team records
        away_records = game['AwayTeamRecords']
        if away_records:
            print(f"{game['AwayTeam']} 2024 Records:")
            for record in away_records[:5]:  # Show first 5 records
                date_str = record['GameDate'] if record['GameDate'] else 'Unknown'
                runs = record['Runs'] if record['Runs'] is not None else 'N/A'
                hits = record['Hits'] if record['Hits'] is not None else 'N/A'
                opponent = record['Opponent']
                location = "Away" if record['IsAway'] else "Home"
                print(f"  {date_str}: {runs} Runs, {hits} Hits vs {opponent} ({location})")
        else:
            print(f"{game['AwayTeam']}: No 2024 records found")
        
        print()
        
        # Display home team records
        home_records = game['HomeTeamRecords']
        if home_records:
            print(f"{game['HomeTeam']} 2024 Records:")
            for record in home_records[:5]:  # Show first 5 records
                date_str = record['GameDate'] if record['GameDate'] else 'Unknown'
                runs = record['Runs'] if record['Runs'] is not None else 'N/A'
                hits = record['Hits'] if record['Hits'] is not None else 'N/A'
                opponent = record['Opponent']
                location = "Away" if record['IsAway'] else "Home"
                print(f"  {date_str}: {runs} Runs, {hits} Hits vs {opponent} ({location})")
        else:
            print(f"{game['HomeTeam']}: No 2024 records found")
        
        print("-" * 50)

def get_team_records_for_date(date_str, teams_data):
    """
    Main function to get 2024 team records for games on a specific date
    
    Args:
        date_str (str): Date in YYYY-MM-DD format
        teams_data (list): List of games for that date
    
    Returns:
        dict: Team records organized by game
    """
    
    print(f"Fetching 2024 team records for games on {date_str}")
    print(f"Number of games to process: {len(teams_data)}")
    
    # Fetch the 2024 team records
    team_records = fetch_2024_team_records(teams_data)
    
    if team_records:
        print(f"Successfully retrieved records for {len(team_records)} games")
        return team_records
    else:
        print("Failed to retrieve team records")
        return None

def get_team_records_for_scheduled_games(date_str):
    """
    Integration function: Fetch games for a specific date and then get their 2024 team records
    
    Args:
        date_str (str): Date in YYYY-MM-DD format
    
    Returns:
        dict: Team records organized by game
    """
    
    # First, fetch the games scheduled for the specified date
    url = f"{SPORTSDATA_BASE_URL}/GamesByDate/{date_str}"
    headers = {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_API_KEY
    }
    
    try:
        print(f"Fetching games scheduled for {date_str}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        scheduled_games = response.json()
        print(f"Found {len(scheduled_games)} games scheduled for {date_str}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching scheduled games: {e}")
        return None
    
    if not scheduled_games:
        print(f"No games scheduled for {date_str}")
        return None
    
    # Parse the scheduled games to extract team information
    teams_data = []
    for game in scheduled_games:
        game_info = {
            'GameID': game.get('GameID'),
            'DateTime': game.get('DateTime'),
            'AwayTeam': game.get('AwayTeam'),
            'HomeTeam': game.get('HomeTeam')
        }
        teams_data.append(game_info)
    
    # Now get the 2024 team records for these teams
    return get_team_records_for_date(date_str, teams_data)

def generate_complete_2024_dataset():
    """
    Generate the complete 2024 dataset with all head-to-head matchups
    and save it in the image format with TeamA Score and TeamB Score columns
    """
    
    print("Generating Complete 2024 MLB Head-to-Head Dataset")
    print("=" * 60)
    
    # Get all head-to-head matchups for 2024
    all_matchups = get_all_2024_head_to_head_matchups()
    
    if not all_matchups:
        print("Failed to fetch matchups data")
        return
    
    print(f"\nSuccessfully collected data for {len(all_matchups)} team pairs")
    
    # Save in image format with scoring columns
    print("\nSaving in image format with TeamA Score and TeamB Score columns...")
    print("Using average runs per game (sum divided by game count)")
    save_matchups(all_matchups, "mlb_2024_head_to_head.csv")
    
    print("\nDataset generation complete!")
    print("File saved: mlb_2024_head_to_head.csv")
    print("Location: 'data' folder")
    print("Includes average adjusted scoring: Home team runs ×0.9, Away team runs ×1.1, then averaged")



# Example usage function
def example_usage():
    """
    Example of how to use the team records function
    """
    
    # Sample teams data (this would come from your main odds fetching function)
    sample_teams_data = [
        {
            'GameID': 73692,
            'DateTime': '2025-08-21T13:10:00',
            'AwayTeam': 'ATH',
            'HomeTeam': 'MIN'
        },
        {
            'GameID': 76222,
            'DateTime': '2025-08-21T14:10:00',
            'AwayTeam': 'TEX',
            'HomeTeam': 'KC'
        }
    ]
    
    # Get team records for a specific date
    date_str = '2025-08-21'
    team_records = get_team_records_for_date(date_str, sample_teams_data)
    
    if team_records:
        # Display the records
        display_team_records(team_records)
        
        # You can also access specific data programmatically
        for game in team_records:
            print(f"\nGame {game['GameID']}:")
            print(f"  {game['AwayTeam']} has {len(game['AwayTeamRecords'])} 2024 records")
            print(f"  {game['HomeTeam']} has {len(game['HomeTeamRecords'])} 2024 records")

def example_head_to_head_usage():
    """
    Example of how to use the head-to-head matchups function
    """
    
    # Example: Get all TEX vs KC matchups from 2024
    print("Example: Getting all TEX vs KC matchups from 2024")
    print("=" * 60)
    
    team1 = "TEX"
    team2 = "KC"
    year = 2024
    
    # Get head-to-head matchups
    matchups = get_head_to_head_matchups(team1, team2, year)
    
    if matchups:
        # Display the matchups
        display_head_to_head_matchups(matchups, team1, team2, year)
        
        # You can also access specific data programmatically
        print(f"\nProgrammatic access example:")
        for game in matchups:
            print(f"  Game {game['GameID']}: {game['GameDate']} - {game['AwayTeam']} {game['AwayTeamRuns']} @ {game['HomeTeam']} {game['HomeTeamRuns']}")
    else:
        print(f"No matchups found between {team1} and {team2} in {year}")

def example_integration_usage():
    """
    Example of how to use the integration function
    """
    
    # Example: Get 2024 team records for games scheduled on a specific date
    date_str = '2025-08-21'
    print(f"Getting 2024 team records for games scheduled on {date_str}")
    
    team_records = get_team_records_for_scheduled_games(date_str)
    
    if team_records:
        display_team_records(team_records)
    else:
        print("No team records found")



if __name__ == "__main__":
    # Run the examples
    print("Example 1: Head-to-Head Matchups (TEX vs KC)")
    print("-" * 40)
    example_head_to_head_usage()
    
    print("\n\nExample 2: Using sample data")
    print("-" * 40)
    example_usage()
    
    print("\n\nExample 3: Integration with API")
    print("-" * 40)
    example_integration_usage()
    
    print("\n\nExample 4: Generate Complete 2024 Dataset")
    print("-" * 40)
    generate_complete_2024_dataset()
    
    print("\n\nExample 5: Generate Dataset for Specific Date")
    print("-" * 40)