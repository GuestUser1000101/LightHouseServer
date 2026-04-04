import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class TBAClient:
    def __init__(self):
        self.auth_key = os.environ.get("TBA_AUTH_KEY")
        self.base_url = "https://www.thebluealliance.com/api/v3"
        
        if not self.auth_key:
            print("CRITICAL: TBA_AUTH_KEY not found in environment.")

    def get_headers(self):
        return {
            "X-TBA-Auth-Key": self.auth_key,
            "accept": "application/json"
        }

    def get_event_matches(self, event_key):
        """Fetches all matches for a specific event."""
        endpoint = f"/event/{event_key}/matches"
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status() 
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching matches: {e}")
            return None

    def print_pretty_json(self, data):
        """Prints any dictionary/list as a formatted JSON string."""
        if data:
            print(json.dumps(data, indent=4, sort_keys=True))
        else:
            print("No data to print.")
    
    def get_tba_match_key(event_key, match_type, match_number):
        if match_type == "Qualifications":
            return f"{event_key}_qm{match_number}"
        elif match_type == "Playoffs":
            return f"{event_key}_sf{match_number}m1"
        elif match_type == "Finals":
            return f"{event_key}_f1m{match_number}"
        return None

if __name__ == "__main__":
    client = TBAClient()
    
    target_event = "2025cmptx"
    
    match_data = client.get_event_matches(target_event)
    client.print_pretty_json([m for m in match_data[:1]])