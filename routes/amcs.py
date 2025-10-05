import os
import io
import pandas as pd
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from routes import amcs_bp
from models import db, AMCsService

# --- AMCs Routes ---
@amcs_bp.route('/', methods=['GET', 'POST'])
@login_required
def amcs_dashboard():
    if request.method == 'POST':
        # ENFORCEMENT: Requires AMCS_EDIT permission
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
                        # Convert date strings to proper format
                        start_date = pd.to_datetime(row.get('Start Date')).strftime('%Y-%m-%d')
                        end_date = pd.to_datetime(row.get('End Date')).strftime('%Y-%m-%d')
                        
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        duration = (end_dt - start_dt).days

                        new_amc = AMCsService(
                            service_id=row.get('Service ID', 'N/A'),
                            date=row.get('Date', datetime.now().strftime('%Y-%m-%d')),
                            type=row.get('Type', 'N/A'),
                            supplier_name=row.get('Supplier Name', 'N/A'),
                            start_date=start_date,
                            end_date=end_date,
                            remarks=row.get('Remarks', 'N/A'),
                            duration=duration
                        )
                        db.session.add(new_amc)
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
            end_date = datetime.strptime(amc.end_date, '%Y-%m-%d')
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
        'Service ID': a.service_id,
        'Date': a.date,
        'Type': a.type,
        'Supplier Name': a.supplier_name,
        'Start Date': a.start_date,
        'End Date': a.end_date,
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
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            new_amc = AMCsService(
                service_id=request.form.get('service_id'), 
                date=request.form.get('date'),
                type=request.form.get('type'), 
                supplier_name=request.form.get('supplier_name'),
                start_date=start_date_str, 
                end_date=end_date_str,
                remarks=request.form.get('remarks'), 
                duration=(end_date - start_date).days,
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
            
    return render_template('add_amcs.html', today=datetime.now().strftime('%Y-%m-%d'))

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
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                amc.attached_file = filename
            
            # Recalculate duration
            start = datetime.strptime(amc.start_date, '%Y-%m-%d')
            end = datetime.strptime(amc.end_date, '%Y-%m-%d')
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
            
    return render_template('edit_amcs.html', amc=amc)

@amcs_bp.route('/view/<int:amc_id>')
@login_required
def view_amcs(amc_id):
    amc = db.session.get(AMCsService, amc_id)
    if not amc: 
        flash("AMC service not found.", "danger")
        return redirect(url_for('amcs.amcs_dashboard'))
        
    return render_template('view_amcs.html', amc=amc)