import requests
import pandas as pd
import json
import argparse
from datetime import datetime
import os

API_KEY = "3d8b7ea85cf946f682ff8bed1279f0c1"
BASE_URL = "https://api.sportsdata.io/api/mlb/fantasy/json"
RESULT_DIR = "data"

def fetch_player_season_projections():
    """Fetch player season projection stats for 2024"""
    url = f"{BASE_URL}/PlayerSeasonProjectionStats/2024"
    headers = {'Ocp-Apim-Subscription-Key': API_KEY}
    
    try:
        print(f"Fetching 2024 season projections for all players...")
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        print(f"Found {len(data)} players with 2024 projections")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching 2024 season projections: {e}")
        return None

def extract_six_factors_from_player(player):
    """Extract only the 6 key factors from player season projection data"""
    
    # Validate team name first
    team = player.get('Team', '')
    if not team or pd.isna(team) or team.strip() == '':
        return None  # Return None for players without team names
    
    position = player.get('Position', '')
    is_pitcher = position == 'P' or 'P' in position
    
    # 1. HITTING ABILITY
    hitting_score = 0
    hitting_factors = {}
    
    if pd.notna(player.get('BattingAverage')):
        hitting_factors['Batting Average'] = f"{player['BattingAverage']:.3f}"
        hitting_score += player['BattingAverage'] * 20  # Reduced from 50
    
    if pd.notna(player.get('OnBasePercentage')):
        hitting_factors['On-Base %'] = f"{player['OnBasePercentage']:.3f}"
        hitting_score += player['OnBasePercentage'] * 10  # Reduced from 25
    
    if pd.notna(player.get('SluggingPercentage')):
        hitting_factors['Slugging %'] = f"{player['SluggingPercentage']:.3f}"
        hitting_score += player['SluggingPercentage'] * 6  # Reduced from 15
    
    if pd.notna(player.get('HomeRuns')):
        hitting_factors['Home Runs'] = int(player['HomeRuns'])
        hitting_score += player['HomeRuns'] * 0.8  # Reduced from 2
    
    if pd.notna(player.get('RunsBattedIn')):
        hitting_factors['RBI'] = int(player['RunsBattedIn'])
        hitting_score += player['RunsBattedIn'] * 0.4  # Reduced from 1
    
    if pd.notna(player.get('StolenBases')):
        hitting_factors['Stolen Bases'] = int(player['StolenBases'])
        hitting_score += player['StolenBases'] * 0.6  # Reduced from 1.5
    
    # 2. PITCHING ABILITY
    pitching_score = 0
    pitching_factors = {}
    
    if pd.notna(player.get('EarnedRunAverage')):
        era = player['EarnedRunAverage']
        if era > 0:
            era_score = max(0, (6.0 - era) * 4)  # Reduced from 10
            pitching_factors['ERA'] = f"{era:.2f}"
            pitching_score += era_score
    
    if pd.notna(player.get('InningsPitched')):
        innings = player['InningsPitched']
        pitching_factors['Innings'] = f"{innings:.1f}"
        pitching_score += innings * 0.2  # Reduced from 0.5
    
    if pd.notna(player.get('PitchingStrikeouts')):
        k_count = player['PitchingStrikeouts']
        pitching_factors['Strikeouts'] = int(k_count)
        pitching_score += k_count * 0.2  # Reduced from 0.5
    
    if pd.notna(player.get('WalksHitsPerInningsPitched')):
        whip = player['WalksHitsPerInningsPitched']
        if whip > 0:
            whip_score = max(0, (2.0 - whip) * 6)  # Reduced from 15
            pitching_factors['WHIP'] = f"{whip:.3f}"
            pitching_score += whip_score
    
    if pd.notna(player.get('Saves')):
        saves = player['Saves']
        pitching_factors['Saves'] = int(saves)
        pitching_score += saves * 0.8  # Reduced from 2
    
    # 3. CLUTCH PERFORMANCE
    clutch_score = 0
    clutch_factors = {}
    
    # RBI efficiency (RBI per at-bat)
    if pd.notna(player.get('RunsBattedIn')) and pd.notna(player.get('AtBats')):
        rbi = player['RunsBattedIn']
        at_bats = player['AtBats']
        if at_bats > 0:
            rbi_per_ab = rbi / at_bats
            clutch_factors['RBI/AB'] = f"{rbi_per_ab:.3f}"
            clutch_score += rbi_per_ab * 20  # Reduced from 50
    
    # Extra base hits (doubles + triples)
    if pd.notna(player.get('Doubles')):
        doubles = player['Doubles']
        clutch_factors['Doubles'] = int(doubles)
        clutch_score += doubles * 0.6  # Reduced from 1.5
    
    if pd.notna(player.get('Triples')):
        triples = player['Triples']
        clutch_factors['Triples'] = int(triples)
        clutch_score += triples * 1.0  # Reduced from 2.5
    
    # Walks (patience at plate)
    if pd.notna(player.get('Walks')):
        walks = player['Walks']
        clutch_factors['Walks'] = int(walks)
        clutch_score += walks * 0.4  # Reduced from 1
    
    # For pitchers: Quality starts and wins
    if is_pitcher:
        if pd.notna(player.get('Wins')):
            wins = player['Wins']
            clutch_factors['Wins'] = int(wins)
            clutch_score += wins * 1.6  # Reduced from 4
        
        if pd.notna(player.get('QualityStarts')):
            qs = player['QualityStarts']
            clutch_factors['Quality Starts'] = int(qs)
            clutch_score += qs * 1.0  # Reduced from 2.5
    
    # 4. SPEED & RANGE (replacing bullpen)
    speed_score = 0
    speed_factors = {}
    
    # Stolen base success rate and attempts
    if pd.notna(player.get('StolenBases')):
        sb = player['StolenBases']
        speed_factors['Stolen Bases'] = int(sb)
        speed_score += sb * 0.8  # Reduced from 2
    
    # Caught stealing (penalty for poor baserunning)
    if pd.notna(player.get('CaughtStealing')):
        cs = player['CaughtStealing']
        speed_factors['Caught Stealing'] = int(cs)
        speed_score -= cs * 0.4  # Reduced from 1
    
    # Triples (indicator of speed and range)
    if pd.notna(player.get('Triples')):
        triples = player['Triples']
        speed_factors['Triples'] = int(triples)
        speed_score += triples * 1.2  # Reduced from 3
    
    # For pitchers: Pickoffs and fielding range
    if is_pitcher:
        if pd.notna(player.get('Pickoffs')):
            pickoffs = player['Pickoffs']
            speed_factors['Pickoffs'] = int(pickoffs)
            speed_score += pickoffs * 0.6  # Reduced from 1.5
    
    # 5. CURRENT FORM (using projected fantasy points)
    form_score = 0
    form_factors = {}
    
    if pd.notna(player.get('FantasyPoints')):
        fantasy_points = player['FantasyPoints']
        form_factors['Fantasy Points'] = round(fantasy_points, 1)
        form_score += fantasy_points * 0.02  # Reduced from 0.1
    
    if pd.notna(player.get('Runs')):
        runs = player['Runs']
        form_factors['Runs'] = int(runs)
        form_score += runs * 0.6  # Reduced from 1.5
    
    if pd.notna(player.get('Hits')):
        hits = player['Hits']
        form_factors['Hits'] = int(hits)
        form_score += hits * 0.4  # Reduced from 1
    
    if pd.notna(player.get('PitchingStrikeouts')):
        k_recent = player['PitchingStrikeouts']
        form_factors['Projected Ks'] = int(k_recent)
        form_score += k_recent * 0.3  # Reduced from 0.75
    
    # 6. CONSISTENCY SCORE (replacing injury risk)
    consistency_score = 0
    consistency_factors = {}
    
    # Batting average consistency (higher BA = more consistent)
    if pd.notna(player.get('BattingAverage')):
        ba = player['BattingAverage']
        if ba > 0.3:
            consistency_score += 4  # Reduced from 10
            consistency_factors['High BA'] = f"{ba:.3f}"
        elif ba > 0.25:
            consistency_score += 3  # Reduced from 7.5
            consistency_factors['Good BA'] = f"{ba:.3f}"
        elif ba > 0.2:
            consistency_score += 2  # Reduced from 5
            consistency_factors['Decent BA'] = f"{ba:.3f}"
    
    # On-base percentage consistency
    if pd.notna(player.get('OnBasePercentage')):
        obp = player['OnBasePercentage']
        if obp > 0.4:
            consistency_score += 3  # Reduced from 7.5
            consistency_factors['High OBP'] = f"{obp:.3f}"
        elif obp > 0.35:
            consistency_score += 2  # Reduced from 5
            consistency_factors['Good OBP'] = f"{obp:.3f}"
    
    # For pitchers: ERA consistency
    if is_pitcher and pd.notna(player.get('EarnedRunAverage')):
        era = player['EarnedRunAverage']
        if era < 3.0:
            consistency_score += 4  # Reduced from 10
            consistency_factors['Excellent ERA'] = f"{era:.2f}"
        elif era < 4.0:
            consistency_score += 3  # Reduced from 7.5
            consistency_factors['Good ERA'] = f"{era:.2f}"
        elif era < 5.0:
            consistency_score += 2  # Reduced from 5
            consistency_factors['Decent ERA'] = f"{era:.2f}"
    
    # Playing time consistency (projected AB/IP)
    if pd.notna(player.get('AtBats')) and player.get('AtBats', 0) > 400:
        consistency_score += 2  # Reduced from 5
        consistency_factors['High AB Projection'] = True
    
    if pd.notna(player.get('InningsPitched')) and player.get('InningsPitched', 0) > 150:
        consistency_score += 2  # Reduced from 5
        consistency_factors['High IP Projection'] = True
    
    # Calculate overall ability score with very conservative weights
    overall_score = (
        hitting_score * 0.35 +
        pitching_score * 0.35 +
        clutch_score * 0.15 +
        speed_score * 0.08 +
        form_score * 0.04 +
        consistency_score * 0.03
    )
    
    return {
        'Team': team,
        'Name': player.get('Name'),
        'Position': position,
        'PlayerType': 'Pitcher' if is_pitcher else 'Batter',
        
        # The 6 Key Factors Only
        'Hitting_Score': round(hitting_score, 1),
        'Pitching_Score': round(pitching_score, 1),
        'Clutch_Score': round(clutch_score, 1),
        'Speed_Score': round(speed_score, 1),
        'Form_Score': round(form_score, 1),
        'Consistency_Score': consistency_score,
        'Overall_Score': round(overall_score, 1),
        
        # Key factor details (simplified)
        'Hitting_Key': ' | '.join([f"{k}: {v}" for k, v in hitting_factors.items()]) if hitting_factors else '',
        'Pitching_Key': ' | '.join([f"{k}: {v}" for k, v in pitching_factors.items()]) if pitching_factors else '',
        'Clutch_Key': ' | '.join([f"{k}: {v}" for k, v in clutch_factors.items()]) if clutch_factors else '',
        'Speed_Key': ' | '.join([f"{k}: {v}" for k, v in speed_factors.items()]) if speed_factors else '',
        'Form_Key': ' | '.join([f"{k}: {v}" for k, v in form_factors.items()]) if form_factors else '',
        'Consistency_Key': ' | '.join([f"{k}: {v}" for k, v in consistency_factors.items()]) if consistency_factors else ''
    }

