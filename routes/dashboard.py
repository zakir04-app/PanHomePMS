import pandas as pd
import io
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from sqlalchemy import or_, not_
from routes import dashboard_bp
from models import db, Employee
from sqlalchemy import func

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    status_filter = request.args.get('status')
    location_filter = request.args.get('location')
    query = request.args.get('query', '').strip()
    
    occupying_statuses = ['Active', 'Vacation', 'On Leave']
    
    # 1. Summary Calculations
    total_employees = Employee.query.filter(
        Employee.status.in_(occupying_statuses), 
        Employee.room.isnot(None)
    ).count()
    
    total_vacant_beds = Employee.query.filter_by(status='Vacant').count()
    total_on_vacation = Employee.query.filter_by(status='Vacation').count()
    total_resigned_terminated = Employee.query.filter(or_(Employee.status == 'Resigned', Employee.status == 'Terminated')).count()
    
    employees_without_room = Employee.query.filter(
        Employee.status == 'Check-in', 
        Employee.room.is_(None)
    ).count()
    
    location_summary = db.session.query(Employee.location, func.count(Employee.id)).filter(
        Employee.status.in_(occupying_statuses),
        Employee.room.isnot(None)
    ).group_by(Employee.location).all()
    
    # 2. Employee Table Query (Base)
    employees_query = Employee.query
    
    employees_query = employees_query.filter(
        Employee.status.notin_(['Ex-Employee', 'Shifted-out'])
    )

    # 3. Filtering and Searching
    if query:
        search_filter = or_(Employee.emp_id.contains(query), Employee.name.contains(query))
        employees_query = employees_query.filter(search_filter)
    
    if status_filter:
        if status_filter == 'Resigned_Or_Terminated':
            employees_query = employees_query.filter(or_(Employee.status == 'Resigned', Employee.status == 'Terminated'))
        elif status_filter == 'Check-in':
            employees_query = Employee.query.filter_by(status='Check-in', room=None)
        else:
            employees_query = employees_query.filter_by(status=status_filter)

    if location_filter:
        employees_query = employees_query.filter_by(location=location_filter)
        
    # 4. Sorting Logic
    sort_order = { 
        'Vacant': -1, 'Active': 0, 'On Leave': 1, 'Vacation': 2, 'Check-in': 3,
        'Resigned': 4, 'Terminated': 5, 'Shifted-out': 98, 'Ex-Employee': 99 
    }
    employees = sorted(
        employees_query.all(),
        key=lambda item: (sort_order.get(item.status, 100), item.room or '', item.name or '')
    )

    return render_template('dashboard.html', 
                           total_employees=total_employees, 
                           total_vacant_beds=total_vacant_beds, 
                           total_on_vacation=total_on_vacation, 
                           total_resigned_terminated=total_resigned_terminated,
                           employees_without_room=employees_without_room,
                           employees=employees, 
                           query=query, 
                           location_summary=location_summary)


@dashboard_bp.route('/download/employees_without_room')
@login_required
def download_employees_without_room():
    """Download a list of employees currently waiting for a room (Status: Check-in, Room: None)."""
    
    employees_query = Employee.query.filter_by(status='Check-in', room=None)
    
    employees_df = pd.read_sql(employees_query.statement, db.engine, columns=[
        'emp_id', 'name', 'designation', 'nationality', 'mobile_number', 'food_variety', 'meal_time', 'remarks'
    ])
    
    buffer = io.BytesIO()
    employees_df.to_excel(buffer, index=False, sheet_name='Employees Awaiting Check-in')
    buffer.seek(0)
    
    return send_file(buffer, as_attachment=True, download_name='employees_awaiting_checkin.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@dashboard_bp.route('/view/employees_without_room')
@login_required
def view_employees_without_room():
    """Displays only employees who are waiting for a room assignment."""
    employees = Employee.query.filter_by(status='Check-in', room=None).all()
    
    return render_template('dashboard.html', 
                           employees=employees,
                           query='',
                           total_employees=0, total_vacant_beds=0, 
                           total_on_vacation=0, total_resigned_terminated=0,
                           employees_without_room=len(employees),
                           location_summary=[])