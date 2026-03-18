import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Configuration ---
# Fix for Render's 'postgres://' vs SQLAlchemy's 'postgresql://'
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
    category = db.Column(db.String(20), nullable=False) # atlas or pit
    content = db.Column(db.Text, nullable=False)        # Stores raw JSON string

with app.app_context():
    db.create_all()

# --- Routes ---

@app.route('/api/<category>', methods=['POST', 'GET'])
def handle_data(category):
    if category not in ['atlas', 'pit']:
        return "Not Found", 404

    if request.method == 'POST':
        try:
            # Get the exact string your Flutter app sends in 'body: fileContent'
            raw_data = request.get_data(as_text=True)
            
            if not raw_data:
                return "Empty", 400

            new_record = ScoutingData(category=category, content=raw_data)
            db.session.add(new_record)
            db.session.commit()
            
            # Per your request: Returns "OK" so your Flutter responseCodes map is happy
            return "OK", 200 
            
        except Exception:
            return "ERROR", 500

    if request.method == 'GET':
        # 1. Fetch all records for the category
        records = ScoutingData.query.filter_by(category=category).all()
        
        # 2. Manually build a JSON array string: [obj1,obj2,obj3]
        # Since each record.content is already a string like '{"team":1}',
        # we join them with commas and wrap them in square brackets.
        combined_json_string = ",".join([r.content for r in records])
        final_output = f"[{combined_json_string}]"
        
        # 3. Return as plain text so response.body is exactly what your 
        # saveDatabaseFile expects to write to the .json file.
        return final_output, 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)