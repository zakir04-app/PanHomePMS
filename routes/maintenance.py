import os
import io
import pandas as pd
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_required, current_user
from routes import maintenance_bp
from models import db, MaintenanceReport

# --- Maintenance Routes ---
@maintenance_bp.route('/', methods=['GET', 'POST'])
@login_required
def maintenance_report():
    if request.method == 'POST':
        # ENFORCEMENT: Requires MAINT_EDIT permission for upload
        if not current_user.can_access_feature('MAINT_EDIT'):
            flash("Permission denied: You cannot upload maintenance reports.", 'danger')
            return redirect(url_for('maintenance.maintenance_report'))
            
        # --- File Upload Logic from the bottom form in maintenance_report.html ---
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and file.filename.endswith(('.xlsx', '.xls', '.csv')):
                try:
                    read_method = pd.read_excel if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv
                    df = read_method(file, dtype=str).fillna('N/A')
                    for _, row in df.iterrows():
                        new_report = MaintenanceReport(
                            block=row.get('Block', 'N/A'),
                            section=row.get('Section', 'N/A'),
                            report_date=row.get('Report Date', datetime.now().strftime('%Y-%m-%d')),
                            details=row.get('Details', 'N/A'),
                            status=row.get('Status', 'Open'),
                            concern=row.get('Concern', 'N/A'),
                            risk=row.get('Risk', 'Low'),
                            remarks=row.get('Remarks', 'N/A')
                        )
                        db.session.add(new_report)
                    db.session.commit()
                    flash('Maintenance reports uploaded successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'File upload failed: {e}', 'danger')
            else:
                flash('Invalid file format. Please upload an Excel or CSV file.', 'danger')
        return redirect(url_for('maintenance.maintenance_report'))

    # --- GET Request Logic: Calculate Summary Statistics ---
    total_reports = MaintenanceReport.query.count()
    total_open = MaintenanceReport.query.filter_by(status='Open').count()
    total_closed = MaintenanceReport.query.filter_by(status='Closed').count()
    
    reports = MaintenanceReport.query.order_by(MaintenanceReport.report_date.desc()).all()
    
    return render_template('maintenance_report.html', 
                           reports=reports,
                           total_reports=total_reports,
                           total_open=total_open,
                           total_closed=total_closed,
                           is_dashboard=True) # Flag to control view

@maintenance_bp.route('/view_list/<string:status_filter>')
@login_required
def view_maintenance_list(status_filter):
    # ENFORCEMENT: All maintenance data is viewable by default (no specific check needed here)
    
    reports_query = MaintenanceReport.query
    
    if status_filter.lower() == 'open':
        reports_query = reports_query.filter_by(status='Open')
        title = "Open Maintenance Issues"
    elif status_filter.lower() == 'closed':
        reports_query = reports_query.filter_by(status='Closed')
        title = "Closed Maintenance Issues"
    else:
        title = "All Maintenance Reports"

    reports = reports_query.order_by(MaintenanceReport.report_date.desc()).all()
    
    return render_template('maintenance_list.html', 
                           reports=reports,
                           title=title,
                           current_filter=status_filter)

@maintenance_bp.route('/download/filtered/<string:status_filter>')
@login_required
def download_filtered_report(status_filter):
    # ENFORCEMENT: Requires explicit Admin permission or a dedicated 'MAINT_VIEW' permission
    if not current_user.is_admin():
         flash("Permission denied: Only administrators can download filtered reports.", 'danger')
         return redirect(url_for('maintenance.maintenance_report'))
         
    reports_query = MaintenanceReport.query
    
    if status_filter.lower() == 'open':
        reports_query = reports_query.filter_by(status='Open')
        filename = 'open_maintenance_reports.xlsx'
    elif status_filter.lower() == 'closed':
        reports_query = reports_query.filter_by(status='Closed')
        filename = 'closed_maintenance_reports.xlsx'
    else:
        filename = 'all_maintenance_reports.xlsx'
    
    reports = reports_query.order_by(MaintenanceReport.report_date.desc()).all()
    
    data = [{
        'Block': r.block,
        'Section': r.section,
        'Report Date': r.report_date,
        'Closed Date': r.closed_date, 
        'Details': r.details,
        'Status': r.status,
        'Concern': r.concern,
        'Risk Level': r.risk,
        'Remarks': r.remarks
    } for r in reports]
    df = pd.DataFrame(data)
    
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name=status_filter.title() + ' Reports')
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@maintenance_bp.route('/download/report')
@login_required
def download_maintenance_report():
    # This route downloads ALL reports (reused for convenience)
    reports = MaintenanceReport.query.order_by(MaintenanceReport.report_date.desc()).all()
    data = [{
        'Block': r.block,
        'Section': r.section,
        'Report Date': r.report_date,
        'Closed Date': r.closed_date, 
        'Details': r.details,
        'Status': r.status,
        'Concern': r.concern,
        'Risk Level': r.risk,
        'Remarks': r.remarks
    } for r in reports]
    df = pd.DataFrame(data)
    
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name='Maintenance Reports')
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name='maintenance_report.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@maintenance_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_maintenance():
    # ENFORCEMENT: Requires MAINT_EDIT permission
    if not current_user.can_access_feature('MAINT_EDIT'):
        flash("Permission denied: You cannot add maintenance reports.", 'danger')
        return redirect(url_for('maintenance.maintenance_report'))
        
    if request.method == 'POST':
        file = request.files.get('attached_file')
        filename = None
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        status = request.form.get('status')
        closed_date = datetime.now().strftime('%Y-%m-%d') if status == 'Closed' else None

        new_report = MaintenanceReport(
            block=request.form.get('block'), 
            section=request.form.get('section'),
            report_date=request.form.get('report_date'), 
            details=request.form.get('details'),
            status=status, 
            concern=request.form.get('concern'),
            risk=request.form.get('risk'), 
            remarks=request.form.get('remarks'),
            closed_date=closed_date,
            attached_file=filename
        )
        db.session.add(new_report)
        db.session.commit()
        flash("Maintenance report added successfully!", "success")
        return redirect(url_for('maintenance.maintenance_report'))
    
    return render_template('add_maintenance.html', today=datetime.now().strftime('%Y-%m-%d'))

