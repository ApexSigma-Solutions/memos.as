import os
print("DATABASE_URL:", os.environ.get("DATABASE_URL"))
print("POSTGRES_HOST:", os.environ.get("POSTGRES_HOST"))
print("POSTGRES_DB:", os.environ.get("POSTGRES_DB"))
print("POSTGRES_USER:", os.environ.get("POSTGRES_USER"))
print("POSTGRES_PORT:", os.environ.get("POSTGRES_PORT"))