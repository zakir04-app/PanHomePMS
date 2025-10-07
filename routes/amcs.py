import os
import io
import pandas as pd
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from routes import amcs_bp
from models import db, AMCsService, AMCsSupplier # Assuming AMCsSupplier is now imported from models

# --- Helper Functions ---
def get_amcs_suppliers():
    """Fetches list of all suppliers for dropdowns."""
    return AMCsSupplier.query.order_by(AMCsSupplier.name).all()

# --- AMCs Dashboard and Setup Routes ---
@amcs_bp.route('/', methods=['GET', 'POST'])
@login_required
def amcs_dashboard():
    if request.method == 'POST':
        # ENFORCEMENT: Requires AMCS_EDIT permission for upload
        if not current_user.can_access_feature('AMCS_EDIT'):
            flash("Permission denied: You cannot upload AMCs data.", 'danger')
            return redirect(url_for('amcs.amcs_dashboard'))
            
        # --- File Upload Logic ---
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
                try:
                    read_method = pd.read_excel if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv
                    df = read_method(file, dtype=str).fillna('N/A')
                    for _, row in df.iterrows():
                        # Use new date field names
                        inspection_date = pd.to_datetime(row.get('Inspection Date', row.get('Start Date'))).strftime('%Y-%m-%d')
                        expiry_date = pd.to_datetime(row.get('Expiry Date', row.get('End Date'))).strftime('%Y-%m-%d')
                        
                        start_dt = datetime.strptime(inspection_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
                        duration = (end_dt - start_dt).days

                        new_amc = AMCsService(
                            # service_id removed
                            date=row.get('Date', datetime.now().strftime('%Y-%m-%d')),
                            type=row.get('Type', 'N/A'),
                            supplier_name=row.get('Supplier Name', 'N/A'),
                            inspection_date=inspection_date, # New field
                            expiry_date=expiry_date,         # New field
                            remarks=row.get('Remarks', 'N/A'),
                            duration=duration
                        )
                        db.session.add(new_amc)
                        
                        # Auto-add supplier if not found
                        supplier_name = row.get('Supplier Name', 'N/A')
                        if supplier_name != 'N/A' and not AMCsSupplier.query.filter_by(name=supplier_name).first():
                             db.session.add(AMCsSupplier(name=supplier_name, contact='N/A'))


                    db.session.commit()
                    flash('AMCs services uploaded successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'File upload failed: {e}', 'danger')
            else:
                flash('Invalid file format. Please upload an Excel or CSV file.', 'danger')
        return redirect(url_for('amcs.amcs_dashboard'))

    # --- GET Request Logic ---
    amcs_list = AMCsService.query.all()
    try:
        for amc in amcs_list:
            end_date = datetime.strptime(amc.expiry_date, '%Y-%m-%d')
            remaining = end_date - datetime.now()
            amc.remaining_days = max(0, remaining.days)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error calculating remaining days: {e}', 'danger')
        
    return render_template('amcs_dashboard.html', amcs_list=amcs_list)

@amcs_bp.route('/download_amcs_report')
@login_required
def download_amcs_report():
    amcs = AMCsService.query.order_by(AMCsService.date.desc()).all()
    data = [{
        # service_id removed
        'Date': a.date,
        'Type': a.type,
        'Supplier Name': a.supplier_name,
        'Inspection Date': a.inspection_date, # New field
        'Expiry Date': a.expiry_date,         # New field
        'Duration (Days)': a.duration,
        'Remaining Days': a.remaining_days,
        'Remarks': a.remarks
    } for a in amcs]
    df = pd.DataFrame(data)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name='AMCs Services')
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name='amcs_services_report.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@amcs_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_amcs():
    # ENFORCEMENT: Requires AMCS_EDIT permission
    if not current_user.can_access_feature('AMCS_EDIT'):
        flash("Permission denied: You cannot add new AMCs.", 'danger')
        return redirect(url_for('amcs.amcs_dashboard'))
        
    if request.method == 'POST':
        file = request.files.get('attached_file')
        filename = None
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        try:
            inspection_date_str = request.form.get('inspection_date') # New field
            expiry_date_str = request.form.get('expiry_date')         # New field
            inspection_date = datetime.strptime(inspection_date_str, '%Y-%m-%d')
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            
            new_amc = AMCsService(
                # service_id removed
                date=request.form.get('date'),
                type=request.form.get('type'), 
                supplier_name=request.form.get('supplier_name'),
                inspection_date=inspection_date_str, 
                expiry_date=expiry_date_str,
                remarks=request.form.get('remarks'), 
                duration=(expiry_date - inspection_date).days,
                attached_file=filename
            )
            db.session.add(new_amc)
            db.session.commit()
            flash("AMC service added successfully!", "success")
            return redirect(url_for('amcs.amcs_dashboard'))
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding AMC service: {e}", "danger")
            
    return render_template('add_amcs.html', today=datetime.now().strftime('%Y-%m-%d'), suppliers=get_amcs_suppliers())

@amcs_bp.route('/edit/<int:amc_id>', methods=['GET', 'POST'])
@login_required
def edit_amcs(amc_id):
    # ENFORCEMENT: Requires AMCS_EDIT permission
    if not current_user.can_access_feature('AMCS_EDIT'):
        flash("Permission denied: You cannot edit AMCs.", 'danger')
        return redirect(url_for('amcs.amcs_dashboard'))
        
    amc = db.session.get(AMCsService, amc_id)
    if not amc: 
        flash("AMC service not found.", "danger")
        return redirect(url_for('amcs.amcs_dashboard'))
        
    if request.method == 'POST':
        try:
            # service_id removed
            amc.date = request.form.get('date')
            amc.type = request.form.get('type')
            amc.supplier_name = request.form.get('supplier_name')
            amc.inspection_date = request.form.get('inspection_date') # New field
            amc.expiry_date = request.form.get('expiry_date')         # New field
            amc.remarks = request.form.get('remarks')
            
            file = request.files.get('attached_file')
            if file and file.filename:
                filename = file.filename
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                amc.attached_file = filename
            
            # Recalculate duration
            start = datetime.strptime(amc.inspection_date, '%Y-%m-%d')
            end = datetime.strptime(amc.expiry_date, '%Y-%m-%d')
            amc.duration = (end - start).days
            
            db.session.commit()
            flash("AMC service updated successfully!", "success")
            return redirect(url_for('amcs.amcs_dashboard'))
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating AMC service: {e}", "danger")
            
    return render_template('edit_amcs.html', amc=amc, suppliers=get_amcs_suppliers())

@amcs_bp.route('/view/<int:amc_id>')
@login_required
def view_amcs(amc_id):
    amc = db.session.get(AMCsService, amc_id)
    if not amc: 
        flash("AMC service not found.", "danger")
        return redirect(url_for('amcs.amcs_dashboard'))
        
    return render_template('view_amcs.html', amc=amc)

# --- Supplier Management Routes ---
@amcs_bp.route('/suppliers', methods=['GET', 'POST'])
@login_required
def manage_suppliers():
    if not current_user.is_admin():
        flash("Permission denied: Only administrators can manage suppliers.", 'danger')
        return redirect(url_for('amcs.amcs_dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact', 'N/A')
        
        if AMCsSupplier.query.filter_by(name=name).first():
            flash(f"Supplier '{name}' already exists.", 'warning')
        else:
            new_supplier = AMCsSupplier(name=name, contact=contact)
            db.session.add(new_supplier)
            db.session.commit()
            flash(f"Supplier '{name}' added successfully.", 'success')
            
        return redirect(url_for('amcs.manage_suppliers'))

    suppliers = get_amcs_suppliers()
    return render_template('manage_suppliers.html', suppliers=suppliers)

@amcs_bp.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
def delete_supplier(supplier_id):
    if not current_user.is_admin():
        flash("Permission denied.", 'danger')
        return redirect(url_for('amcs.amcs_dashboard'))
        
    supplier = db.session.get(AMCsSupplier, supplier_id)
    
    if not supplier:
        flash("Supplier not found.", 'danger')
        return redirect(url_for('amcs.manage_suppliers'))
        
    # Check if supplier is currently used in any AMCs service
    if AMCsService.query.filter_by(supplier_name=supplier.name).first():
        flash(f"Cannot delete supplier '{supplier.name}' as they are associated with existing AMCs records.", 'danger')
    else:
        db.session.delete(supplier)
        db.session.commit()
        flash(f"Supplier '{supplier.name}' deleted successfully.", 'success')
        
    return redirect(url_for('amcs.manage_suppliers'))