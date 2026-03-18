import os
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
    # Using db.JSON allows PostgreSQL to store and return actual objects
    content = db.Column(db.JSON, nullable=False)        

with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/api/<category>', methods=['POST', 'GET'])
def handle_data(category):
    if category not in ['atlas', 'pit']:
        return "Not Found", 404

    if request.method == 'POST':
        try:
            # force=True ensures it parses the body as JSON 
            # even if the Flutter header isn't perfect.
            json_data = request.get_json(force=True)
            
            if not json_data:
                return "Empty File", 400

            new_record = ScoutingData(category=category, content=json_data)
            db.session.add(new_record)
            db.session.commit()
            
            # Per your request: Returns "OK"
            return "OK", 200 
            
        except Exception:
            return "ERROR", 500

    if request.method == 'GET':
        # Fetch all records
        records = ScoutingData.query.filter_by(category=category).all()
        
        # Extract the 'content' (which are now Python dicts, not strings)
        # This creates: [{"team": 1}, {"team": 2}]
        data_list = [record.content for record in records]
        
        # Returns a true JSON array
        return jsonify(data_list), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)