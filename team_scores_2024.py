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

def extract_seven_factors_from_player(player):
    """Extract the 7 key factors from player season projection data"""
    
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
    
    # 6. UMPIRE IMPACT (replacing consistency)
    umpire_impact_score = 0
    umpire_impact_factors = {}
    
    # Strike zone discipline (walks vs strikeouts ratio)
    if pd.notna(player.get('Walks')) and pd.notna(player.get('Strikeouts')):
        walks = player['Walks']
        strikeouts = player['Strikeouts']
        if strikeouts > 0:
            bb_k_ratio = walks / strikeouts
            umpire_impact_factors['BB/K Ratio'] = f"{bb_k_ratio:.2f}"
            umpire_impact_score += bb_k_ratio * 8  # New factor
    
    # For pitchers: Control (walks per inning)
    if is_pitcher and pd.notna(player.get('Walks')) and pd.notna(player.get('InningsPitched')):
        walks = player['Walks']
        innings = player['InningsPitched']
        if innings > 0:
            bb_per_ip = walks / innings
            umpire_impact_factors['BB/IP'] = f"{bb_per_ip:.2f}"
            # Lower BB/IP is better, so we invert the score
            umpire_impact_score += max(0, (2.0 - bb_per_ip) * 6)
    
    # HBP (hit by pitch) - can indicate umpire favoritism
    if pd.notna(player.get('HitByPitch')):
        hbp = player['HitByPitch']
        umpire_impact_factors['HBP'] = int(hbp)
        umpire_impact_score += hbp * 0.8  # New factor
    
    # For pitchers: Wild pitches
    if is_pitcher and pd.notna(player.get('WildPitches')):
        wp = player['WildPitches']
        umpire_impact_factors['Wild Pitches'] = int(wp)
        # Penalty for wild pitches
        umpire_impact_score -= wp * 0.6
    
    # 7. BULLPEN FATIGUE
    bullpen_fatigue_score = 0
    bullpen_fatigue_factors = {}
    
    # For pitchers: Innings pitched workload
    if is_pitcher and pd.notna(player.get('InningsPitched')):
        innings = player['InningsPitched']
        bullpen_fatigue_factors['Innings'] = f"{innings:.1f}"
        # Higher innings = more fatigue risk
        if innings > 200:
            bullpen_fatigue_score -= 3  # Heavy workload penalty
        elif innings > 150:
            bullpen_fatigue_score -= 1  # Moderate workload penalty
        elif innings > 100:
            bullpen_fatigue_score += 1  # Good workload balance
        else:
            bullpen_fatigue_score += 2  # Fresh arm bonus
    
    # For pitchers: Appearances (games played)
    if is_pitcher and pd.notna(player.get('Games')):
        games = player['Games']
        bullpen_fatigue_factors['Games'] = int(games)
        # More appearances = more fatigue
        if games > 70:
            bullpen_fatigue_score -= 2  # High appearance penalty
        elif games > 50:
            bullpen_fatigue_score -= 1  # Moderate appearance penalty
        elif games > 30:
            bullpen_fatigue_score += 1  # Good appearance balance
    
    # For pitchers: Saves (closer workload)
    if is_pitcher and pd.notna(player.get('Saves')):
        saves = player['Saves']
        if saves > 0:
            bullpen_fatigue_factors['Saves'] = int(saves)
            # High save count = more pressure situations
            if saves > 40:
                bullpen_fatigue_score -= 2  # High pressure penalty
            elif saves > 25:
                bullpen_fatigue_score -= 1  # Moderate pressure penalty
    
    # For batters: Games played (position player fatigue)
    if not is_pitcher and pd.notna(player.get('Games')):
        games = player['Games']
        bullpen_fatigue_factors['Games'] = int(games)
        # More games = more fatigue
        if games > 150:
            bullpen_fatigue_score -= 1  # High game count penalty
        elif games > 120:
            bullpen_fatigue_score += 0  # Neutral
        else:
            bullpen_fatigue_score += 1  # Fresh player bonus
    
    # Calculate overall ability score with updated weights for 7 factors
    overall_score = (
        hitting_score * 0.30 +
        pitching_score * 0.30 +
        clutch_score * 0.15 +
        speed_score * 0.08 +
        form_score * 0.04 +
        umpire_impact_score * 0.08 +
        bullpen_fatigue_score * 0.05
    )
    
    return {
        'Team': team,
        'Name': player.get('Name'),
        'Position': position,
        'PlayerType': 'Pitcher' if is_pitcher else 'Batter',
        
        # The 7 Key Factors
        'Hitting_Score': round(hitting_score, 1),
        'Pitching_Score': round(pitching_score, 1),
        'Clutch_Score': round(clutch_score, 1),
        'Speed_Score': round(speed_score, 1),
        'Form_Score': round(form_score, 1),
        'Umpire_Impact_Score': round(umpire_impact_score, 1),
        'Bullpen_Fatigue_Score': round(bullpen_fatigue_score, 1),
        'Overall_Score': round(overall_score, 1),
        
        # Key factor details (simplified)
        'Hitting_Key': ' | '.join([f"{k}: {v}" for k, v in hitting_factors.items()]) if hitting_factors else '',
        'Pitching_Key': ' | '.join([f"{k}: {v}" for k, v in pitching_factors.items()]) if pitching_factors else '',
        'Clutch_Key': ' | '.join([f"{k}: {v}" for k, v in clutch_factors.items()]) if clutch_factors else '',
        'Speed_Key': ' | '.join([f"{k}: {v}" for k, v in speed_factors.items()]) if speed_factors else '',
        'Form_Key': ' | '.join([f"{k}: {v}" for k, v in form_factors.items()]) if form_factors else '',
        'Umpire_Impact_Key': ' | '.join([f"{k}: {v}" for k, v in umpire_impact_factors.items()]) if umpire_impact_factors else '',
        'Bullpen_Fatigue_Key': ' | '.join([f"{k}: {v}" for k, v in bullpen_fatigue_factors.items()]) if bullpen_fatigue_factors else ''
    }

