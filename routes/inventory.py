import os
import io
import pandas as pd
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from routes import inventory_bp
from models import db, InventoryItem, InventoryTransaction, Employee 

# --- Inventory Routes ---
@inventory_bp.route('/')
@login_required
def inventory_dashboard():
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    total_received_qty = db.session.query(func.sum(InventoryTransaction.quantity)).filter_by(type='Incoming').scalar() or 0
    total_distributed_qty = db.session.query(func.sum(InventoryTransaction.quantity)).filter_by(type='Outgoing').scalar() or 0
    current_stock = db.session.query(func.sum(InventoryItem.quantity)).scalar() or 0
    return render_template('inventory_dashboard.html', 
                           items=items, 
                           total_received_qty=total_received_qty, 
                           total_distributed_qty=total_distributed_qty, 
                           current_stock=current_stock)

@inventory_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_inventory_item():
    # ENFORCEMENT: Requires INV_EDIT permission
    if not current_user.can_access_feature('INV_EDIT'):
        flash("Permission denied: You cannot modify inventory settings.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
        
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
            return redirect(url_for('inventory.inventory_dashboard'))
    return render_template('add_inventory.html')

@inventory_bp.route('/incoming', methods=['GET', 'POST'])
@login_required
def incoming_inventory():
    # ENFORCEMENT: Requires INV_EDIT permission
    if not current_user.can_access_feature('INV_EDIT'):
        flash("Permission denied: You cannot record incoming stock.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
        
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        try:
            quantity = int(request.form.get('quantity'))
        except (ValueError, TypeError):
            flash("Invalid quantity entered.", "danger")
            return redirect(url_for('inventory.incoming_inventory'))
            
        item = db.session.get(InventoryItem, int(item_id))
        if item:
            item.quantity += quantity
            file = request.files.get('attached_file')
            filename = None
            if file and file.filename:
                filename = file.filename
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename)) 
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
            return redirect(url_for('inventory.inventory_dashboard'))
        else:
            flash("Item not found.", "danger")
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template('incoming_inventory.html', items=items, today=datetime.now().strftime('%Y-%m-%d'))

@inventory_bp.route('/outgoing', methods=['GET', 'POST'])
@login_required
def outgoing_inventory():
    # ENFORCEMENT: Requires INV_EDIT permission
    if not current_user.can_access_feature('INV_EDIT'):
        flash("Permission denied: You cannot record outgoing stock.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

    if request.method == 'POST':
        emp_id = request.form.get('emp_id')
        item_id = request.form.get('item_id')
        try:
            quantity = int(request.form.get('quantity'))
        except (ValueError, TypeError):
            flash("Invalid quantity entered.", "danger")
            return redirect(url_for('inventory.outgoing_inventory'))

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
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename)) 
            new_transaction = InventoryTransaction(
                item_id=item.id, item_name=item.name, type='Outgoing', 
                quantity=quantity, date=datetime.now().strftime('%Y-%m-%d'),
                emp_id=emp_id, room_number=employee.room, file_path=filename
            )
            db.session.add(new_transaction)
            db.session.commit()
            flash(f"{quantity} {item.name}(s) distributed to {employee.name} successfully!", "success")
            return redirect(url_for('inventory.inventory_dashboard'))
    active_employees = Employee.query.filter(Employee.status.in_(['Active', 'Vacation'])).all()
    items = InventoryItem.query.filter(InventoryItem.quantity > 0).order_by(InventoryItem.name).all()
    return render_template('outgoing_inventory.html', today=datetime.now().strftime('%Y-%m-%d'), employees=active_employees, items=items)

