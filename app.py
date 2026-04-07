import json
import os
import time
import logging
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from security import generate_random_key, get_as_hashed
from tba_client import TBAClient


load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

raw_url = os.environ.get("DATABASE_URL")
encoded_pass = os.environ.get("DB_PASS_ENCODED")
user = os.environ.get("DB_USER")
name = os.environ.get("DB_NAME")
admin_pass = os.environ.get("ADMIN_PASS")

if raw_url:
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
elif encoded_pass and user and name:
    raw_url = f"postgresql://{user}:{encoded_pass}@localhost:5432/{name}"
else:
    raw_url = "postgresql://postgres:password@localhost:5432/scouting_db"

logging.info(f"Connecting to: {raw_url}")

app.config["SQLALCHEMY_DATABASE_URI"] = raw_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class ConfigData(db.Model):
    __tablename__ = "config"
    id = db.Column(db.Integer, primary_key=True)
    event_key = db.Column(db.Text, nullable=False)


class ScoutingData(db.Model):
    __tablename__ = "scouting_records"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)
    unique_id = db.Column(db.String(100), index=True)
    content = db.Column(db.Text, nullable=False)


class SecurityData(db.Model):
    __tablename__ = "uuids"
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.Text, nullable=False)


class TemporaryKeyData(db.Model):
    __tablename__ = "temp_keys"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text, nullable=False)


time.sleep(5)
with app.app_context():
    db.create_all()
    if not ConfigData.query.first():
        db.session.add(ConfigData(event_key="2026nrg"))
        db.session.commit()


@app.route("/config", methods=["GET", "POST"])
def handle_config():
    if request.method == "POST":
        if request.headers.get("password") != admin_pass:
            return "Unauthorized", 401

        raw_data = request.get_data(as_text=True)
        if not raw_data:
            return "Empty", 400

        event_key = json.loads(raw_data).get("event_key")
        if event_key:
            ConfigData.query.first().event_key = event_key

        db.session.commit()
        return "Config successfully changed.", 200

    if request.method == "GET":
        return f"{ConfigData.query.first().event_key}", 200


@app.route("/secure/nuclear", methods=["DELETE"])
def wipe_security():
    if request.headers.get("password") != admin_pass:
        return "Unauthorized", 401

    TemporaryKeyData.query.delete()
    SecurityData.query.delete()
    db.session.commit()

    return "Security database wiped", 200


@app.route("/secure/key", methods=["GET"])
def see_all_keys():
    if request.headers.get("password") != admin_pass:
        return "Unauthorized", 401

    return ",".join([r.key for r in TemporaryKeyData.query.all()]), 200


@app.route("/secure/key", methods=["POST"])
def get_one_time_key():
    if request.headers.get("password") != admin_pass:
        return "Unauthorized", 401

    raw_key = generate_random_key(12)
    new_record = TemporaryKeyData(key=get_as_hashed(raw_key))
    db.session.add(new_record)
    db.session.commit()
    return raw_key, 200


@app.route("/secure/create", methods=["POST"])
def register_device():
    raw_key = request.headers.get("key")
    uuid = request.headers.get("uuid")

    if not raw_key or not uuid:
        return "Failed to register device. Missing headers.", 400

    existing_temp_key = TemporaryKeyData.query.filter_by(
        key=get_as_hashed(raw_key)
    ).first()
    if existing_temp_key:
        existing_uuid_record = SecurityData.query.filter_by(
            uuid=get_as_hashed(uuid)
        ).first()
        db.session.delete(existing_temp_key)
        if existing_uuid_record:
            db.session.commit()
            return f"Device already registered. UUID: {uuid}", 200
        new_record = SecurityData(uuid=get_as_hashed(uuid))
        db.session.add(new_record)
        db.session.commit()
        return f"Successfully registered device. UUID: {uuid}", 200
    else:
        return f"Failed to register device. Invalid key. UUID: {uuid}", 400


