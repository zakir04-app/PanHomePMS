import os
import io
import pandas as pd
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from routes import staff_mgmt_bp
from models import db, Employee, Camp, AppUser 
from config import Config

# Define required column names
REQUIRED_COLUMNS = ['ACCOMMODATION_NAME', 'ROOM', 'EMP_ID', 'STATUS', 'NAME', 'LOCATION']

# --- Helper Functions ---
def get_vacant_beds_list():
    """Fetches list of vacant beds for assignment dropdowns."""
    vacant_beds_query = Employee.query.filter_by(status='Vacant').order_by(Employee.accommodation_name, Employee.room).all()
    # Ensure the list contains all details needed by the JavaScript
    return [{'id': bed.id, 'accommodation_name': bed.accommodation_name, 'room': bed.room, 'emp_id': bed.emp_id} for bed in vacant_beds_query]

def get_locations_list():
    """Fetches list of general Locations from the Camp table."""
    locations_query = db.session.query(Camp.location).filter(Camp.location.isnot(None)).distinct().order_by(Camp.location).all()
    return [loc[0] for loc in locations_query if loc[0]]

def get_accommodations_list():
    """Fetches unique accommodation names from the Employee table."""
    accommodations_query = db.session.query(Employee.accommodation_name).filter(
        Employee.accommodation_name.isnot(None),
        Employee.accommodation_name != 'N/A' # Exclude dummy N/A entries
    ).distinct().order_by(Employee.accommodation_name).all()
    # Returns a simple list of strings
    return [acc[0] for acc in accommodations_query]


