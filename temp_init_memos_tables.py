from app.services.postgres_client import get_postgres_client

# Initialize the PostgreSQL client which will create tables
client = get_postgres_client()
print("Tables initialized successfully")