import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from datetime import datetime, timedelta
import pandas as pd
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key') # Ye secret key aap Render par set kar sakte hain
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///panhome.db')
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class AppUser(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    mobile = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

    def __init__(self, username, email, mobile, password, role):
        self.username = username
        self.email = email
        self.mobile = mobile
        self.password_hash = generate_password_hash(password)
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accommodation_name = db.Column(db.String(100))
    room = db.Column(db.String(50))
    emp_id = db.Column(db.String(50), unique=True)
    name = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    nationality = db.Column(db.String(100))
    mobile_number = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Active')
    food_variety = db.Column(db.String(100))
    meal_time = db.Column(db.String(100))
    location = db.Column(db.String(100))
    remarks = db.Column(db.String(255))
    check_out_date = db.Column(db.String(50))
    shift_out_date = db.Column(db.String(50))
    def __repr__(self):
        return f'<Employee {self.name}>'

class Camp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))
    def __repr__(self):
        return f'<Camp {self.name}>'

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camp_id = db.Column(db.Integer, db.ForeignKey('camp.id'))
    room_number = db.Column(db.String(50), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=1)
    occupied_beds = db.Column(db.Integer, default=0)
    def __repr__(self):
        return f'<Room {self.room_number}>'

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Integer, default=0)

class InventoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'))
    item_name = db.Column(db.String(100))
    type = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    date = db.Column(db.String(50))
    emp_id = db.Column(db.String(50))
    room_number = db.Column(db.String(50))
    lpo_number = db.Column(db.String(50))
    supplier_name = db.Column(db.String(100))
    file_path = db.Column(db.String(255))

class MaintenanceReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    block = db.Column(db.String(50))
    section = db.Column(db.String(50))
    report_date = db.Column(db.String(50))
    details = db.Column(db.String(500))
    status = db.Column(db.String(20), default='Open')
    closed_date = db.Column(db.String(50))
    concern = db.Column(db.String(100))
    risk = db.Column(db.String(20))
    remarks = db.Column(db.String(500))
    attached_file = db.Column(db.String(255))

class AMCsService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String(50))
    date = db.Column(db.String(50))
    description = db.Column(db.String(500))
    supplier_name = db.Column(db.String(100))
    start_date = db.Column(db.String(50))
    end_date = db.Column(db.String(50))
    cost = db.Column(db.Float)
    type = db.Column(db.String(100))
    remarks = db.Column(db.String(255))
    duration = db.Column(db.String(50))
    remaining_days = db.Column(db.Integer)
    attached_file = db.Column(db.String(255))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return AppUser.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = AppUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