# --- Staff Management Routes ---
@staff_mgmt_bp.route('/add_staff', methods=['GET', 'POST'])
@login_required
def add_staff():
    if request.method == 'POST':
        # --- 1. Excel Upload Logic (omitted for brevity) ---
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
                try:
                    read_method = pd.read_excel if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv
                    df = read_method(file, dtype=str) 
                    
                    df.columns = [str(col).strip().upper().replace(' ', '_').replace('#', 'NUMBER') for col in df.columns]
                    df.fillna('N/A', inplace=True)
                    
                    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
                    if missing_cols:
                        raise KeyError(f"Missing required columns: {', '.join(missing_cols)}")
                    
                    accommodations_in_file = df['ACCOMMODATION_NAME'].unique().tolist()
                    if accommodations_in_file:
                        Employee.query.filter(Employee.accommodation_name.in_(accommodations_in_file)).delete(synchronize_session=False)
                    
                    processed_emp_ids = set()
                    duplicates_found = []
                    vacant_counters = {}

                    for _, row in df.iterrows():
                        status = row.get('STATUS', 'N/A')
                        emp_id = str(row.get('EMP_ID', 'N/A'))
                        accommodation_name = row.get('ACCOMMODATION_NAME', 'N/A')
                        room_number = str(row.get('ROOM', 'N/A'))

                        if accommodation_name == 'N/A' or room_number == 'N/A': continue
                        if accommodation_name not in accommodations_in_file: continue
                        
                        if status.lower() != 'vacant' and emp_id != 'N/A' and emp_id:
                            if emp_id in processed_emp_ids:
                                duplicates_found.append(emp_id)
                                continue 
                            processed_emp_ids.add(emp_id)
                        
                        existing_camp = Camp.query.filter_by(name=accommodation_name).first()
                        if not existing_camp:
                            new_camp = Camp(name=accommodation_name, location=row.get('LOCATION', 'N/A')) 
                            db.session.add(new_camp)
                        
                        if status.lower() == 'vacant':
                            vacant_counters.setdefault(room_number, 0)
                            vacant_counters[room_number] += 1
                            emp_id = f"{room_number}-Vacant-{vacant_counters[room_number]}"
                            
                        bed = Employee(
                            accommodation_name=accommodation_name, room=room_number,
                            status=status, emp_id=emp_id, name=row.get('NAME', '-'),
                            designation=row.get('DESIGNATION', '-'), nationality=row.get('NATIONALITY', '-'),
                            mobile_number=str(row.get('MOBILE_NUMBER', '-')), food_variety=row.get('FOOD_VARIETY', '-'),
                            meal_time=row.get('MEAL_TIME', '-'), location=row.get('LOCATION', 'N/A'),
                            remarks=row.get('REMARKS', '')
                        )
                        db.session.add(bed)

                    db.session.commit()
                    
                    if duplicates_found:
                        flash(f"File uploaded, but skipped duplicate EMP IDs: {', '.join(set(duplicates_found))}", "warning")
                    else:
                        flash('File uploaded and data synchronized successfully!', 'success')

                except KeyError as e:
                    db.session.rollback()
                    flash(f"Upload failed. A required column is missing from your file: {e}. Please check the Excel template.", "danger")
                except Exception as e:
                    db.session.rollback()
                    flash(f'File upload failed due to a processing error: {e}', 'danger')
            else:
                flash('Invalid file format. Please upload an Excel or CSV file.', 'danger')
        
        # --- 2. Manual Assignment/Check-in Logic (omitted for brevity) ---
        else:
            try:
                emp_id_to_assign = request.form.get('emp_id')
                vacant_bed_id = request.form.get('vacant_bed_id')
                
                if request.form.get('action_type') == 'check_in':
                    new_employee = Employee(
                        accommodation_name=None, room=None,
                        emp_id=emp_id_to_assign, name=request.form.get('name'),
                        designation=request.form.get('designation'), nationality=request.form.get('nationality'),
                        mobile_number=request.form.get('mobile_number'), food_variety=request.form.get('food_variety'),
                        meal_time=request.form.get('meal_time'), location=request.form.get('location'),
                        remarks=request.form.get('remarks'), status='Check-in'
                    )
                    db.session.add(new_employee)
                    flash('Staff data entered successfully and employee is awaiting room assignment!', 'success')
                
                else:
                    vacant_bed = db.session.get(Employee, int(vacant_bed_id))
                    
                    if not vacant_bed or vacant_bed.status != 'Vacant':
                        flash('Selected bed is not available or not vacant.', 'danger')
                        return redirect(url_for('staff_mgmt.add_staff'))

                    vacant_bed.emp_id = emp_id_to_assign
                    vacant_bed.name = request.form.get('name')
                    vacant_bed.designation = request.form.get('designation')
                    vacant_bed.nationality = request.form.get('nationality')
                    vacant_bed.mobile_number = request.form.get('mobile_number')
                    vacant_bed.status = 'Active'
                    vacant_bed.location = request.form.get('location')
                    vacant_bed.food_variety = request.form.get('food_variety')
                    vacant_bed.meal_time = request.form.get('meal_time')
                    vacant_bed.remarks = request.form.get('remarks')
                    
                    flash('Employee assigned to bed successfully!', 'success')
                
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f'Error assigning employee: {e}', 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
    
    # --- GET Request Logic ---
    return render_template('add_staff.html', 
                           accommodations=get_accommodations_list(), # CORRECT: List of strings
                           vacant_beds=get_vacant_beds_list(),
                           locations=get_locations_list(),
                           nationalities=Config.NATIONALITIES,
                           food_varieties=Config.FOOD_VARIETIES, 
                           meal_times=Config.MEAL_TIMES)