def fetch_six_factors_for_2024_season():
    """Fetch only the 6 key factors for all players for the 2024 season"""
    print(f"Fetching SIX KEY FACTORS for ALL TEAMS for 2024 SEASON...")
    
    # Fetch season projections
    projections = fetch_player_season_projections()
    
    if not projections:
        print(f"No player projections found for 2024 season")
        return [], projections
    
    all_players_six_factors = []
    
    # Process each player
    print(f"Processing {len(projections)} players...")
    
    filtered_count = 0
    for i, player in enumerate(projections):
        if i % 100 == 0:
            print(f"  Processed {i}/{len(projections)} players...")
        
        # Skip players with null or empty team names
        team = player.get('Team', '')
        if not team or pd.isna(team) or team.strip() == '':
            filtered_count += 1
            continue
        
        player_six_factors = extract_six_factors_from_player(player)
        if player_six_factors is not None:  # Only add players with valid team names
            all_players_six_factors.append(player_six_factors)
    
    print(f"Filtered out {filtered_count} players with null/empty team names")
    print(f"Remaining players: {len(all_players_six_factors)}")
    
    return all_players_six_factors, projections

def calculate_team_scores(players_data):
    """Calculate team scores based on the sum of all players' overall scores"""
    df = pd.DataFrame(players_data)
    
    # Calculate team scores by summing overall scores for each team
    team_scores = df.groupby('Team')['Overall_Score'].sum().reset_index()
    team_scores.columns = ['Team', 'Team_Score']
    
    # Round team scores to 1 decimal place
    team_scores['Team_Score'] = team_scores['Team_Score'].round(1)
    
    # Sort teams by score (highest first)
    team_scores = team_scores.sort_values('Team_Score', ascending=False)
    
    return team_scores

