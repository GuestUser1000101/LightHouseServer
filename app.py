import json
import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

raw_url = os.environ.get("DATABASE_URL")
import logging

logging.info(raw_url)
if raw_url:
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
else:
    raw_url = "postgresql://postgres:password@localhost:5432/scouting_db"

app.config["SQLALCHEMY_DATABASE_URI"] = raw_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class ScoutingData(db.Model):
    __tablename__ = "scouting_records"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    unique_id = db.Column(db.String(100), index=True)
    content = db.Column(db.Text, nullable=False)


time.sleep(5)
with app.app_context():
    db.create_all()


@app.route("/api/<category>", methods=["POST", "GET"])
def handle_data(category):
    if category not in ["atlas", "pit"]:
        return "Not Found", 404

    if request.method == "POST":
        try:
            raw_data = request.get_data(as_text=True)
            if not raw_data:
                return "Empty", 400

            data_dict = json.loads(raw_data)

            if category == "atlas":
                identifier = f"{data_dict.get('matchType', 'unknown')}-{data_dict.get('matchNumber', '0')}"
            else:
                identifier = str(data_dict.get("teamNumber", "0"))

            existing = ScoutingData.query.filter_by(
                category=category, unique_id=identifier
            ).first()

            if existing:
                existing.content = raw_data
            else:
                new_record = ScoutingData(
                    category=category, unique_id=identifier, content=raw_data
                )
                db.session.add(new_record)

            db.session.commit()
            return "OK", 200

        except Exception:
            return "ERROR", 500

    if request.method == "GET":
        records = ScoutingData.query.filter_by(category=category).all()
        combined_json = ",".join([r.content for r in records])
        return f"[{combined_json}]", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
