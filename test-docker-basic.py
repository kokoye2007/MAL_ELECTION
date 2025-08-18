#!/usr/bin/env python3
"""
Basic test to validate Docker setup without full build.
Tests configuration files and basic functionality.
"""

import yaml
import json
import os
import sys
from pathlib import Path

def test_docker_compose():
    """Test docker-compose.yml is valid."""
    print("🔍 Testing docker-compose.yml...")
    
    try:
        with open('docker-compose.yml', 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Check required services
        required_services = ['postgres', 'myanmar-election-viz', 'nginx', 'redis']
        services = compose_config.get('services', {})
        
        for service in required_services:
            if service not in services:
                print(f"❌ Missing service: {service}")
                return False
            print(f"✅ Service found: {service}")
        
        # Check postgres configuration
        postgres = services['postgres']
        if postgres.get('image') != 'postgis/postgis:15-3.4':
            print(f"❌ Wrong postgres image: {postgres.get('image')}")
            return False
        
        print("✅ docker-compose.yml is valid")
        return True
        
    except Exception as e:
        print(f"❌ docker-compose.yml error: {e}")
        return False

def test_dockerfile():
    """Test Dockerfile syntax."""
    print("\n🔍 Testing Dockerfile...")
    
    try:
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()
        
        # Check required elements
        required_elements = [
            'FROM python:3.11-slim',
            'WORKDIR /app',
            'COPY requirements.txt',
            'RUN pip install',
            'EXPOSE 8501',
            'CMD ["streamlit"'
        ]
        
        for element in required_elements:
            if element not in dockerfile_content:
                print(f"❌ Missing in Dockerfile: {element}")
                return False
            print(f"✅ Found: {element}")
        
        print("✅ Dockerfile is valid")
        return True
        
    except Exception as e:
        print(f"❌ Dockerfile error: {e}")
        return False

def test_requirements():
    """Test requirements.txt is valid."""
    print("\n🔍 Testing requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        # Check critical packages
        critical_packages = [
            'streamlit',
            'pandas',
            'folium',
            'psycopg2-binary',
            'redis'
        ]
        
        for package in critical_packages:
            if package not in requirements:
                print(f"❌ Missing package: {package}")
                return False
            print(f"✅ Package found: {package}")
        
        # Check for problematic packages
        if 'streamlit-redis' in requirements:
            print("❌ Found problematic package: streamlit-redis")
            return False
        
        print("✅ requirements.txt is valid")
        return True
        
    except Exception as e:
        print(f"❌ requirements.txt error: {e}")
        return False

def test_sql_schema():
    """Test SQL schema file."""
    print("\n🔍 Testing SQL schema...")
    
    try:
        schema_file = Path('database/init/01_schema.sql')
        if not schema_file.exists():
            print(f"❌ Schema file missing: {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            schema_content = f.read()
        
        # Check required tables
        required_tables = [
            'CREATE TABLE constituencies',
            'CREATE TABLE mimu_boundaries',
            'CREATE TABLE assemblies',
            'CREATE EXTENSION IF NOT EXISTS postgis'
        ]
        
        for table in required_tables:
            if table not in schema_content:
                print(f"❌ Missing SQL element: {table}")
                return False
            print(f"✅ Found: {table}")
        
        print("✅ SQL schema is valid")
        return True
        
    except Exception as e:
        print(f"❌ SQL schema error: {e}")
        return False

def test_migration_script():
    """Test migration script syntax."""
    print("\n🔍 Testing migration script...")
    
    try:
        migration_file = Path('database/migrate_csv_to_db.py')
        if not migration_file.exists():
            print(f"❌ Migration script missing: {migration_file}")
            return False
        
        # Basic syntax check
        with open(migration_file, 'r') as f:
            content = f.read()
        
        # Compile to check syntax
        compile(content, migration_file, 'exec')
        
        # Check for required classes/functions
        required_elements = [
            'class CSVToDatabaseMigrator',
            'def run_migration',
            'def load_csv_data',
            'def validate_migration'
        ]
        
        for element in required_elements:
            if element not in content:
                print(f"❌ Missing in migration script: {element}")
                return False
            print(f"✅ Found: {element}")
        
        print("✅ Migration script is valid")
        return True
        
    except Exception as e:
        print(f"❌ Migration script error: {e}")
        return False

def test_data_files():
    """Test required data files exist."""
    print("\n🔍 Testing data files...")
    
    data_files = [
        'data/processed/myanmar_constituencies.json',
        'data/processed/summary_statistics.json'
    ]
    
    for file_path in data_files:
        if Path(file_path).exists():
            print(f"✅ Found: {file_path}")
        else:
            print(f"⚠️  Optional file missing: {file_path}")
    
    # Check if at least one constituency data file exists
    csv_exists = Path('data/processed/myanmar_constituencies.csv').exists()
    json_exists = Path('data/processed/myanmar_constituencies.json').exists()
    
    if csv_exists or json_exists:
        print("✅ Constituency data available for migration")
        return True
    else:
        print("⚠️  No constituency data found (migration will skip)")
        return True  # Not a failure, just no data to migrate

def main():
    """Run all tests."""
    print("🐳 Docker Migration Configuration Test")
    print("=" * 50)
    
    tests = [
        test_docker_compose,
        test_dockerfile,
        test_requirements,
        test_sql_schema,
        test_migration_script,
        test_data_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Docker migration setup is ready.")
        print("\n📝 Next steps:")
        print("   1. Build containers: docker-compose build")
        print("   2. Start services: docker-compose up -d")
        print("   3. Run migration: docker-compose exec myanmar-election-app python database/migrate_csv_to_db.py")
        print("   4. Access app: http://localhost:8501")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)