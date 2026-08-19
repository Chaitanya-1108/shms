from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


# Initialize database object
db = SQLAlchemy()


class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    # Set password (hashed)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Check password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Helmet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    helmet_id = db.Column(db.String(100), unique=True, nullable=False)

    gas_level = db.Column(db.Float, default=0.0)
    temperature = db.Column(db.Float, default=0.0)

    latitude = db.Column(db.Float, default=0.0)
    longitude = db.Column(db.Float, default=0.0)

    battery_level = db.Column(db.Float, default=100.0)

    status = db.Column(db.String(50), default="SAFE")

    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
def ist_now():
    return datetime.now(ZoneInfo("Asia/Kolkata"))

class SensorReading(db.Model):
    """Time-series telemetry for helmets."""
    id = db.Column(db.Integer, primary_key=True)
    helmet_id = db.Column(db.Integer, db.ForeignKey('helmet.id', ondelete='CASCADE'), nullable=False)
    gas_level = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    battery_level = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=ist_now, index=True)

    helmet = db.relationship('Helmet', backref=db.backref('readings', lazy='dynamic', cascade='all, delete-orphan'))