@maintenance_bp.route('/edit/<int:report_id>', methods=['GET', 'POST'])
@login_required
def edit_maintenance(report_id):
    # ENFORCEMENT: Requires MAINT_EDIT permission
    if not current_user.can_access_feature('MAINT_EDIT'):
        flash("Permission denied: You cannot edit maintenance reports.", 'danger')
        return redirect(url_for('maintenance.maintenance_report'))
        
    report = db.session.get(MaintenanceReport, report_id)
    if not report: 
        flash("Report not found.", "danger")
        return redirect(url_for('maintenance.maintenance_report'))
        
    if request.method == 'POST':
        # --- Date and Status Logic ---
        new_status = request.form.get('status')
        submitted_closed_date = request.form.get('closed_date')

        if new_status == 'Closed':
            if submitted_closed_date:
                report.closed_date = submitted_closed_date
            elif not report.closed_date:
                report.closed_date = datetime.now().strftime('%Y-%m-%d')
        else:
            report.closed_date = None

        # --- Update other fields ---
        report.block = request.form.get('block')
        report.section = request.form.get('section')
        report.report_date = request.form.get('report_date')
        report.details = request.form.get('details')
        report.status = new_status
        report.concern = request.form.get('concern')
        report.risk = request.form.get('risk')
        report.remarks = request.form.get('remarks')
        
        file = request.files.get('attached_file')
        if file and file.filename:
            filename = file.filename
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            report.attached_file = filename
            
        db.session.commit()
        flash("Maintenance report updated successfully!", "success")
        return redirect(url_for('maintenance.maintenance_report'))
        
    return render_template('edit_maintenance.html', report=report)

@maintenance_bp.route('/view/<int:report_id>')
@login_required
def view_maintenance_report(report_id):
    report = db.session.get(MaintenanceReport, report_id)
    if not report: 
        flash("Report not found.", "danger")
        return redirect(url_for('maintenance.maintenance_report'))
        
    return render_template('view_maintenance_report.html', report=report)