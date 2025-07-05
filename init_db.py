from app import create_app, db

print("--- Running init_db.py ---")
app = create_app()
with app.app_context():
    print("App context created. Creating all database tables...")
    try:
        db.create_all()
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"An error occurred during database initialization: {e}")
        exit(1)
print("--- Database initialization script finished ---")