@app.route('/forgot_password')
def forgot_password():
    flash("You are not allowed to change or create the password. Please contact your IT administrator for help.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    status_filter = request.args.get('status')
    location_filter = request.args.get('location')
    
    total_employees = Employee.query.filter(Employee.status != 'Ex-Employee', Employee.status != 'Shifted-out').count()
    total_vacant_beds = db.session.query(func.sum(Room.capacity - Room.occupied_beds)).scalar() or 0
    total_on_vacation = Employee.query.filter_by(status='Vacation').count()
    total_resigned_terminated = Employee.query.filter(or_(Employee.status == 'Resigned', Employee.status == 'Terminated')).count()
    
    query = request.args.get('query', '')
    employees = Employee.query
    if query:
        employees = employees.filter(or_(Employee.emp_id.contains(query), Employee.name.contains(query)))
    
    if status_filter:
        employees = employees.filter_by(status=status_filter)
    
    if location_filter:
        employees = employees.filter_by(location=location_filter)
    
    employees = employees.order_by(Employee.status).all()
    
    employee_sort_order = {
        'Active': 0, 'On Leave': 1, 'Vacation': 2, 'Resigned': 3, 'Terminated': 4,
        'Shifted-out': 5, 'Ex-Employee': 6
    }
    
    employees.sort(key=lambda emp: employee_sort_order.get(emp.status, 99))
    
    location_summary = db.session.query(Employee.location, func.count(Employee.id)).group_by(Employee.location).all()

    return render_template('dashboard.html', 
                           total_employees=total_employees, 
                           total_vacant_beds=total_vacant_beds, 
                           total_on_vacation=total_on_vacation,
                           total_resigned_terminated=total_resigned_terminated,
                           employees=employees, 
                           query=query,
                           location_summary=location_summary)


@app.route('/edit_employee/<string:emp_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first_or_404()
    nationalities = ['Pakistani', 'Indian', 'Bangladeshi', 'Nepali', 'Filipino', 'Sri Lankan', 'Other']
    statuses = ['Active', 'Vacation', 'Resigned', 'Terminated', 'Other']
    food_varieties = ['Non-Veg Rice', 'Veg Rice', 'Non-Veg Chapati', 'Veg Chapati', 'Arabic', 'Veg/Non-Veg Roti']
    meal_times = ['Lunch', 'Dinner']

    if request.method == 'POST':
        if 'checkout_btn' in request.form:
            employee.status = 'Ex-Employee'
            employee.check_out_date = datetime.now().strftime('%Y-%m-%d')
            room_to_update = Room.query.filter_by(room_number=employee.room).first()
            if room_to_update:
                room_to_update.occupied_beds = max(0, room_to_update.occupied_beds - 1)
        elif 'shiftout_btn' in request.form:
            employee.status = 'Shifted-out'
            employee.shift_out_date = datetime.now().strftime('%Y-%m-%d')
            room_to_update = Room.query.filter_by(room_number=employee.room).first()
            if room_to_update:
                room_to_update.occupied_beds = max(0, room_to_update.occupied_beds - 1)
        else:
            employee.accommodation_name = request.form['accommodation_name']
            employee.room = request.form['room']
            employee.name = request.form['name']
            employee.designation = request.form['designation']
            employee.nationality = request.form['nationality']
            employee.mobile_number = request.form['mobile_number']
            employee.status = request.form['status']
            if employee.status == 'Other':
                employee.status = request.form['other_status']
            employee.food_variety = request.form['food_variety']
            employee.meal_time = request.form['meal_time']
            employee.location = request.form['location']
            employee.remarks = request.form['remarks']
        
        try:
            db.session.commit()
            flash('Employee data updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee data: {e}', 'danger')

    return render_template('edit_employee.html', employee=employee, nationalities=nationalities, statuses=statuses, food_varieties=food_varieties, meal_times=meal_times)

@app.route('/add_staff', methods=['GET', 'POST'])
@login_required
def add_staff():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
                try:
                    df = pd.read_excel(file) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
                    df = df.where(pd.notnull(df), 'N/A')
                    room_counts = df['Room'].value_counts()
                    
                    for _, row in df.iterrows():
                        try:
                            accommodation_name = row['Accommodation Name']
                            room_number = row['Room']
                            emp_id = str(row['EMP ID'])
                            
                            existing_emp = Employee.query.filter_by(emp_id=emp_id).first()
                            
                            if existing_emp:
                                existing_emp.accommodation_name = accommodation_name
                                existing_emp.room = room_number
                                existing_emp.name = row['NAME']
                                existing_emp.designation = row['Designation']
                                existing_emp.nationality = row['Nationality']
                                existing_emp.mobile_number = str(row['Mobile Number'])
                                existing_emp.status = row['Status']
                                existing_emp.food_variety = row['Food Variety']
                                existing_emp.meal_time = row['Meal Time']
                                existing_emp.location = row['Location']
                                existing_emp.remarks = row['Remarks']
                            else:
                                new_employee = Employee(
                                    accommodation_name=accommodation_name,
                                    room=room_number,
                                    emp_id=emp_id,
                                    name=row['NAME'],
                                    designation=row['Designation'],
                                    nationality=row['Nationality'],
                                    mobile_number=str(row['Mobile Number']),
                                    status=row['Status'],
                                    food_variety=row['Food Variety'],
                                    meal_time=row['Meal Time'],
                                    location=row['Location'],
                                    remarks=row['Remarks']
                                )
                                db.session.add(new_employee)

                            existing_camp = Camp.query.filter_by(name=accommodation_name).first()
                            if not existing_camp:
                                new_camp = Camp(name=accommodation_name, location=row.get('Location', 'N/A'))
                                db.session.add(new_camp)
                            
                            existing_room = Room.query.filter_by(room_number=room_number).first()
                            if not existing_room:
                                new_room = Room(
                                    camp_id=Camp.query.filter_by(name=accommodation_name).first().id, 
                                    room_number=room_number,
                                    capacity=int(row.get('Capacity', room_counts.get(room_number, 1))),
                                    occupied_beds=1
                                )
                                db.session.add(new_room)
                            else:
                                if existing_room.occupied_beds < existing_room.capacity:
                                    existing_room.occupied_beds += 1
                                
                        except Exception as e:
                            print(f"Skipping row due to error: {e}")
                    db.session.commit()
                    flash('Data uploaded and updated successfully from Excel!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'Error uploading data from Excel: {e}', 'danger')
            else:
                flash('Invalid file format. Please upload an Excel or CSV file.', 'danger')
        else:
            try:
                emp_id = request.form.get('emp_id')
                existing_emp = Employee.query.filter_by(emp_id=emp_id).first()
                if existing_emp:
                    flash('Employee with this EMP ID already exists.', 'danger')
                    return redirect(url_for('add_staff'))

                room_number = request.form.get('room')
                room_to_update = Room.query.filter_by(room_number=room_number).first()
                if room_to_update:
                    if room_to_update.occupied_beds < room_to_update.capacity:
                        room_to_update.occupied_beds += 1
                    else:
                        flash(f"Room {room_number} is already full.", 'danger')
                        return redirect(url_for('add_staff'))
                
                new_employee = Employee(
                    accommodation_name=request.form.get('accommodation_name'),
                    room=room_number,
                    emp_id=emp_id,
                    name=request.form.get('name'),
                    designation=request.form.get('designation'),
                    nationality=request.form.get('nationality'),
                    mobile_number=request.form.get('mobile_number'),
                    status='Active',
                    food_variety=request.form.get('food_variety'),
                    meal_time=request.form.get('meal_time'),
                    location=request.form.get('location'),
                    remarks=request.form.get('remarks')
                )
                db.session.add(new_employee)
                db.session.commit()
                flash('Employee added successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding employee: {e}', 'danger')
        return redirect(url_for('add_staff'))
    
    accommodations = Camp.query.all()
    vacant_rooms_data = []
    rooms = Room.query.all()
    for room in rooms:
        vacant_beds = room.capacity - room.occupied_beds
        for _ in range(vacant_beds):
            vacant_rooms_data.append(room)
            
    nationalities = ['Pakistani', 'Indian', 'Bangladeshi', 'Nepali', 'Filipino', 'Sri Lankan', 'Other']
    food_varieties = ['Non-Veg Rice', 'Veg Rice', 'Non-Veg Chapati', 'Veg Chapati', 'Arabic', 'Veg/Non-Veg Roti']
    meal_times = ['Lunch', 'Dinner']
    return render_template('add_staff.html', accommodations=accommodations, vacant_rooms=vacant_rooms_data, nationalities=nationalities, food_varieties=food_varieties, meal_times=meal_times)

@app.route('/data', methods=['GET', 'POST'])
@login_required
def data_management():
    if request.method == 'POST':
        download_type = request.form.get('download_type')
        filter_value = request.form.get('filter_value')
        
        employees = Employee.query
        
        if download_type == 'location' and filter_value:
            employees = employees.filter(Employee.location == filter_value)
        elif download_type == 'status' and filter_value:
            employees = employees.filter(Employee.status == filter_value)
        
        employees_df = pd.read_sql(employees.statement, db.engine)
        
        buffer = io.BytesIO()
        employees_df.to_excel(buffer, index=False)
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, download_name='employee_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    locations = db.session.query(Employee.location).distinct().all()
    statuses = ['Active', 'Vacation', 'Resigned', 'Terminated', 'Shifted-out', 'Ex-Employee', 'Other']
    
    return render_template('data.html', locations=locations, statuses=statuses)

@app.route('/inventory')
@login_required
def inventory_dashboard():
    items = InventoryItem.query.all()
    
    total_received_qty = db.session.query(func.sum(InventoryTransaction.quantity)).filter_by(type='Incoming').scalar() or 0
    total_distributed_qty = db.session.query(func.sum(InventoryTransaction.quantity)).filter_by(type='Outgoing').scalar() or 0
    current_stock = db.session.query(func.sum(InventoryItem.quantity)).scalar() or 0
    
    return render_template('inventory_dashboard.html', 
                           items=items, 
                           total_received_qty=total_received_qty,
                           total_distributed_qty=total_distributed_qty,
                           current_stock=current_stock)

@app.route('/incoming', methods=['GET', 'POST'])
@login_required
def incoming_inventory():
    if request.method == 'POST':
        item_name = request.form.get('item_description')
        quantity = int(request.form.get('received_qty'))
        supplier_name = request.form.get('supplier_name')
        lpo_number = request.form.get('lpo_number')
        remarks = request.form.get('remarks')
        
        file = request.files.get('attached_file')
        file_path = None
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        item = InventoryItem.query.filter_by(name=item_name).first()
        if not item:
            item = InventoryItem(name=item_name, quantity=0)
            db.session.add(item)
            db.session.commit()

        item.quantity += quantity
        
        new_transaction = InventoryTransaction(
            item_id=item.id,
            item_name=item.name,
            type='Incoming',
            quantity=quantity,
            date=datetime.now().strftime('%Y-%m-%d'),
            supplier_name=supplier_name,
            lpo_number=lpo_number,
            file_path=file_path
        )

        db.session.add(new_transaction)
        db.session.commit()
        flash(f"{quantity} {item_name}(s) received successfully!", "success")
        return redirect(url_for('inventory_dashboard'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('incoming_inventory.html', today=today)

@app.route('/outgoing', methods=['GET', 'POST'])
@login_required
def outgoing_inventory():
    employees = Employee.query.all()
    items = InventoryItem.query.all()
    
    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        item_name = request.form.get('item_description')
        quantity = int(request.form.get('quantity'))
        
        file = request.files.get('attached_file')
        file_path = None
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        
        employee = Employee.query.filter_by(emp_id=emp_id).first()
        item = InventoryItem.query.filter_by(name=item_name).first()
        
        if not employee:
            flash("Employee not found.", "danger")
            return redirect(url_for('outgoing_inventory'))
        
        if not item or item.quantity < quantity:
            flash("Not enough stock for this item.", "danger")
            return redirect(url_for('outgoing_inventory'))

        item.quantity -= quantity
        
        new_transaction = InventoryTransaction(
            item_id=item.id,
            item_name=item.name,
            type='Outgoing',
            quantity=quantity,
            date=datetime.now().strftime('%Y-%m-%d'),
            emp_id=emp_id,
            room_number=employee.room,
            file_path=file_path
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash(f"{quantity} {item_name}(s) distributed to {employee.name} successfully!", "success")
        return redirect(url_for('inventory_dashboard'))

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('outgoing_inventory.html', today=today, employees=employees, items=items)

@app.route('/get_employee_details/<string:emp_id>')
@login_required
def get_employee_details(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first()
    if employee:
        return jsonify({
            'name': employee.name,
            'room': employee.room,
            'designation': employee.designation,
            'location': employee.location
        })
    return jsonify({})

@app.route('/inventory/transactions/<string:transaction_type>')
@login_required
def inventory_transactions(transaction_type):
    transactions = InventoryTransaction.query.filter_by(type=transaction_type).order_by(InventoryTransaction.date.desc()).all()
    return render_template('inventory_transactions.html', transactions=transactions, transaction_type=transaction_type)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/check_in_staff/<string:emp_id>', methods=['POST'])
@login_required
def check_in_staff(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first_or_404()
    if employee.status in ['Ex-Employee', 'Shifted-out']:
        employee.status = 'Active'
        employee.check_out_date = None
        employee.shift_out_date = None
        db.session.commit()
        flash(f"Staff {employee.name} has been checked back in. Please assign a new room.", 'success')
    return redirect(url_for('edit_employee', emp_id=emp_id))

@app.route('/maintenance')
@login_required
def maintenance_report():
    reports = MaintenanceReport.query.order_by(MaintenanceReport.report_date.desc()).all()
    return render_template('maintenance_report.html', reports=reports)

@app.route('/add_maintenance', methods=['GET', 'POST'])
@login_required
def add_maintenance():
    if request.method == 'POST':
        block = request.form.get('block')
        section = request.form.get('section')
        report_date = request.form.get('report_date')
        details = request.form.get('details')
        status = request.form.get('status')
        closed_date = request.form.get('closed_date')
        concern = request.form.get('concern')
        if concern == 'Outsource':
            concern = request.form.get('outsource_name')
        risk = request.form.get('risk')
        remarks = request.form.get('remarks')
        
        file = request.files.get('attached_file')
        file_path = None
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        new_report = MaintenanceReport(
            block=block,
            section=section,
            report_date=report_date,
            details=details,
            status=status,
            closed_date=closed_date if status == 'Closed' else None,
            concern=concern,
            risk=risk,
            remarks=remarks,
            attached_file=file_path
        )
        db.session.add(new_report)
        db.session.commit()
        flash("Maintenance report added successfully!", "success")
        return redirect(url_for('maintenance_report'))
        
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_maintenance.html', today=today)

@app.route('/edit_maintenance/<int:report_id>', methods=['GET', 'POST'])
@login_required
def edit_maintenance(report_id):
    report = MaintenanceReport.query.get_or_404(report_id)
    if request.method == 'POST':
        report.block = request.form.get('block')
        report.section = request.form.get('section')
        report.report_date = request.form.get('report_date')
        report.details = request.form.get('details')
        report.status = request.form.get('status')
        report.closed_date = request.form.get('closed_date') if request.form.get('status') == 'Closed' else None
        report.concern = request.form.get('concern')
        if report.concern == 'Outsource':
            report.concern = request.form.get('outsource_name')
        report.risk = request.form.get('risk')
        report.remarks = request.form.get('remarks')
        
        file = request.files.get('attached_file')
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            report.attached_file = file_path
            
        db.session.commit()
        flash("Maintenance report updated successfully!", "success")
        return redirect(url_for('maintenance_report'))
        
    return render_template('edit_maintenance.html', report=report)

@app.route('/view_maintenance_report/<int:report_id>')
@login_required
def view_maintenance_report(report_id):
    report = MaintenanceReport.query.get_or_404(report_id)
    return render_template('view_maintenance_report.html', report=report)

@app.route('/amcs')
@login_required
def amcs_dashboard():
    amcs_list = AMCsService.query.all()
    try:
        for amc in amcs_list:
            end_date = datetime.strptime(amc.end_date, '%Y-%m-%d')
            remaining = end_date - datetime.now()
            amc.remaining_days = remaining.days if remaining.days > 0 else 0
            amc.status = 'Active' if amc.remaining_days > 0 else 'Expired'
        
        db.session.commit()
        return render_template('amcs_dashboard.html', amcs_list=amcs_list)

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {e}. Please ensure your database is up to date and restart the application.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/amcs/add', methods=['GET', 'POST'])
@login_required
def add_amcs():
    if request.method == 'POST':
        service_id = request.form.get('service_id')
        date = request.form.get('date')
        type = request.form.get('type')
        supplier_name = request.form.get('supplier_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        remarks = request.form.get('remarks')
        
        file = request.files.get('attached_file')
        file_path = None
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        duration = (end - start).days

        new_amc = AMCsService(
            service_id=service_id,
            date=date,
            type=type,
            supplier_name=supplier_name,
            start_date=start_date,
            end_date=end_date,
            remarks=remarks,
            duration=duration,
            remaining_days=duration,
            attached_file=file_path
        )
        db.session.add(new_amc)
        db.session.commit()
        flash("AMC service added successfully!", "success")
        return redirect(url_for('amcs_dashboard'))

    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('add_amcs.html', today=today)


@app.route('/amcs/edit/<int:amc_id>', methods=['GET', 'POST'])
@login_required
def edit_amcs(amc_id):
    amc = AMCsService.query.get_or_404(amc_id)
    if request.method == 'POST':
        amc.service_id = request.form.get('service_id')
        amc.date = request.form.get('date')
        amc.type = request.form.get('type')
        amc.supplier_name = request.form.get('supplier_name')
        amc.start_date = request.form.get('start_date')
        amc.end_date = request.form.get('end_date')
        amc.remarks = request.form.get('remarks')

        file = request.files.get('attached_file')
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            amc.attached_file = file_path

        start = datetime.strptime(amc.start_date, '%Y-%m-%d')
        end = datetime.strptime(amc.end_date, '%Y-%m-%d')
        amc.duration = (end - start).days

        db.session.commit()
        flash("AMC service updated successfully!", "success")
        return redirect(url_for('amcs_dashboard'))

    return render_template('edit_amcs.html', amc=amc)


@app.route('/amcs/view/<int:amc_id>')
@login_required
def view_amcs(amc_id):
    amc = AMCsService.query.get_or_404(amc_id)
    return render_template('view_amcs.html', amc=amc)

@app.route('/amcs/download/<int:amc_id>')
@login_required
def download_amcs_file(amc_id):
    amc = AMCsService.query.get_or_404(amc_id)
    if amc.attached_file and os.path.exists(amc.attached_file):
        return send_file(amc.attached_file, as_attachment=True)
    flash("No file attached to this AMC record.", "danger")
    return redirect(url_for('amcs_dashboard'))

@app.route('/settings')
@login_required
def settings_dashboard():
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))
    return render_template('settings_dashboard.html', users=AppUser.query.all())

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        role = request.form.get('role')

        if AppUser.query.filter_by(username=username).first():
            flash("Username already exists.", 'danger')
        else:
            new_user = AppUser(username, email, mobile, password, role)
            db.session.add(new_user)
            db.session.commit()
            flash(f"User {username} added successfully!", 'success')
            return redirect(url_for('settings_dashboard'))
    
    return render_template('add_user.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))
    
    user_to_edit = AppUser.query.get_or_404(user_id)
    if request.method == 'POST':
        user_to_edit.username = request.form.get('username')
        user_to_edit.email = request.form.get('email')
        user_to_edit.mobile = request.form.get('mobile')
        user_to_edit.role = request.form.get('role')
        new_password = request.form.get('password')
        if new_password:
            user_to_edit.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("User updated successfully!", 'success')
        return redirect(url_for('settings_dashboard'))
    
    return render_template('edit_user.html', user=user_to_edit)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))

    user_to_delete = AppUser.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
    else:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User deleted successfully!", 'success')
    
    return redirect(url_for('settings_dashboard'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        admin_user = AppUser.query.filter_by(username='admin').first()
        if not admin_user:
            new_admin = AppUser(username='admin', email='admin@panhome.com', mobile='N/A', password='admin123', role='admin')
            db.session.add(new_admin)
            db.session.commit()
    app.run(debug=True)