@staff_mgmt_bp.route('/edit_employee/<string:emp_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first_or_404()
    
    # ENFORCEMENT: Check permission to edit this employee's location
    location_to_check = employee.location or employee.accommodation_name or '-'
    
    if not current_user.can_edit_location(location_to_check):
        flash(f"Permission denied: You cannot edit staff in location '{location_to_check}'.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))

    if request.method == 'POST':
        try:
            # =================================================================
            # 1. CHECKOUT / SHIFT-OUT LOGIC 
            # =================================================================
            if 'checkout_btn' in request.form or 'shiftout_btn' in request.form:
                original_room = employee.room
                original_acc = employee.accommodation_name
                original_loc = employee.location
                
                is_vacating_room = original_room is not None

                if 'checkout_btn' in request.form:
                    employee.status = 'Ex-Employee'
                    employee.check_out_date = datetime.now().strftime('%Y-%m-%d')
                    msg = 'Employee successfully Checked Out (Ex-Employee).'
                else: 
                    employee.status = 'Check-in' 
                    employee.shift_out_date = datetime.now().strftime('%Y-%m-%d')
                    msg = 'Employee successfully Shifted Out and placed in Awaiting Room status.'
                
                if is_vacating_room:
                    employee.room = None
                    employee.accommodation_name = None
                    employee.location = None
                    
                    vacant_count = Employee.query.filter(Employee.room == original_room, Employee.status == 'Vacant').count()
                    new_vacant_id = f"{original_room}-Vacant-{vacant_count + 1}"
                    
                    vacant_bed = Employee(
                        emp_id=new_vacant_id, status='Vacant', name='-',
                        accommodation_name=original_acc, room=original_room,
                        location=original_loc, designation='-', nationality='-',
                        mobile_number='-', food_variety='-', meal_time='-', remarks='Bedspace'
                    )
                    db.session.add(vacant_bed)
                
                db.session.commit()
                flash(msg, 'success')
                return redirect(url_for('dashboard_bp.dashboard')) 
            # =================================================================
            
            # =================================================================
            # 2. BED SHIFT LOGIC 
            # =================================================================
            elif 'bed_shift_action' in request.form: 
                new_vacant_bed_id = request.form.get('vacant_bed_id')
                
                if not new_vacant_bed_id:
                    flash('Please select a new vacant bed for the shift.', 'danger')
                    return redirect(url_for('staff_mgmt.edit_employee', emp_id=emp_id))

                new_bed = db.session.get(Employee, int(new_vacant_bed_id))
                if new_bed and new_bed.status == 'Vacant':
                    
                    old_vacant_id = f"{employee.room}-Vacant-{Employee.query.filter_by(room=employee.room, status='Vacant').count() + 1}"
                    old_bed_as_vacant = Employee(
                        emp_id=old_vacant_id, status='Vacant', name='-',
                        accommodation_name=employee.accommodation_name, room=employee.room,
                        location=employee.location, designation='-', nationality='-',
                        mobile_number='-', food_variety='-', meal_time='-', remarks='Bedspace'
                    )
                    db.session.add(old_bed_as_vacant)
                    
                    employee.accommodation_name = new_bed.accommodation_name
                    employee.room = new_bed.room
                    employee.location = new_bed.location
                    
                    db.session.delete(new_bed) 
                    
                    db.session.commit()
                    flash('Employee successfully shifted to the new bed!', 'success')
                    return redirect(url_for('dashboard_bp.dashboard'))
                else:
                    flash('Selected bed is not available or not vacant.', 'danger')
                    return redirect(url_for('staff_mgmt.edit_employee', emp_id=emp_id))
            
            # =================================================================
            # 3. CHECK-IN LOGIC 
            # =================================================================
            elif 'checkin_btn' in request.form:
                new_vacant_bed_id = request.form.get('vacant_bed_id')
                if new_vacant_bed_id:
                    new_bed = db.session.get(Employee, int(new_vacant_bed_id))
                    if new_bed and new_bed.status == 'Vacant':
                        
                        db.session.delete(employee)
                        db.session.flush() 
                        
                        new_bed.emp_id = employee.emp_id
                        new_bed.name = employee.name
                        new_bed.designation = employee.designation
                        new_bed.nationality = employee.nationality
                        new_bed.mobile_number = employee.mobile_number
                        new_bed.status = 'Active' 
                        new_bed.location = employee.location
                        new_bed.food_variety = employee.food_variety
                        new_bed.meal_time = employee.meal_time
                        new_bed.remarks = employee.remarks
                        
                        db.session.commit()
                        flash('Employee successfully Checked-in and assigned to a bed!', 'success')
                        return redirect(url_for('dashboard_bp.dashboard'))
                    else:
                        flash('Selected bed is not available or not vacant.', 'danger')
                        return redirect(url_for('staff_mgmt.edit_employee', emp_id=emp_id))
                else:
                    flash('Please select a vacant bed for check-in.', 'danger')
                    return redirect(url_for('staff_mgmt.edit_employee', emp_id=emp_id))
            
            # =================================================================
            # 4. REGULAR UPDATE LOGIC (Generic form submission)
            # =================================================================
            else:
                employee.name = request.form['name']
                employee.designation = request.form['designation']
                employee.nationality = request.form['nationality']
                employee.mobile_number = request.form['mobile_number']
                employee.status = request.form['status']
                employee.location = request.form['location']
                employee.food_variety = request.form['food_variety']
                employee.meal_time = request.form['meal_time']
                employee.remarks = request.form['remarks']
            
            db.session.commit()
            flash('Data updated successfully!', 'success')
            return redirect(url_for('dashboard_bp.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating data: {e}', 'danger') 
            return redirect(url_for('staff_mgmt.edit_employee', emp_id=emp_id))

    # --- GET Request Logic ---
    return render_template('edit_employee.html', 
        employee=employee, is_vacant_record=employee.status == 'Vacant', is_awaiting_checkin=employee.status == 'Check-in' and employee.room is None,
        nationalities=Config.NATIONALITIES, food_varieties=Config.FOOD_VARIETIES,
        meal_times=Config.MEAL_TIMES, statuses=Config.EMPLOYEE_STATUSES,
        accommodations=get_accommodations_list(), 
        vacant_beds=get_vacant_beds_list(),
        locations=get_locations_list())

@staff_mgmt_bp.route('/get_employee_details/<string:emp_id>')
@login_required
def get_employee_details(emp_id):
    employee = Employee.query.filter_by(emp_id=emp_id).first()
    if employee:
        if employee.status == 'Check-in' and employee.room is None:
             return jsonify({
                'name': employee.name, 
                'designation': employee.designation, 
                'location': employee.location, 
                'mobile_number': employee.mobile_number,
                'status': 'Check-in'
            })
        
        return jsonify({
            'name': employee.name, 'room': employee.room, 'designation': employee.designation, 
            'location': employee.location, 'accommodation_name': employee.accommodation_name,
            'mobile_number': employee.mobile_number,
            'status': employee.status
        })
    return jsonify({'error': 'Employee not found'}), 404


# --- Location Management Routes ---
@staff_mgmt_bp.route('/locations', methods=['GET', 'POST'])
@login_required
def locations():
    if not current_user.is_admin():
        flash("You do not have permission to access location management.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
        
    if request.method == 'POST':
        new_location_name = request.form.get('location_name', '').strip()
        if new_location_name:
            existing = Camp.query.filter(func.lower(Camp.location) == func.lower(new_location_name)).first()
            if existing:
                flash('This location already exists.', 'warning')
            else:
                placeholder_name = f"Camp at {new_location_name}"
                counter = 1
                while Camp.query.filter_by(name=placeholder_name).first():
                    placeholder_name = f"Camp at {new_location_name} ({counter})"
                    counter += 1
                
                new_camp = Camp(name=placeholder_name, location=new_location_name)
                db.session.add(new_camp)
                db.session.commit()
                flash(f'Location "{new_location_name}" added successfully.', 'success')
        else:
            flash('Location name cannot be empty.', 'danger')
        return redirect(url_for('staff_mgmt.locations'))

    camps_with_locations = Camp.query.filter(Camp.location.isnot(None)).order_by(Camp.location).all()
    return render_template('locations.html', camps=camps_with_locations)

@staff_mgmt_bp.route('/locations/edit/<int:camp_id>', methods=['GET', 'POST'])
@login_required
def edit_location(camp_id):
    if not current_user.is_admin():
        flash("You do not have permission to access location management.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))

    camp_to_edit = db.session.get(Camp, camp_id)
    if not camp_to_edit:
        flash('Location not found.', 'danger')
        return redirect(url_for('staff_mgmt.locations'))
    
    old_location = camp_to_edit.location

    if request.method == 'POST':
        new_location = request.form.get('location_name', '').strip()
        if not new_location:
            flash('Location name cannot be empty.', 'danger')
            return redirect(url_for('staff_mgmt.edit_location', camp_id=camp_id))

        existing = Camp.query.filter(func.lower(Camp.location) == func.lower(new_location)).first()
        if existing and existing.id != camp_id:
            flash(f'Location "{new_location}" already exists.', 'warning')
        else:
            Employee.query.filter_by(location=old_location).update({'location': new_location})
            camp_to_edit.location = new_location
            db.session.commit()
            flash('Location updated successfully.', 'success')
            return redirect(url_for('staff_mgmt.locations'))

    return render_template('edit_location.html', camp=camp_to_edit)

@staff_mgmt_bp.route('/locations/delete/<int:camp_id>', methods=['POST'])
@login_required
def delete_location(camp_id):
    if not current_user.is_admin():
        flash("You do not have permission to access location management.", 'danger')
        return redirect(url_for('dashboard_bp.dashboard'))
        
    camp_to_delete = db.session.get(Camp, camp_id)
    if not camp_to_delete:
        flash('Location not found.', 'danger')
        return redirect(url_for('staff_mgmt.locations'))

    employees_at_location = Employee.query.filter_by(location=camp_to_delete.location).count()
    if employees_at_location > 0:
        flash(f'Cannot delete "{camp_to_delete.location}" because it is still assigned to {employees_at_location} employee(s).', 'danger')
    else:
        db.session.delete(camp_to_delete)
        db.session.commit()
        flash(f'Location "{camp_to_delete.location}" has been deleted.', 'success')
    
    return redirect(url_for('staff_mgmt.locations'))

@staff_mgmt_bp.route('/data', methods=['GET', 'POST'])
@login_required
def data_management():
    if request.method == 'POST':
        # --- Download Logic ---
        download_type = request.form.get('download_type')
        filter_value = request.form.get('filter_value')
        employees_query = Employee.query
        
        if download_type and filter_value and filter_value != 'all':
            if download_type == 'location':
                employees_query = employees_query.filter(Employee.location == filter_value)
            elif download_type == 'status':
                employees_query = employees_query.filter(Employee.status == filter_value)
            elif download_type == 'accommodation':
                employees_query = employees_query.filter(Employee.accommodation_name == filter_value)
            elif download_type == 'nationality':
                employees_query = employees_query.filter(Employee.nationality == filter_value)
        
        employees_df = pd.read_sql(employees_query.statement, db.engine)
        buffer = io.BytesIO()
        employees_df.to_excel(buffer, index=False)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name='employee_data.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # --- Summary Data for GET request ---
    active_statuses = ['Active', 'Vacation', 'On Leave', 'Resigned', 'Terminated']
    
    locations_query = db.session.query(Employee.location).filter(Employee.location.isnot(None)).distinct().order_by(Employee.location).all()
    statuses_query = db.session.query(Employee.status).filter(Employee.status.isnot(None)).distinct().order_by(Employee.status).all()
    accommodations_query = Camp.query.order_by(Camp.name).all()
    nationalities_query = db.session.query(Employee.nationality).filter(Employee.nationality.isnot(None)).distinct().order_by(Employee.nationality).all()

    # Format data for Jinja/JavaScript consumption
    accommodations_list = [{'name': camp.name} for camp in accommodations_query]
    locations_list = [loc[0] for loc in locations_query if loc[0]]
    statuses_list = [s[0] for s in statuses_query if s[0]]
    nationalities_list = [nat[0] for nat in nationalities_query if nat[0]]

    designation_summary = db.session.query(Employee.designation, func.count(Employee.id)).filter(Employee.status.in_(active_statuses)).group_by(Employee.designation).order_by(func.count(Employee.id).desc()).all()
    nationality_summary = db.session.query(Employee.nationality, func.count(Employee.id)).filter(Employee.status.in_(active_statuses)).group_by(Employee.nationality).order_by(func.count(Employee.id).desc()).all()

    return render_template('data.html', 
                           locations=locations_list,
                           statuses=statuses_list,
                           accommodations=accommodations_list,
                           nationalities=nationalities_list,
                           designation_summary=designation_summary,
                           nationality_summary=nationality_summary)