def add_team_scores_to_players(players_data):
    """Add team score column to each player's data"""
    df = pd.DataFrame(players_data)
    team_scores = calculate_team_scores(players_data)
    
    # Merge team scores with player data
    df_with_team_scores = df.merge(team_scores, on='Team', how='left')
    
    # Convert back to list of dictionaries
    return df_with_team_scores.to_dict('records')

def display_six_factors_summary(players_data, season="2024"):
    """Display a summary of the 6 key factors"""
    
    if not players_data:
        print("No player data to display")
        return
    
    df = pd.DataFrame(players_data)
    
    print(f"\n" + "="*80)
    print(f"SIX KEY FACTORS SUMMARY - {season} SEASON")
    print("="*80)
    
    # Sort by overall score
    df_sorted = df.sort_values('Overall_Score', ascending=False)
    
    print(f"\nTOP 20 PLAYERS BY OVERALL ABILITY:")
    print("-" * 80)
    
    for i, (_, player) in enumerate(df_sorted.head(20).iterrows()):
        team_score_info = f" | Team Score: {player['Team_Score']:>6.1f}" if 'Team_Score' in player else ""
        print(f"\n{i+1:2d}. {player['Name']:<20} ({player['Team']:<3}) - {player['Position']:<2}")
        print(f"     Overall Score: {player['Overall_Score']:>6.1f} | Type: {player['PlayerType']}{team_score_info}")
        
        # Show only the 6 key factors
        if player['Hitting_Score'] > 0:
            print(f"     🏏 Hitting: {player['Hitting_Score']:>6.1f} - {player['Hitting_Key']}")
        
        if player['Pitching_Score'] > 0:
            print(f"     ⚾ Pitching: {player['Pitching_Score']:>6.1f} - {player['Pitching_Key']}")
        
        if player['Clutch_Score'] > 0:
            print(f"     💪 Clutch: {player['Clutch_Score']:>6.1f} - {player['Clutch_Key']}")
        
        if player['Speed_Score'] != 0:
            print(f"     🏃 Speed: {player['Speed_Score']:>6.1f} - {player['Speed_Key']}")
        
        if player['Form_Score'] > 0:
            print(f"     📈 Form: {player['Form_Score']:>6.1f} - {player['Form_Key']}")
        
        if player['Consistency_Score'] > 0:
            print(f"     ⚙️  Consistency: {player['Consistency_Score']:>6.1f} - {player['Consistency_Key']}")
    
    # Summary statistics
    print(f"\n" + "="*80)
    print("SUMMARY OF SIX KEY FACTORS:")
    print("="*80)
    
    print(f"Total Players Analyzed: {len(df)}")
    print(f"Pitchers: {len(df[df['PlayerType'] == 'Pitcher'])}")
    print(f"Batters: {len(df[df['PlayerType'] == 'Batter'])}")
    
    # Display team rankings
    if 'Team_Score' in df.columns:
        team_scores = calculate_team_scores(players_data)
        print(f"\nTEAM RANKINGS BY TOTAL PLAYER SCORES:")
        print("-" * 50)
        for i, (_, team) in enumerate(team_scores.iterrows()):
            print(f"{i+1:2d}. {team['Team']:<3} - Total Score: {team['Team_Score']:>8.1f}")
    
    print(f"\nScore Ranges:")
    print(f"Hitting: {df['Hitting_Score'].min():.1f} - {df['Hitting_Score'].max():.1f}")
    print(f"Pitching: {df['Pitching_Score'].min():.1f} - {df['Pitching_Score'].max():.1f}")
    print(f"Clutch: {df['Clutch_Score'].min():.1f} - {df['Clutch_Score'].max():.1f}")
    print(f"Speed: {df['Speed_Score'].min():.1f} - {df['Speed_Score'].max():.1f}")
    print(f"Form: {df['Form_Score'].min():.1f} - {df['Form_Score'].max():.1f}")
    print(f"Consistency: {df['Consistency_Score'].min():.1f} - {df['Consistency_Score'].max():.1f}")
    print(f"Overall: {df['Overall_Score'].min():.1f} - {df['Overall_Score'].max():.1f}")
    if 'Team_Score' in df.columns:
        print(f"Team Score: {df['Team_Score'].min():.1f} - {df['Team_Score'].max():.1f}")

