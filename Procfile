release: python -c "from app import app, db; with app.app_context(): db.create_all()"
web: gunicorn --bind 0.0.0.0:$PORT app:app