import os
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Configuration ---
raw_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/scouting_db')
if raw_url and raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = raw_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class ScoutingData(db.Model):
    __tablename__ = 'scouting_records'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    # Store unique identifiers as strings to make searching easier
    unique_id = db.Column(db.String(100), index=True) 
    content = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/api/<category>', methods=['POST', 'GET'])
def handle_data(category):
    if category not in ['atlas', 'pit']:
        return "Not Found", 404

    if request.method == 'POST':
        try:
            raw_data = request.get_data(as_text=True)
            if not raw_data:
                return "Empty", 400
            
            # Parse the string to find the unique keys
            data_dict = json.loads(raw_data)
            identifier = ""

            if category == 'atlas':
                # Create a composite key: e.g., "Quals-42"
                m_type = data_dict.get("matchType", "unknown")
                m_num = data_dict.get("matchNumber", "0")
                identifier = f"{m_type}-{m_num}"
            
            elif category == 'pit':
                # Key is just the team number: e.g., "254"
                identifier = str(data_dict.get("teamNumber", "0"))

            # Check if this record already exists
            existing_record = ScoutingData.query.filter_by(
                category=category, 
                unique_id=identifier
            ).first()

            if existing_record:
                # Update existing data with the new upload
                existing_record.content = raw_data
            else:
                # Create new record
                new_record = ScoutingData(
                    category=category, 
                    unique_id=identifier, 
                    content=raw_data
                )
                db.session.add(new_record)
            
            db.session.commit()
            return "OK", 200 
            
        except Exception as e:
            print(f"Error: {e}")
            return "ERROR", 500

    if request.method == 'GET':
        records = ScoutingData.query.filter_by(category=category).all()
        combined_json_string = ",".join([r.content for r in records])
        return f"[{combined_json_string}]", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)