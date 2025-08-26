# MLB Odds Data Fetcher

This script fetches MLB game data from the sportsdata.io API and saves it as a CSV file in the exact format shown in your reference image.

## Features

- Fetches MLB game data for a specific date
- Extracts only the essential fields:
  - GameID: Unique identifier for each game
  - DateTime: Game start time
  - AwayTeam: Away team abbreviation
  - HomeTeam: Home team abbreviation
- Saves data to CSV format in a `results` folder
- Formats output to match the reference image structure exactly
- Handles API errors gracefully

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **API Configuration:**
   The script uses the API credentials stored in `config.py`:
   - API Key: b4541c2cd3124b35bdd2f5267773044e
   - Base URL: https://api.sportsdata.io/api/mlb/odds/json

## Usage

Run the script:
```bash
python mlb_odds_fetcher.py
```

The script will:
1. Attempt to fetch game data for yesterday's games
2. If no data is available for yesterday, try today's games
3. Parse the response and extract the required fields
4. Create a `results` folder if it doesn't exist
5. Save the data to a CSV file named `mlb_odds_YYYY-MM-DD.csv` in the results folder

## Output Format

The CSV file will be saved in the `results` folder and will have the exact structure shown in your reference image:

- **Header**: GameID, DateTime, Away/Home Team
- **Data Structure**: Each game takes two rows:
  - Row 1: GameID, DateTime, AwayTeam
  - Row 2: (empty), (empty), HomeTeam

Example:
```
GameID,DateTime,Away/Home Team
76221,2025-08-21T13:10:00,ATH
,,MIN
76222,2025-08-21T14:10:00,TEX
,,KC
```

## API Endpoint

The script uses the `GamesByDate` endpoint:
```
GET https://api.sportsdata.io/api/mlb/odds/json/GamesByDate/{date}
```

## Notes

- The script automatically creates a `results` folder
- Output format exactly matches your reference image
- Only essential game information is included
- Error handling is implemented for network issues and API errors 