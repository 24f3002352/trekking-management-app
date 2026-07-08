from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=True)
    # Roles allowed
    role = db.Column(db.String(20), nullable=False, default='user')
    # Status allowed
    status = db.Column(db.String(20), nullable=False, default='approved')

    
    bookings = db.relationship('Booking', backref='trekker', lazy=True)
    assigned_treks = db.relationship('Trek', backref='guide', lazy=True)

class Trek(db.Model):
    __tablename__ = 'treks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False) # Easy, Moderate, Hard
    duration = db.Column(db.Integer, nullable=False) # Days
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.String(50), nullable=False)
    end_date = db.Column(db.String(50), nullable=False)
    
    status = db.Column(db.String(20), nullable=False, default='Open')
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    bookings = db.relationship('Booking', backref='trek_event', lazy=True)

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey('treks.id'), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Booked') # Booked, Cancelled, Completed

def init_db(app):
    """Programmatic schema initialization to avoid manual DB browser dependencies."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        # Seed default pre-existing master superuser safely if not found
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            hashed_pw = generate_password_hash("admin123", method='scrypt')
            default_admin = User(
                username="admin",
                password=hashed_pw,
                name="System Administrator",
                contact="0000000000",
                role="admin",
                status="approved"
            )
            db.session.add(default_admin)
            db.session.commit()
            print("[INFO] Database successfully established and initial administrator 'admin' initialized.")
