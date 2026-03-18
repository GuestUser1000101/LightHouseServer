import os
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Configuration ---
# Render Fix: SQLAlchemy requires 'postgresql://' but Render provides 'postgres://'
raw_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/scouting_db')
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = raw_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class ScoutingData(db.Model):
    __tablename__ = 'scouting_records'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False) 
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
                return "Empty File", 400

            new_record = ScoutingData(category=category, content=raw_data)
            db.session.add(new_record)
            db.session.commit()
            
            return "Created", 201 
            
        except Exception:
            return "ERROR", 500

    if request.method == 'GET':
        # 1. Fetch all records for the category
        records = ScoutingData.query.filter_by(category=category).all()
        
        # 2. Extract the strings into a list
        # This creates: ["{json1}", "{json2}", "{json3}"]
        data_list = [record.content for record in records]
        
        # 3. Return as a JSON array
        return jsonify(data_list), 200

if __name__ == '__main__':
    # Use environment port for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)