import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Configuration ---
# If your friend is hosting locally, they replace 'user', 'pass', and 'localhost'
DB_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/scouting_db')
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
class ScoutingData(db.Model):
    __tablename__ = 'scouting_records'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False) # atlas or pit
    content = db.Column(db.Text, nullable=False)        # Storing as Text to match your 'fileContent' string

with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/api/<category>', methods=['POST', 'GET'])
def handle_data(category):
    # Match your Flutter logic: only handle atlas and pit
    # Note: 'hp' and 'chronos' will now return 404 because you asked to ignore them
    if category not in ['atlas', 'pit']:
        return "Not Found", 404

    if request.method == 'POST':
        try:
            # IMPORTANT: Your Flutter app sends 'fileContent' (a String).
            # We use request.get_data(as_text=True) to capture that raw string directly.
            raw_data = request.get_data(as_text=True)
            
            if not raw_data:
                return "Empty File", 400

            new_record = ScoutingData(category=category, content=raw_data)
            db.session.add(new_record)
            db.session.commit()
            
            # This returns 201. Your Flutter 'responseCodes' map should 
            # ideally have 201 set to "Success" or "Uploaded".
            return "Created", 201 
            
        except Exception:
            return "ERROR", 500

    if request.method == 'GET':
        # Your Flutter 'downloadDatabase' expects 'response.body' to be the database content.
        # We join all records with a newline or return them as a giant JSON string.
        records = ScoutingData.query.filter_by(category=category).all()
        
        # We return the contents joined by newlines so saveDatabaseFile receives one big string
        combined_data = "\n".join([r.content for r in records])
        return combined_data, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)