import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
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
    theme = db.Column(db.String(20), default='default')
    font_style = db.Column(db.String(20), default='inter')
    font_size = db.Column(db.String(20), default='normal')

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

class Camp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    camp_id = db.Column(db.Integer, db.ForeignKey('camp.id'))
    room_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(50), default='Vacant')

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
    return db.session.get(AppUser, int(user_id))

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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/forgot_password')
def forgot_password():
    flash("You are not allowed to change or create the password. Please contact your IT administrator for help.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    status_filter = request.args.get('status')
    location_filter = request.args.get('location')
    query = request.args.get('query', '')
    active_statuses = ['Active', 'Vacation', 'On Leave', 'Resigned', 'Terminated']
    
    total_employees = Employee.query.filter(Employee.status.in_(active_statuses)).count()
    total_vacant_beds = Employee.query.filter_by(status='Vacant').count()
    total_on_vacation = Employee.query.filter_by(status='Vacation').count()
    total_resigned_terminated = Employee.query.filter(or_(Employee.status == 'Resigned', Employee.status == 'Terminated')).count()
    
    location_summary = db.session.query(Employee.location, func.count(Employee.id)).filter(
        Employee.status.in_(active_statuses)
    ).group_by(Employee.location).all()
    
    employees_query = Employee.query.filter(Employee.status != 'Ex-Employee', Employee.status != 'Shifted-out')

    if status_filter:
        employees_query = employees_query.filter_by(status=status_filter)
    if location_filter:
        employees_query = employees_query.filter_by(location=location_filter)
    if query:
        search_filter = or_(
            Employee.emp_id.contains(query), 
            Employee.name.contains(query),
            Employee.room.contains(query)
        )
        employees_query = employees_query.filter(search_filter)
        
    sort_order = { 'Vacant': -1, 'Active': 0, 'On Leave': 1, 'Vacation': 2, 'Resigned': 3, 'Terminated': 4 }
    employees = sorted(
        employees_query.all(),
        key=lambda item: (sort_order.get(item.status, 99), item.room, item.name)
    )

    return render_template('dashboard.html', 
                           total_employees=total_employees, total_vacant_beds=total_vacant_beds, 
                           total_on_vacation=total_on_vacation, total_resigned_terminated=total_resigned_terminated,
                           employees=employees, query=query, location_summary=location_summary)

@app.route('/edit_employee/<string:emp_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first_or_404()
    is_vacant_record = employee.status == 'Vacant'
    nationalities = ['Afghan', 'Algerian', 'American', 'Andorran', 'Angolan', 'Antiguans', 'Argentinean', 'Armenian', 'Australian', 'Austrian', 'Azerbaijani', 'Bahamian', 'Bahraini', 'Bangladeshi', 'Barbadian', 'Barbudans', 'Batswana', 'Belarusian', 'Belgian', 'Belizean', 'Beninese', 'Bhutanese', 'Bolivian', 'Bosnian', 'Brazilian', 'British', 'Bruneian', 'Bulgarian', 'Burkinabe', 'Burmese', 'Burundian', 'Cambodian', 'Cameroonian', 'Canadian', 'Cape Verdean', 'Central African', 'Chadian', 'Chilean', 'Chinese', 'Colombian', 'Comoran',  'Congolese', 'Costa Rican', 'Croatian', 'Cuban', 'Cypriot', 'Czech', 'Danish', 'Djibouti', 'Dominican', 'Dutch', 'East Timorese', 'Ecuadorean', 'Egyptian', 'Emirian', 'Equatorial Guinean', 'Eritrean', 'Estonian', 'Ethiopian', 'Fijian', 'Filipino', 'Finnish', 'French', 'Gabonese', 'Gambian', 'Georgian', 'German', 'Ghanaian', 'Greek', 'Grenadian', 'Guatemalan', 'Guinea-Bissauan', 'Guinean', 'Guyanese', 'Haitian', 'Herzegovinian', 'Honduran', 'Hungarian', 'I-Kiribati', 'Icelander', 'Indian', 'Indonesian', 'Iranian', 'Iraqi', 'Irish', 'Israeli', 'Italian', 'Ivorian', 'Jamaican', 'Japanese', 'Jordanian', 'Kazakhstani', 'Kenyan', 'Kittian and Nevisian', 'Kuwaiti', 'Kyrgyz', 'Laotian', 'Latvian', 'Lebanese', 'Liberian', 'Libyan', 'Liechtensteiner', 'Lithuanian', 'Luxembourger', 'Macedonian', 'Malagasy', 'Malawian', 'Malaysian', 'Maldivan', 'Malian', 'Maltese', 'Marshallese', 'Mauritanian', 'Mauritian', 'Mexican', 'Micronesian', 'Moldovan', 'Monacan', 'Mongolian', 'Moroccan', 'Mosotho', 'Motswana', 'Mozambican', 'Namibian', 'Nauruan', 'Nepalese', 'New Zealander', 'Nicaraguan', 'Nigerian', 'Nigerien', 'North Korean', 'Northern Irish', 'Norwegian', 'Omani', 'Pakistani', 'Palauan', 'Panamanian', 'Papua New Guinean', 'Paraguayan', 'Peruvian', 'Polish', 'Portuguese', 'Qatari', 'Romanian', 'Russian', 'Rwandan', 'Saint Lucian', 'Salvadoran', 'Samoan', 'San Marinese', 'Sao Tomean', 'Saudi', 'Scottish', 'Senegalese', 'Serbian', 'Seychellois', 'Sierra Leonean', 'Singaporean', 'Slovakian', 'Slovenian', 'Solomon Islander', 'Somali', 'South African', 'South Korean', 'Spanish', 'Sri Lankan', 'Sudanese', 'Surinamer', 'Swazi', 'Swedish', 'Swiss', 'Syrian', 'Taiwanese', 'Tajik', 'Tanzanian', 'Thai', 'Togolese', 'Tongan', 'Trinidadian or Tobagonian', 'Tunisian', 'Turkish', 'Tuvaluan', 'Ugandan', 'Ukrainian', 'Uruguayan', 'Uzbekistani', 'Venezuelan', 'Vietnamese', 'Welsh', 'Yemenite', 'Zambian', 'Zimbabwean']
    food_varieties = ['Non-Veg Rice', 'Veg Rice', 'Non-Veg Chapati', 'Veg Chapati', 'Arabic', 'Veg/Non-Veg Roti']
    meal_times = ['Lunch', 'Dinner']
    statuses = ['Active', 'Vacation', 'Resigned', 'Terminated', 'Other']

    if request.method == 'POST':
        try:
            if 'checkout_btn' in request.form or 'shiftout_btn' in request.form:
                new_status = 'Ex-Employee' if 'checkout_btn' in request.form else 'Shifted-out'
                employee.status = new_status
                if new_status == 'Ex-Employee':
                    employee.check_out_date = datetime.now().strftime('%Y-%m-%d')
                else:
                    employee.shift_out_date = datetime.now().strftime('%Y-%m-%d')
                
                new_vacant_id = f"VACANT_{employee.room}_{int(datetime.now().timestamp())}"
                vacant_bed = Employee(
                    emp_id=new_vacant_id, status='Vacant', name='-',
                    accommodation_name=employee.accommodation_name,
                    room=employee.room, location=employee.location,
                    designation='-', nationality='-', mobile_number='-',
                    food_variety='-', meal_time='-', remarks='Bedspace'
                )
                db.session.add(vacant_bed)
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
            
            db.session.commit()
            flash('Data updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating data: {e}', 'danger')

    return render_template('edit_employee.html', 
                           employee=employee, is_vacant_record=is_vacant_record,
                           nationalities=nationalities, food_varieties=food_varieties,
                           meal_times=meal_times, statuses=statuses)

@app.route('/add_staff', methods=['GET', 'POST'])
@login_required
def add_staff():
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
                try:
                    read_method = pd.read_excel if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv
                    df = read_method(file, dtype=str)
                    df.fillna('N/A', inplace=True)
                    accommodations_in_file = df['Accommodation Name'].unique().tolist()
                    if accommodations_in_file:
                        Employee.query.filter(Employee.accommodation_name.in_(accommodations_in_file)).delete(synchronize_session=False)
                    vacant_counters = {}
                    for _, row in df.iterrows():
                        accommodation_name = row.get('Accommodation Name', 'N/A')
                        if accommodation_name not in accommodations_in_file: continue
                        room_number = str(row.get('Room', 'N/A'))
                        status = row.get('Status', 'N/A')
                        if accommodation_name == 'N/A' or room_number == 'N/A': continue
                        existing_camp = Camp.query.filter_by(name=accommodation_name).first()
                        if not existing_camp:
                            new_camp = Camp(name=accommodation_name, location=row.get('Location', 'N/A'))
                            db.session.add(new_camp)
                        emp_id = str(row.get('EMP ID', 'N/A'))
                        if status.lower() == 'vacant':
                            vacant_counters.setdefault(room_number, 0)
                            vacant_counters[room_number] += 1
                            emp_id = f"VACANT_{room_number}_{vacant_counters[room_number]}"
                        bed = Employee(
                            accommodation_name=accommodation_name, room=room_number,
                            status=status, emp_id=emp_id, name=row.get('NAME', '-'),
                            designation=row.get('Designation', '-'), nationality=row.get('Nationality', '-'),
                            mobile_number=str(row.get('Mobile Number', '-')), food_variety=row.get('Food Variety', '-'),
                            meal_time=row.get('Meal Time', '-'), location=row.get('Location', 'N/A'),
                            remarks=row.get('Remarks', '')
                        )
                        db.session.add(bed)
                    db.session.commit()
                    flash('File uploaded and data synchronized successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'File upload failed: {e}', 'danger')
            else:
                flash('Invalid file format. Please upload an Excel or CSV file.', 'danger')
        else:
            try:
                emp_id_to_assign = request.form.get('emp_id')
                vacant_bed_id = request.form.get('vacant_bed_id')
                vacant_bed = db.session.get(Employee, int(vacant_bed_id))
                if not vacant_bed or vacant_bed.status != 'Vacant':
                    flash('Selected bed is not vacant.', 'danger')
                    return redirect(url_for('add_staff'))
                vacant_bed.emp_id = emp_id_to_assign
                vacant_bed.name = request.form.get('name')
                vacant_bed.designation = request.form.get('designation')
                vacant_bed.nationality = request.form.get('nationality')
                vacant_bed.mobile_number = request.form.get('mobile_number')
                vacant_bed.status = 'Active'
                vacant_bed.food_variety = request.form.get('food_variety')
                vacant_bed.meal_time = request.form.get('meal_time')
                vacant_bed.remarks = request.form.get('remarks')
                db.session.commit()
                flash('Employee assigned to bed successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error assigning employee: {e}', 'danger')
        return redirect(url_for('dashboard'))
    
    accommodations = Camp.query.order_by(Camp.name).all()
    vacant_beds_query = Employee.query.filter_by(status='Vacant').order_by(Employee.accommodation_name, Employee.room).all()
    vacant_beds_list = [{'id': bed.id, 'accommodation_name': bed.accommodation_name, 'room': bed.room, 'emp_id': bed.emp_id} for bed in vacant_beds_query]
    nationalities = ['Pakistani', 'Indian', 'Bangladeshi', 'Nepali', 'Filipino', 'Sri Lankan', 'Other']
    food_varieties = ['Non-Veg Rice', 'Veg Rice', 'Non-Veg Chapati', 'Veg Chapati', 'Arabic', 'Veg/Non-Veg Roti']
    meal_times = ['Lunch', 'Dinner']
    return render_template('add_staff.html', 
                           accommodations=accommodations, vacant_beds=vacant_beds_list,
                           nationalities=nationalities, food_varieties=food_varieties,
                           meal_times=meal_times)

@app.route('/data', methods=['GET', 'POST'])
@login_required
def data_management():
    if request.method == 'POST':
        download_type = request.form.get('download_type')
        filter_value = request.form.get('filter_value')
        employees_query = Employee.query
        if download_type and filter_value:
            if download_type == 'location':
                employees_query = employees_query.filter(Employee.location == filter_value)
            elif download_type == 'status':
                employees_query = employees_query.filter(Employee.status == filter_value)
            elif download_type == 'accommodation':
                employees_query = employees_query.filter(Employee.accommodation_name == filter_value)
        employees_df = pd.read_sql(employees_query.statement, db.engine)
        buffer = io.BytesIO()
        employees_df.to_excel(buffer, index=False)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='employee_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    active_statuses = ['Active', 'Vacation', 'On Leave', 'Resigned', 'Terminated']
    locations_query = db.session.query(Employee.location).filter(Employee.location.isnot(None)).distinct().order_by(Employee.location).all()
    statuses_query = db.session.query(Employee.status).filter(Employee.status.isnot(None)).distinct().order_by(Employee.status).all()
    accommodations_query = Camp.query.order_by(Camp.name).all()
    accommodations_list = [{'name': camp.name} for camp in accommodations_query]
    designation_summary = db.session.query(Employee.designation, func.count(Employee.id)).filter(Employee.status.in_(active_statuses)).group_by(Employee.designation).order_by(func.count(Employee.id).desc()).all()
    nationality_summary = db.session.query(Employee.nationality, func.count(Employee.id)).filter(Employee.status.in_(active_statuses)).group_by(Employee.nationality).order_by(func.count(Employee.id).desc()).all()
    return render_template('data.html', 
                           locations=[loc[0] for loc in locations_query if loc[0]],
                           statuses=[s[0] for s in statuses_query if s[0]],
                           accommodations=accommodations_list,
                           designation_summary=designation_summary,
                           nationality_summary=nationality_summary)

@app.route('/inventory')
@login_required
def inventory_dashboard():
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    total_received_qty = db.session.query(func.sum(InventoryTransaction.quantity)).filter_by(type='Incoming').scalar() or 0
    total_distributed_qty = db.session.query(func.sum(InventoryTransaction.quantity)).filter_by(type='Outgoing').scalar() or 0
    current_stock = db.session.query(func.sum(InventoryItem.quantity)).scalar() or 0
    return render_template('inventory_dashboard.html', items=items, total_received_qty=total_received_qty, total_distributed_qty=total_distributed_qty, current_stock=current_stock)

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_inventory_item():
    if request.method == 'POST':
        item_name = request.form.get('name')
        if not item_name:
            flash('Item name cannot be empty.', 'danger')
        elif InventoryItem.query.filter(func.lower(InventoryItem.name) == func.lower(item_name)).first():
            flash('An item with this name already exists.', 'danger')
        else:
            new_item = InventoryItem(name=item_name, quantity=0)
            db.session.add(new_item)
            db.session.commit()
            flash(f'Item "{item_name}" added successfully.', 'success')
            return redirect(url_for('inventory_dashboard'))
    return render_template('add_inventory.html')

@app.route('/inventory/incoming', methods=['GET', 'POST'])
@login_required
def incoming_inventory():
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        quantity = int(request.form.get('quantity'))
        item = db.session.get(InventoryItem, int(item_id))
        if item:
            item.quantity += quantity
            file = request.files.get('attached_file')
            filename = None
            if file and file.filename:
                filename = file.filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_transaction = InventoryTransaction(
                item_id=item.id, item_name=item.name, type='Incoming', quantity=quantity,
                date=datetime.now().strftime('%Y-%m-%d'),
                supplier_name=request.form.get('supplier_name'),
                lpo_number=request.form.get('lpo_number'),
                file_path=filename
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash(f"{quantity} {item.name}(s) received successfully!", "success")
            return redirect(url_for('inventory_dashboard'))
        else:
            flash("Item not found.", "danger")
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template('incoming_inventory.html', items=items, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/inventory/outgoing', methods=['GET', 'POST'])
@login_required
def outgoing_inventory():
    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        item_id = request.form.get('item_id')
        quantity = int(request.form.get('quantity'))
        employee = Employee.query.filter_by(emp_id=emp_id).first()
        item = db.session.get(InventoryItem, int(item_id))
        if not employee:
            flash("Employee not found.", "danger")
        elif not item or item.quantity < quantity:
            flash("Not enough stock for this item.", "danger")
        else:
            item.quantity -= quantity
            file = request.files.get('attached_file')
            filename = None
            if file and file.filename:
                filename = file.filename
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_transaction = InventoryTransaction(
                item_id=item.id, item_name=item.name, type='Outgoing', 
                quantity=quantity, date=datetime.now().strftime('%Y-%m-%d'),
                emp_id=emp_id, room_number=employee.room, file_path=filename
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash(f"{quantity} {item.name}(s) distributed to {employee.name} successfully!", "success")
            return redirect(url_for('inventory_dashboard'))
    active_employees = Employee.query.filter(Employee.status.in_(['Active', 'Vacation'])).all()
    items = InventoryItem.query.filter(InventoryItem.quantity > 0).order_by(InventoryItem.name).all()
    return render_template('outgoing_inventory.html', today=datetime.now().strftime('%Y-%m-%d'), employees=active_employees, items=items)

@app.route('/get_employee_details/<string:emp_id>')
@login_required
def get_employee_details(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first()
    if employee:
        return jsonify({
            'name': employee.name, 'room': employee.room, 'designation': employee.designation, 
            'location': employee.location, 'accommodation_name': employee.accommodation_name
        })
    return jsonify({'error': 'Employee not found'}), 404

@app.route('/inventory/transactions/<string:transaction_type>')
@login_required
def inventory_transactions(transaction_type):
    transactions = InventoryTransaction.query.filter_by(type=transaction_type).order_by(InventoryTransaction.date.desc()).all()
    return render_template('inventory_transactions.html', transactions=transactions, transaction_type=transaction_type.title())

@app.route('/maintenance')
@login_required
def maintenance_report():
    reports = MaintenanceReport.query.order_by(MaintenanceReport.report_date.desc()).all()
    return render_template('maintenance_report.html', reports=reports)

@app.route('/add_maintenance', methods=['GET', 'POST'])
@login_required
def add_maintenance():
    if request.method == 'POST':
        file = request.files.get('attached_file')
        filename = None
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_report = MaintenanceReport(
            block=request.form.get('block'), section=request.form.get('section'),
            report_date=request.form.get('report_date'), details=request.form.get('details'),
            status=request.form.get('status'), concern=request.form.get('concern'),
            risk=request.form.get('risk'), remarks=request.form.get('remarks'),
            closed_date=datetime.now().strftime('%Y-%m-%d') if request.form.get('status') == 'Closed' else None,
            attached_file=filename
        )
        db.session.add(new_report)
        db.session.commit()
        flash("Maintenance report added successfully!", "success")
        return redirect(url_for('maintenance_report'))
    return render_template('add_maintenance.html', today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/edit_maintenance/<int:report_id>', methods=['GET', 'POST'])
@login_required
def edit_maintenance(report_id):
    report = db.session.get(MaintenanceReport, report_id)
    if not report: return redirect(url_for('maintenance_report'))
    if request.method == 'POST':
        report.block = request.form.get('block')
        report.section = request.form.get('section')
        report.report_date = request.form.get('report_date')
        report.details = request.form.get('details')
        report.status = request.form.get('status')
        report.closed_date = datetime.now().strftime('%Y-%m-%d') if request.form.get('status') == 'Closed' and not report.closed_date else report.closed_date
        report.concern = request.form.get('concern')
        report.risk = request.form.get('risk')
        report.remarks = request.form.get('remarks')
        file = request.files.get('attached_file')
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            report.attached_file = filename
        db.session.commit()
        flash("Maintenance report updated successfully!", "success")
        return redirect(url_for('maintenance_report'))
    return render_template('edit_maintenance.html', report=report)

@app.route('/view_maintenance_report/<int:report_id>')
@login_required
def view_maintenance_report(report_id):
    report = db.session.get(MaintenanceReport, report_id)
    return render_template('view_maintenance_report.html', report=report)

@app.route('/amcs')
@login_required
def amcs_dashboard():
    amcs_list = AMCsService.query.all()
    try:
        for amc in amcs_list:
            end_date = datetime.strptime(amc.end_date, '%Y-%m-%d')
            remaining = end_date - datetime.now()
            amc.remaining_days = max(0, remaining.days)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error calculating remaining days: {e}', 'danger')
    return render_template('amcs_dashboard.html', amcs_list=amcs_list)

@app.route('/amcs/add', methods=['GET', 'POST'])
@login_required
def add_amcs():
    if request.method == 'POST':
        file = request.files.get('attached_file')
        filename = None
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        new_amc = AMCsService(
            service_id=request.form.get('service_id'), date=request.form.get('date'),
            type=request.form.get('type'), supplier_name=request.form.get('supplier_name'),
            start_date=request.form.get('start_date'), end_date=request.form.get('end_date'),
            remarks=request.form.get('remarks'), duration=(end_date - start_date).days,
            attached_file=filename
        )
        db.session.add(new_amc)
        db.session.commit()
        flash("AMC service added successfully!", "success")
        return redirect(url_for('amcs_dashboard'))
    return render_template('add_amcs.html', today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/amcs/edit/<int:amc_id>', methods=['GET', 'POST'])
@login_required
def edit_amcs(amc_id):
    amc = db.session.get(AMCsService, amc_id)
    if not amc: return redirect(url_for('amcs_dashboard'))
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            amc.attached_file = filename
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
    amc = db.session.get(AMCsService, amc_id)
    return render_template('view_amcs.html', amc=amc)

@app.route('/uploads/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/settings')
@login_required
def settings_dashboard():
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))
    users = AppUser.query.all()
    return render_template('settings.html', users=users)

@app.route('/settings/change_appearance', methods=['POST'])
@login_required
def change_appearance():
    theme = request.form.get('theme')
    font_style = request.form.get('font_style')
    font_size = request.form.get('font_size')
    
    user = db.session.get(AppUser, current_user.id)
    
    if theme in ['default', 'dark', 'light', 'blue', 'ocean', 'skyblue', 'darkgreen', 'darkgold']:
        user.theme = theme
    if font_style in ['inter', 'poppins', 'roboto-slab']:
        user.font_style = font_style
    if font_size in ['small', 'normal', 'large']:
        user.font_size = font_size
        
    db.session.commit()
    flash('Appearance settings updated successfully!', 'success')
    return redirect(url_for('settings_dashboard'))

@app.route('/settings/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        if AppUser.query.filter_by(username=username).first():
            flash("Username already exists.", 'danger')
        else:
            new_user = AppUser(
                username=username, email=request.form.get('email'),
                mobile=request.form.get('mobile'), password=request.form.get('password'),
                role=request.form.get('role')
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"User {username} added successfully!", 'success')
            return redirect(url_for('settings_dashboard'))
    return render_template('add_user.html')

@app.route('/settings/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))
    user_to_edit = db.session.get(AppUser, user_id)
    if not user_to_edit:
        flash("User not found.", "danger")
        return redirect(url_for('settings_dashboard'))
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

@app.route('/settings/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin():
        flash("You do not have permission to access this page.", 'danger')
        return redirect(url_for('dashboard'))
    if user_id == current_user.id:
        flash("You cannot delete your own account.", 'danger')
        return redirect(url_for('settings_dashboard'))
    user_to_delete = db.session.get(AppUser, user_id)
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash("User deleted successfully!", 'success')
    else:
        flash("User not found.", "danger")
    return redirect(url_for('settings_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not AppUser.query.filter_by(username='admin').first():
            new_admin = AppUser(username='admin', email='admin@panhome.com', mobile='N/A', password='admin123', role='admin')
            db.session.add(new_admin)
            db.session.commit()
    app.run(debug=True)