def fetch_seven_factors_for_2024_season():
    """Fetch the 7 key factors for all players for the 2024 season"""
    print(f"Fetching SEVEN KEY FACTORS for ALL TEAMS for 2024 SEASON...")
    
    # Fetch season projections
    projections = fetch_player_season_projections()
    
    if not projections:
        print(f"No player projections found for 2024 season")
        return [], projections
    
    all_players_seven_factors = []
    
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
        
        player_seven_factors = extract_seven_factors_from_player(player)
        if player_seven_factors is not None:  # Only add players with valid team names
            all_players_seven_factors.append(player_seven_factors)
    
    print(f"Filtered out {filtered_count} players with null/empty team names")
    print(f"Remaining players: {len(all_players_seven_factors)}")
    
    return all_players_seven_factors, projections

def prepare_players_data(players_data):
    """Prepare player data for output"""
    df = pd.DataFrame(players_data)
    
    # Convert back to list of dictionaries
    return df.to_dict('records')

def display_seven_factors_summary(players_data, season="2024"):
    """Display a summary of the 7 key factors"""
    
    if not players_data:
        print("No player data to display")
        return
    
    df = pd.DataFrame(players_data)
    
    print(f"\n" + "="*80)
    print(f"SEVEN KEY FACTORS SUMMARY - {season} SEASON")
    print("="*80)
    
    # Sort by overall score
    df_sorted = df.sort_values('Overall_Score', ascending=False)
    
    print(f"\nTOP 20 PLAYERS BY OVERALL ABILITY:")
    print("-" * 80)
    
    for i, (_, player) in enumerate(df_sorted.head(20).iterrows()):
        print(f"\n{i+1:2d}. {player['Name']:<20} ({player['Team']:<3}) - {player['Position']:<2}")
        print(f"     Overall Score: {player['Overall_Score']:>6.1f} | Type: {player['PlayerType']}")
        
        # Show only the 7 key factors
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
        
        if player['Umpire_Impact_Score'] > 0:
            print(f"     ⚙️  Umpire Impact: {player['Umpire_Impact_Score']:>6.1f} - {player['Umpire_Impact_Key']}")
        
        if player['Bullpen_Fatigue_Score'] != 0:
            print(f"     🥱 Bullpen Fatigue: {player['Bullpen_Fatigue_Score']:>6.1f} - {player['Bullpen_Fatigue_Key']}")
    
    # Summary statistics
    print(f"\n" + "="*80)
    print("SUMMARY OF SEVEN KEY FACTORS:")
    print("="*80)
    
    print(f"Total Players Analyzed: {len(df)}")
    print(f"Pitchers: {len(df[df['PlayerType'] == 'Pitcher'])}")
    print(f"Batters: {len(df[df['PlayerType'] == 'Batter'])}")
    
    print(f"\nScore Ranges:")
    print(f"Hitting: {df['Hitting_Score'].min():.1f} - {df['Hitting_Score'].max():.1f}")
    print(f"Pitching: {df['Pitching_Score'].min():.1f} - {df['Pitching_Score'].max():.1f}")
    print(f"Clutch: {df['Clutch_Score'].min():.1f} - {df['Clutch_Score'].max():.1f}")
    print(f"Speed: {df['Speed_Score'].min():.1f} - {df['Speed_Score'].max():.1f}")
    print(f"Form: {df['Form_Score'].min():.1f} - {df['Form_Score'].max():.1f}")
    print(f"Umpire Impact: {df['Umpire_Impact_Score'].min():.1f} - {df['Umpire_Impact_Score'].max():.1f}")
    print(f"Bullpen Fatigue: {df['Bullpen_Fatigue_Score'].min():.1f} - {df['Bullpen_Fatigue_Score'].max():.1f}")
    print(f"Overall: {df['Overall_Score'].min():.1f} - {df['Overall_Score'].max():.1f}")

