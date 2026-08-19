from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, Admin, Helmet, SensorReading
import random
from datetime import datetime
from zoneinfo import ZoneInfo

# -----------------------------
# Flask App Configuration
# -----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Register app with SQLAlchemy
db.init_app(app)

# -----------------------------
# Flask-Login Setup
# -----------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ------------------------------
# Database insert test
# ------------------------------
@app.route("/test")
def test():
    new_data = Helmet(gas=20, temperature=30, battery=75)
    db.session.add(new_data)
    db.session.commit()
    return "Data inserted!"
def ist_now():
    return datetime.now(ZoneInfo("Asia/Kolkata"))
# -----------------------------
# Check Database Data
# -----------------------------
@app.route("/check")
def check():
    data = Helmet.query.all()

    result = ""
    for item in data:
        result += f"Gas: {item.gas}, Temp: {item.temperature}, Battery: {item.battery} <br>"

    return result

# -----------------------------
# Simulate Data
# -----------------------------
@app.route('/simulate')
@login_required
def simulate():
    helmets = Helmet.query.all()

    for helmet in helmets:
        # generate simulated sensor values
        g = random.randint(100, 500)
        t = random.randint(20, 70)
        b = random.randint(10, 100)

        helmet.gas_level = g
        helmet.temperature = t
        helmet.battery_level = b
        helmet.last_updated = ist_now()

        # save a time-series reading
        from models import SensorReading
        sr = SensorReading(helmet_id=helmet.id, gas_level=g, temperature=t, battery_level=b)
        db.session.add(sr)

    db.session.commit()

    return redirect(url_for('dashboard'))


# -----------------------------
# Load User for Flask-Login
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))

# -----------------------------
# Home Route (ONLY ONE NOW ✅)
# -----------------------------
@app.route("/")
def home():
    return redirect(url_for("login"))

# -----------------------------
# Login Route
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")

# -----------------------------
# Dashboard
# -----------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    helmets = Helmet.query.all()

    for helmet in helmets:
        if helmet.gas_level > 300 or helmet.temperature > 50:
            helmet.status = "DANGER"
        elif helmet.battery_level < 20:
            helmet.status = "WARNING"
        else:
            helmet.status = "SAFE"

    db.session.commit()

    total = len(helmets)
    safe = len([h for h in helmets if h.status == "SAFE"])
    danger = len([h for h in helmets if h.status == "DANGER"])
    warning = len([h for h in helmets if h.status == "WARNING"])

    helmet_data = []
    for h in helmets:
        helmet_data.append({
            "helmet_id": h.helmet_id,
            "gas_level": h.gas_level,
            "temperature": h.temperature,
            "battery_level": h.battery_level
        })

    return render_template(
        "dashboard.html",
        helmets=helmets,
        helmet_data=helmet_data,
        total=total,
        safe=safe,
        danger=danger,
        warning=warning,
        username=current_user.username,
        server_gmt=ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
    )

# -----------------------------
# API - real time data for frontend
# -----------------------------
@app.route('/api/helmets')
@login_required
def api_helmets():
    helmets = Helmet.query.all()

    # update statuses (same logic as dashboard)
    for helmet in helmets:
        if helmet.gas_level > 300 or helmet.temperature > 50:
            helmet.status = "DANGER"
        elif helmet.battery_level < 20:
            helmet.status = "WARNING"
        else:
            helmet.status = "SAFE"

    db.session.commit()

    helmet_list = []
    for h in helmets:
        helmet_list.append({
            "id": h.id,
            "helmet_id": h.helmet_id,
            "gas_level": h.gas_level,
            "temperature": h.temperature,
            "battery_level": h.battery_level,
            "status": h.status,
            "last_updated": h.last_updated.isoformat() if h.last_updated else datetime.utcnow().isoformat()
        })

    return {"helmets": helmet_list, "server_time": ist_now().isoformat()}


# -----------------------------
# API - helmet readings / history
# -----------------------------
@app.route('/api/helmet/<int:hid>/readings')
@login_required
def api_helmet_readings(hid):
    # optional ?limit= parameter
    limit = request.args.get('limit', type=int)
    q = SensorReading.query.filter_by(helmet_id=hid).order_by(SensorReading.timestamp.desc())
    if limit:
        q = q.limit(limit)
    readings = q.all()

    data = [
        {
            'timestamp': r.timestamp.isoformat(),
            'gas_level': r.gas_level,
            'temperature': r.temperature,
            'battery_level': r.battery_level
        }
        for r in reversed(readings)  # return oldest → newest
    ]

    return {'helmet_id': hid, 'readings': data}


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# -----------------------------
# Add & Remove Helmet
# -----------------------------
@app.route('/add_helmet', methods=['GET', 'POST'])
@login_required
def add_helmet():
    if request.method == 'POST':
        if 'helmet_id' in request.form:
            helmet_id = request.form.get('helmet_id')

            if Helmet.query.filter_by(helmet_id=helmet_id).first():
                flash("Helmet ID already exists!", "danger")
            else:
                new_helmet = Helmet(helmet_id=helmet_id)
                db.session.add(new_helmet)
                db.session.commit()
                flash("Helmet Added Successfully!", "success")

        elif 'delete_id' in request.form:
            helmet_to_delete = Helmet.query.get(int(request.form.get('delete_id')))
            if helmet_to_delete:
                db.session.delete(helmet_to_delete)
                db.session.commit()
                flash(f"Helmet {helmet_to_delete.helmet_id} removed successfully!", "success")
            else:
                flash("Helmet not found!", "danger")

        return redirect(url_for('add_helmet'))

    helmets = Helmet.query.all()
    return render_template('add_helmet.html', helmets=helmets)

# -----------------------------
# Delete Helmet Route
# -----------------------------
@app.route('/delete_helmet/<int:helmet_id>', methods=['POST'])
@login_required
def delete_helmet(helmet_id):
    helmet = Helmet.query.get_or_404(helmet_id)
    db.session.delete(helmet)
    db.session.commit()
    flash(f"Helmet {helmet.helmet_id} removed successfully!", "success")
    return redirect(url_for('dashboard'))


# -----------------------------
# History page (recent readings)
# -----------------------------
@app.route('/history')
@login_required
def history():
    # show recent readings (newest first)
    limit = 500
    readings = SensorReading.query.order_by(SensorReading.timestamp.desc()).limit(limit).all()

    # prepare compact records for template (oldest->newest)
    out = []
    for r in reversed(readings):
        out.append({
            'helmet_id': r.helmet.helmet_id if r.helmet else f'id:{r.helmet_id}',
            'gas_level': r.gas_level,
            'temperature': r.temperature,
            'battery_level': r.battery_level,
            'timestamp': r.timestamp
        })

    return render_template('history.html', readings=out, server_gmt=ist_now().strftime('%Y-%m-%d %H:%M:%S IST'))

# -----------------------------
# Create Database & Default Admin
# -----------------------------
def create_tables():
    with app.app_context():
        db.create_all()

        if not Admin.query.filter_by(username="admin").first():
            admin = Admin(username="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Default admin created: username=admin password=admin123")

# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