@app.route("/nuclear", methods=["DELETE"])
def wipe_all():
    if request.headers.get("password") != admin_pass:
        return "Unauthorized", 401

    db.drop_all()
    db.create_all()
    if not ConfigData.query.first():
        db.session.add(ConfigData(event_key="2026nrg"))
        db.session.commit()

    return "Database wiped", 200


@app.route("/api/prediction", methods=["GET"])
def get_prediction_leaderboard():
    try:
        client = TBAClient()
        event_key = ConfigData.query.first().event_key
        match_data = client.get_event_matches(event_key)

        records = ScoutingData.query.filter_by(category="atlas").all()
        record_content = [json.loads(r.content) for r in records]

        leaderboard = {}

        for content in record_content:
            if not content.get("matchPrediction"):
                continue
            match_key = TBAClient.get_tba_match_key(
                event_key, content.get("matchType"), content.get("matchNumber")
            )

            winner = None
            resultTime = None
            for match in match_data:
                if match.get("key") and match.get("key") == match_key:
                    winner = match.get("winning_alliance")
                    resultTime = match.get("post_result_time")
                    break

            predicted_winner = content.get("matchPrediction").get("prediction")
            predicted_time = content.get("matchPrediction").get("time")

            if (
                not winner
                or resultTime == None
                or not predicted_winner
                or predicted_time == None
            ):
                continue

            if winner == predicted_winner and predicted_time < resultTime:
                if not leaderboard.get(content.get("scouterName")):
                    leaderboard[content.get("scouterName")] = 0
                leaderboard[content.get("scouterName")] += 1

        return json.dumps(leaderboard), 200
    except Exception as e:
        logging.error(f"GET Error: {e}")
        return "ERROR", 500


@app.route("/api/<category>", methods=["POST", "GET", "DELETE"])
def handle_data(category):
    if category not in ["atlas", "pit"]:
        return "Not Found", 404

    if request.method == "POST":
        try:
            uuid = request.headers.get("X-API-KEY")
            existing = SecurityData.query.filter_by(uuid=get_as_hashed(uuid)).first()
            if not existing:
                return "Unauthorized", 401

            raw_data = request.get_data(as_text=True)
            if not raw_data:
                return "Empty", 400

            data_dict = json.loads(raw_data)

            if category == "atlas":
                m_type = data_dict.get("matchType", "unknown")
                m_num = data_dict.get("matchNumber", "0")
                d_station = data_dict.get("driverStation", "unknown")
                identifier = f"{m_type}-{m_num}-{d_station}"
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

        except Exception as e:
            logging.error(f"POST Error: {e}")
            return "ERROR", 500

    if request.method == "GET":
        try:
            records = ScoutingData.query.filter_by(category=category).all()
            combined_json = ",".join([r.content for r in records])
            return f"[{combined_json}]", 200
        except Exception as e:
            logging.error(f"GET Error: {e}")
            return "ERROR", 500

    if request.method == "DELETE":
        if request.headers.get("password") != admin_pass:
            return "Unauthorized", 401

        try:
            raw_data = request.get_data(as_text=True)
            if not raw_data:
                return "Empty", 400

            data_dict = json.loads(raw_data)

            if category == "atlas":
                m_type = data_dict.get("matchType", "unknown")
                m_num = data_dict.get("matchNumber", "0")
                d_station = data_dict.get("driverStation", "unknown")
                identifier = f"{m_type}-{m_num}-{d_station}"
            else:
                identifier = str(data_dict.get("teamNumber", "0"))

            existing = ScoutingData.query.filter_by(
                category=category, unique_id=identifier
            ).first()

            if existing:
                db.session.delete(existing)
                db.session.commit()
                return "Successfully deleted.", 200
            else:
                return "Failed to delete entry. Entry not found.", 404
        except Exception as e:
            logging.error(f"POST Error: {e}")
            return "ERROR", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