def main():
    parser = argparse.ArgumentParser(description="Fetch the 7 key factors for ALL TEAMS for the 2024 season")
    parser.add_argument("--out-dir", type=str, default=RESULT_DIR, help="Output directory for files")
    args = parser.parse_args()
    
    result_dir = args.out_dir
    
    print(f"=== MLB SEVEN KEY FACTORS FETCHER - 2024 SEASON ===")
    print(f"Output Directory: {result_dir}")
    print("=" * 50)
    
    # Fetch the 7 key factors for 2024 season
    all_players_seven_factors, projections = fetch_seven_factors_for_2024_season()
    
    if not all_players_seven_factors:
        print(f"No players found for 2024 season")
        return
    
    # Create output directory
    os.makedirs(result_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Prepare player data for output
    all_players_data = prepare_players_data(all_players_seven_factors)
    
    # Save player data to file (excluding the detailed "_Key" columns)
    output_file = os.path.join(result_dir, "mlb_2024_players_score.csv")
    df = pd.DataFrame(all_players_data)
    
    # Remove the detailed "_Key" columns for cleaner CSV output
    key_columns = ['Hitting_Key', 'Pitching_Key', 'Clutch_Key', 'Speed_Key', 'Form_Key', 'Umpire_Impact_Key', 'Bullpen_Fatigue_Key']
    df_clean = df.drop(columns=[col for col in key_columns if col in df.columns])
    
    df_clean = df_clean.sort_values(['Team', 'PlayerType', 'Overall_Score'], ascending=[True, True, False])
    df_clean.to_csv(output_file, index=False)
    
    print(f"\nSaved PLAYER SCORES: {output_file}")
    print(f"Total player records: {len(df_clean)}")
    print(f"Columns: {len(df_clean.columns)} (clean version without detailed breakdowns)")
    
    # Display summary
    display_seven_factors_summary(all_players_data, "2024")
    
    print(f"\n=== FETCH COMPLETE ===")
    print(f"The 7 key factors have been extracted and saved for the 2024 season!")
    print(f"Files created:")
    print(f"  - {os.path.basename(output_file)} (Player data with 7 key factors)")

if __name__ == "__main__":
    main() 