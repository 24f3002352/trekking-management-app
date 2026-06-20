import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from models import db, User, Trek, Booking, init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'SuperSecretTrekKey2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trekking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database system state configurations cleanly
init_db(app)

# Session Authentication Gateway Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_gate'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# 1. CORE AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def index_redirect():
    return redirect(url_for('login_gate'))

@app.route('/login', methods=['GET', 'POST'])
def login_gate():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Invalid combination of username or secret password.', 'danger')
            return redirect(url_for('login_gate'))
            
        if user.status == 'blacklisted':
            flash('Your access has been terminated by administration management.', 'danger')
            return redirect(url_for('login_gate'))
            
        if user.role == 'staff' and user.status == 'pending':
            flash('Your account application is still awaiting Admin verification review.', 'warning')
            return redirect(url_for('login_gate'))
            
        login_user(user)
        if user.role == 'admin': return redirect(url_for('admin_dashboard'))
        elif user.role == 'staff': return redirect(url_for('staff_dashboard'))
        else: return redirect(url_for('user_dashboard'))
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_gate():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        name = request.form.get('name').strip()
        contact = request.form.get('contact').strip()
        role = request.form.get('role') # 'user' or 'staff'
        
        if User.query.filter_by(username=username).first():
            flash('Username is currently taken by another account registration.', 'danger')
            return redirect(url_for('register_gate'))
            
        # Admin accounts are explicitly banned from self-register templates
        if role not in ['user', 'staff']:
            role = 'user'
            
        # Staff accounts are initialized with a 'pending' state until verified by an Admin
        initial_status = 'pending' if role == 'staff' else 'approved'
        hashed_pw = generate_password_hash(password, method='scrypt')
        
        new_account = User(
            username=username, password=hashed_pw, name=name, 
            contact=contact, role=role, status=initial_status
        )
        db.session.add(new_account)
        db.session.commit()
        
        if role == 'staff':
            flash('Registration successful! Please wait for administrative dashboard activation approval.', 'info')
        else:
            flash('Registration completed! Proceeding to system log in portal.', 'success')
        return redirect(url_for('login_gate'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout_portal():
    logout_user()
    flash('Secure logout completed successfully.', 'success')
    return redirect(url_for('login_gate'))

# ==========================================
# 2. ADMINISTRATIVE PORTAL ROUTING Matrix
# ==========================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('login_gate'))
    
    # Text-based Global Search Logic Implementation
    search_query = request.args.get('search', '').strip()
    
    # Native analytical metric operations counters
    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='user').count()
    total_staff = User.query.filter_by(role='staff').count()
    total_bookings = Booking.query.count()
    
    if search_query:
        # Check against name patterns or ID parameters matches dynamically
        treks_list = Trek.query.filter((Trek.title.like(f"%{search_query}%")) | (Trek.id == search_query)).all()
        users_list = User.query.filter((User.role == 'user') & ((User.name.like(f"%{search_query}%")) | (User.id == search_query))).all()
        staff_list = User.query.filter((User.role == 'staff') & ((User.name.like(f"%{search_query}%")) | (User.id == search_query))).all()
    else:
        treks_list = Trek.query.all()
        users_list = User.query.filter_by(role='user').all()
        staff_list = User.query.filter_by(role='staff').all()
        
    all_bookings = Booking.query.order_by(Booking.id.desc()).all()
    
    return render_template('admin_dash.html', 
                           treks=treks_list, users=users_list, staff_members=staff_list, bookings=all_bookings,
                           t_treks=total_treks, t_users=total_users, t_staff=total_staff, t_bookings=total_bookings, search_val=search_query)

@app.route('/admin/trek/add', methods=['POST'])
@login_required
def admin_add_trek():
    if current_user.role != 'admin': return redirect(url_for('login_gate'))
    
    new_trek = Trek(
        title=request.form.get('title'),
        location=request.form.get('location'),
        difficulty=request.form.get('difficulty'),
        duration=int(request.form.get('duration')),
        total_slots=int(request.form.get('total_slots')),
        available_slots=int(request.form.get('total_slots')),
        start_date=request.form.get('start_date'),
        end_date=request.form.get('end_date'),
        status='Open'
    )
    db.session.add(new_trek)
    db.session.commit()
    flash('New target expedition successfully generated on system logs.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/trek/edit/<int:id>', methods=['POST'])
@login_required
def admin_edit_trek(id):
    if current_user.role != 'admin': return redirect(url_for('login_gate'))
    trek = Trek.query.get_or_400(id)
    trek.title = request.form.get('title')
    trek.location = request.form.get('location')
    trek.difficulty = request.form.get('difficulty')
    trek.duration = int(request.form.get('duration'))
    trek.status = request.form.get('status')
    
    # Readjust availability constraints safely
    slots = int(request.form.get('total_slots'))
    diff = slots - trek.total_slots
    trek.total_slots = slots
    trek.available_slots += diff
    
    db.session.commit()
    flash('Expedition updates updated.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/trek/assign/<int:id>', methods=['POST'])
@login_required
def admin_assign_staff(id):
    if current_user.role != 'admin': return redirect(url_for('login_gate'))
    trek = Trek.query.get_or_400(id)
    trek.staff_id = request.form.get('staff_id') or None
    db.session.commit()
    flash('Personnel assignments reassigned successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/status/<int:id>/<string:action>')
@login_required
def admin_toggle_status(id, action):
    if current_user.role != 'admin': return redirect(url_for('login_gate'))
    target_account = User.query.get_or_400(id)
    
    if action == 'approve': target_account.status = 'approved'
    elif action == 'blacklist': target_account.status = 'blacklisted'
    elif action == 'deactivate': target_account.status = 'pending'
    
    db.session.commit()
    flash(f'Account state parameter adjusted to: {target_account.status.upper()}', 'info')
    return redirect(url_for('admin_dashboard'))

# ==========================================
# 3. EXPEDITION STAFF FIELD OPERATIONS
# ==========================================

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'staff' or current_user.status != 'approved':
        return redirect(url_for('logout_portal'))
        
    assigned_treks = Trek.query.filter_by(staff_id=current_user.id).all()
    return render_template('staff_dash.html', treks=assigned_treks)

@app.route('/staff/trek/update/<int:id>', methods=['POST'])
@login_required
def staff_update_trek(id):
    if current_user.role != 'staff': return redirect(url_for('login_gate'))
    trek = Trek.query.get_or_400(id)
    
    # Guard check: Ensure only assigned staff can manage a trek
    if trek.staff_id != current_user.id:
        flash('Access Denied: You are not assigned as the operational manager for this trek entry.', 'danger')
        return redirect(url_for('staff_dashboard'))
        
    trek.status = request.form.get('status')
    trek.available_slots = int(request.form.get('available_slots'))
    db.session.commit()
    flash('Logistical operational data updated.', 'success')
    return redirect(url_for('staff_dashboard'))

# ==========================================
# 4. TREKKER CLIENT USER SPACE
# ==========================================

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user': return redirect(url_for('login_gate'))
    
    # Query logic filter definitions
    diff_filter = request.args.get('difficulty', '').strip()
    loc_filter = request.args.get('location', '').strip()
    search_title = request.args.get('search_title', '').strip()
    
    query = Trek.query.filter_by(status='Open')
    if diff_filter: query = query.filter_by(difficulty=diff_filter)
    if loc_filter: query = query.filter(Trek.location.like(f"%{loc_filter}%"))
    if search_title: query = query.filter(Trek.title.like(f"%{search_title}%"))
    
    available_treks = query.all()
    user_bookings = Booking.query.filter_by(user_id=current_user.id).all()
    
    return render_template('user_dash.html', treks=available_treks, bookings=user_bookings)

@app.route('/user/book/<int:trek_id>', methods=['POST'])
@login_required
def user_book_trek(trek_id):
    if current_user.role != 'user': return redirect(url_for('login_gate'))
    trek = Trek.query.get_or_400(trek_id)
    
    # Rule Validation Safeguards
    if trek.status != 'Open':
        flash('Booking rejected: Registration operations for this activity are currently closed.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    if trek.available_slots <= 0:
        flash('Booking rejected: All slots for this trek have been filled.', 'danger')
        return redirect(url_for('user_dashboard'))
        
    already_booked = Booking.query.filter_by(user_id=current_user.id, trek_id=trek_id, status='Booked').first()
    if already_booked:
        flash('You have already reserved a slot for this trek.', 'warning')
        return redirect(url_for('user_dashboard'))
        
    # Transaction Processing
    trek.available_slots -= 1
    new_booking = Booking(
        user_id=current_user.id,
        trek_id=trek.id,
        booking_date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Your slot reservation has been secured.', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/user/booking/cancel/<int:id>', methods=['POST'])
@login_required
def user_cancel_booking(id):
    if current_user.role != 'user': return redirect(url_for('login_gate'))
    booking = Booking.query.get_or_400(id)
    
    if booking.user_id != current_user.id:
        return redirect(url_for('user_dashboard'))
        
    if booking.status == 'Booked':
        booking.status = 'Cancelled'
        # Return slot back to availability counts pool safely
        booking.trek_event.available_slots += 1
        db.session.commit()
        flash('Reservation booking entry canceled successfully.', 'info')
        
    return redirect(url_for('user_dashboard'))

@app.route('/user/profile/update', methods=['POST'])
@login_required
def user_update_profile():
    if current_user.role != 'user': return redirect(url_for('login_gate'))
    current_user.name = request.form.get('name').strip()
    current_user.contact = request.form.get('contact').strip()
    db.session.commit()
    flash('Your identity verification contact profile parameters were saved.', 'success')
    return redirect(url_for('user_dashboard'))

# ==========================================
# SYSTEM ENGINE EXECUTION WRAPPER
# ==========================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)