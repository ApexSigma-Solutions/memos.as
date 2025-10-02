#!/usr/bin/env python3
"""
Database Initialization Script for memOS.as

This script ensures the PostgreSQL database tables are properly created
with correct schema for integration testing.
"""

import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))


def initialize_database():
    """Initialize the PostgreSQL database with correct schema."""
    try:
        print("🗄️  Initializing memOS.as database...")
    except UnicodeEncodeError:
        print("Initializing memOS.as database...")

    try:
        from services.postgres_client import PostgresClient, Base

        # Create PostgreSQL client
        client = PostgresClient()

        # Drop and recreate all tables to ensure correct schema
        try:
            print("🔄 Recreating database tables...")
        except UnicodeEncodeError:
            print("Recreating database tables...")
        Base.metadata.drop_all(bind=client.engine)
        Base.metadata.create_all(bind=client.engine)

        # Test the connection and table creation
        with client.get_session() as session:
            # Test a simple query
            from sqlalchemy import text

            session.execute(text("SELECT 1"))

            # Check that our tables exist
            result = session.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
            )

            tables = [row[0] for row in result.fetchall()]
            try:
                print(f"✅ Created tables: {', '.join(tables)}")
            except UnicodeEncodeError:
                print(f"Created tables: {', '.join(tables)}")

            # Verify the memories table has correct schema
            result = session.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'memories'
                ORDER BY ordinal_position
            """
            )

            columns = result.fetchall()
            try:
                print("📋 Memories table schema:")
            except UnicodeEncodeError:
                print("Memories table schema:")
            for col_name, data_type, nullable, default in columns:
                print(
                    f"   {col_name:15} : {data_type:12} (nullable: {nullable}, default: {default})"
                )

            # Check if id column has proper auto-increment (serial/sequence)
            id_column = next((col for col in columns if col[0] == "id"), None)
            if id_column and "nextval" in str(id_column[3]):
                try:
                    print("✅ ID column properly configured with auto-increment")
                except UnicodeEncodeError:
                    print("ID column properly configured with auto-increment")
            else:
                try:
                    print("⚠️  ID column may not have auto-increment configured")
                except UnicodeEncodeError:
                    print("ID column may not have auto-increment configured")

        try:
            print("✅ Database initialization completed successfully")
        except UnicodeEncodeError:
            print("Database initialization completed successfully")
        return True

    except Exception as e:
        try:
            print(f"❌ Database initialization failed: {e}")
        except UnicodeEncodeError:
            print(f"Database initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_memory_storage():
    """Test memory storage functionality."""
    try:
        print("\n🧪 Testing memory storage...")
    except UnicodeEncodeError:
        print("\nTesting memory storage...")

    try:
        from services.postgres_client import get_postgres_client

        client = get_postgres_client()

        # Test storing a memory
        test_content = "Integration test memory content"
        test_metadata = {"test": True, "source": "init_script"}

        memory_id = client.store_memory(content=test_content, metadata=test_metadata)

        if memory_id is not None:
            try:
                print(f"✅ Successfully stored test memory with ID: {memory_id}")
            except UnicodeEncodeError:
                print(f"Successfully stored test memory with ID: {memory_id}")

            # Test retrieving the memory
            retrieved_memory = client.get_memory(memory_id)
            if retrieved_memory:
                try:
                    print(
                        f"✅ Successfully retrieved memory: {retrieved_memory['content'][:50]}..."
                    )
                except UnicodeEncodeError:
                    print(
                        f"Successfully retrieved memory: {retrieved_memory['content'][:50]}..."
                    )
                return True
            else:
                try:
                    print("❌ Failed to retrieve stored memory")
                except UnicodeEncodeError:
                    print("Failed to retrieve stored memory")
                return False
        else:
            try:
                print("❌ Failed to store test memory - returned None")
            except UnicodeEncodeError:
                print("Failed to store test memory - returned None")
            return False

    except Exception as e:
        try:
            print(f"❌ Memory storage test failed: {e}")
        except UnicodeEncodeError:
            print(f"Memory storage test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function to initialize database and run tests."""
    try:
        print("🚀 MEMOS.AS DATABASE INITIALIZATION")
        print("=" * 50)
    except UnicodeEncodeError:
        # Fallback for Windows console encoding issues
        print("MEMOS.AS DATABASE INITIALIZATION")
        print("=" * 50)

    # Initialize database
    if not initialize_database():
        try:
            print("\n💥 Database initialization failed")
        except UnicodeEncodeError:
            print("\nDatabase initialization failed")
        return False

    # Test functionality
    if not test_memory_storage():
        try:
            print("\n💥 Memory storage test failed")
        except UnicodeEncodeError:
            print("\nMemory storage test failed")
        return False

    try:
        print("\n🎉 Database initialization and testing completed successfully!")
        print("📊 memOS.as is ready for integration testing")
    except UnicodeEncodeError:
        print("\nDatabase initialization and testing completed successfully!")
        print("memOS.as is ready for integration testing")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