@inventory_bp.route('/transaction/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    # ENFORCEMENT: Requires INV_EDIT permission
    if not current_user.can_access_feature('INV_EDIT'):
        flash("Permission denied: You cannot edit stock transactions.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
        
    transaction = db.session.get(InventoryTransaction, transaction_id)
    if not transaction or transaction.type != 'Outgoing':
        flash('Transaction not found or is not an outgoing type.', 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

    original_quantity = transaction.quantity

    if request.method == 'POST':
        try:
            new_quantity = int(request.form.get('quantity'))
            if new_quantity <= 0:
                flash('Quantity must be a positive number.', 'danger')
            else:
                # Adjust stock
                difference = new_quantity - original_quantity
                transaction.item.quantity -= difference
                
                # Update transaction details
                transaction.quantity = new_quantity
                transaction.date = request.form.get('date')
                
                db.session.commit()
                flash('Transaction updated successfully.', 'success')
                return redirect(url_for('inventory.inventory_transactions', transaction_type='Outgoing'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating transaction: {e}', 'danger')

    return render_template('edit_transaction.html', transaction=transaction)

@inventory_bp.route('/transaction/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    # ENFORCEMENT: Requires INV_EDIT permission
    if not current_user.can_access_feature('INV_EDIT'):
        flash("Permission denied: You cannot delete stock transactions.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
        
    transaction = db.session.get(InventoryTransaction, transaction_id)
    if not transaction or transaction.type != 'Outgoing':
        flash('Transaction not found or is not an outgoing type.', 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
    
    try:
        # Restore the stock quantity
        transaction.item.quantity += transaction.quantity
        
        db.session.delete(transaction)
        db.session.commit()
        flash('Transaction deleted and stock restored successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting transaction: {e}', 'danger')
    
    return redirect(url_for('inventory.inventory_transactions', transaction_type='Outgoing'))


# --- NEW DEDICATED VIEW ROUTES ---

@inventory_bp.route('/view/total_stock')
@login_required
def view_total_stock():
    # ENFORCEMENT: Requires INV_VIEW or INV_EDIT permission
    if not current_user.can_access_feature('INV_VIEW'):
        flash("Permission denied: You cannot view total stock records.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
    
    items = InventoryItem.query.order_by(InventoryItem.name).all()
    return render_template('inventory_total_stock.html', items=items, title="Current Stock List")

@inventory_bp.route('/view/received')
@login_required
def view_received():
    # ENFORCEMENT: Requires INV_VIEW or INV_EDIT permission
    if not current_user.can_access_feature('INV_VIEW'):
        flash("Permission denied: You cannot view received stock records.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
    
    transactions = InventoryTransaction.query.filter_by(type='Incoming').order_by(InventoryTransaction.date.desc()).all()
    return render_template('inventory_transactions.html', 
                           transactions=transactions, 
                           transaction_type="Incoming", 
                           title="Total Received Stock History",
                           can_download=current_user.can_access_feature('INV_VIEW'))

@inventory_bp.route('/view/distributed')
@login_required
def view_distributed():
    # ENFORCEMENT: Requires INV_VIEW or INV_EDIT permission
    if not current_user.can_access_feature('INV_VIEW'):
        flash("Permission denied: You cannot view distributed stock records.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
        
    transactions = InventoryTransaction.query.filter_by(type='Outgoing').order_by(InventoryTransaction.date.desc()).all()
    return render_template('inventory_transactions.html', 
                           transactions=transactions, 
                           transaction_type="Outgoing", 
                           title="Total Distributed Stock History",
                           can_download=current_user.can_access_feature('INV_VIEW'))


# --- DEDICATED DOWNLOAD ROUTES (REUSED) ---

@inventory_bp.route('/download/total_stock') # NEW DOWNLOAD ROUTE
@login_required
def download_total_stock():
    # ENFORCEMENT: Requires INV_VIEW or INV_EDIT permission
    if not current_user.can_access_feature('INV_VIEW'):
        flash("Permission denied: You cannot download inventory reports.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

    items = InventoryItem.query.order_by(InventoryItem.name).all()
    data = [{
        'Item Name': item.name,
        'Quantity in Stock': item.quantity
    } for item in items]
    
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name='Current Stock List')
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name='current_stock_list.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@inventory_bp.route('/download/incoming')
@login_required
def download_incoming_history():
    # ENFORCEMENT: Requires INV_VIEW or INV_EDIT permission
    if not current_user.can_access_feature('INV_VIEW'):
        flash("Permission denied: You cannot download incoming reports.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

    transactions = InventoryTransaction.query.filter_by(type='Incoming').order_by(InventoryTransaction.date.desc()).all()
    data = [{
        'Date': tx.date, 'Item Name': tx.item_name, 'Quantity': tx.quantity,
        'Supplier': tx.supplier_name, 'LPO Number': tx.lpo_number
    } for tx in transactions]
    
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name='Incoming Stock History')
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name='incoming_stock_history.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@inventory_bp.route('/download/outgoing')
@login_required
def download_outgoing_history():
    # ENFORCEMENT: Requires INV_VIEW or INV_EDIT permission
    if not current_user.can_access_feature('INV_VIEW'):
        flash("Permission denied: You cannot download distribution reports.", 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

    transactions = InventoryTransaction.query.filter_by(type='Outgoing').order_by(InventoryTransaction.date.desc()).all()
    data = [{
        'Date': tx.date, 'Item Name': tx.item_name, 'Quantity': tx.quantity,
        'Employee ID': tx.emp_id, 'Room Number': tx.room_number
    } for tx in transactions]
    
    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name='Outgoing Stock History')
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name='outgoing_stock_history.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@inventory_bp.route('/transactions/<string:transaction_type>')
@login_required
def inventory_transactions(transaction_type):
    transactions = InventoryTransaction.query.filter_by(type=transaction_type.title()).order_by(InventoryTransaction.date.desc()).all()
    
    can_download = current_user.can_access_feature('INV_VIEW')
    
    return render_template('inventory_transactions.html', 
                           transactions=transactions, 
                           transaction_type=transaction_type.title(),
                           can_download=can_download)