def main():
    parser = argparse.ArgumentParser(description="Fetch ONLY the 6 key factors for ALL TEAMS for the 2024 season")
    parser.add_argument("--out-dir", type=str, default=RESULT_DIR, help="Output directory for files")
    args = parser.parse_args()
    
    result_dir = args.out_dir
    
    print(f"=== MLB SIX KEY FACTORS FETCHER - 2024 SEASON ===")
    print(f"Output Directory: {result_dir}")
    print("=" * 50)
    
    # Fetch only the 6 key factors for 2024 season
    all_players_six_factors, projections = fetch_six_factors_for_2024_season()
    
    if not all_players_six_factors:
        print(f"No players found for 2024 season")
        return
    
    # Create output directory
    os.makedirs(result_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Add team scores to player data
    all_players_with_team_scores = add_team_scores_to_players(all_players_six_factors)
    
    # Save player data to file (excluding the detailed "_Key" columns)
    output_file = os.path.join(result_dir, "mlb_2024_players_score.csv")
    df = pd.DataFrame(all_players_with_team_scores)
    
    # Remove the detailed "_Key" columns for cleaner CSV output
    key_columns = ['Hitting_Key', 'Pitching_Key', 'Clutch_Key', 'Speed_Key', 'Form_Key', 'Consistency_Key']
    df_clean = df.drop(columns=[col for col in key_columns if col in df.columns])
    
    df_clean = df_clean.sort_values(['Team', 'PlayerType', 'Overall_Score'], ascending=[True, True, False])
    df_clean.to_csv(output_file, index=False)
    
    # Save team scores to separate file
    team_scores = calculate_team_scores(all_players_six_factors)
    team_scores_file = os.path.join(result_dir, "mlb_2024_teams_score.csv")
    team_scores.to_csv(team_scores_file, index=False)
    
    print(f"\nSaved PLAYER SCORES: {output_file}")
    print(f"Total player records: {len(df_clean)}")
    print(f"Columns: {len(df_clean.columns)} (clean version without detailed breakdowns)")
    
    print(f"\nSaved TEAM SCORES: {team_scores_file}")
    print(f"Total teams: {len(team_scores)}")
    print(f"Team score range: {team_scores['Team_Score'].min():.1f} - {team_scores['Team_Score'].max():.1f}")
    
    # Display summary
    display_six_factors_summary(all_players_with_team_scores, "2024")
    
    print(f"\n=== FETCH COMPLETE ===")
    print(f"Only the 6 key factors have been extracted and saved for the 2024 season!")
    print(f"Files created:")
    print(f"  - {os.path.basename(output_file)} (Player data with team scores)")
    print(f"  - {os.path.basename(team_scores_file)} (Team rankings)")

if __name__ == "__main__":
    main() 