#!/usr/bin/env python3
"""
Complete Database Initialization Script
Consolidates all migration scripts into a single initialization process.
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import json
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

class DatabaseInitializer:
    """Complete database initialization with all data."""
    
    def __init__(self):
        self.connection_string = os.getenv(
            'DATABASE_URL',
            'postgresql://election_user:election_dev_2025@postgres:5432/myanmar_election'
        )
        self.base_path = Path(__file__).parent.parent
        
    def run_sql_file(self, sql_file_path: str, ignore_errors: bool = False):
        """Execute SQL file."""
        print(f"🔧 Executing {sql_file_path}...")
        
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor() as cursor:
                with open(sql_file_path, 'r', encoding='utf-8') as f:
                    cursor.execute(f.read())
            conn.commit()
            conn.close()
            print(f"✅ Completed {sql_file_path}")
        except Exception as e:
            if ignore_errors:
                print(f"⚠️  {sql_file_path} had errors (ignoring): {e}")
            else:
                print(f"❌ Error executing {sql_file_path}: {e}")
                raise
    
    def run_migration_script(self, script_path: str, description: str):
        """Run Python migration script."""
        print(f"🔧 {description}...")
        
        try:
            result = subprocess.run([
                sys.executable, script_path
            ], cwd=self.base_path, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ {description} completed")
                if result.stdout:
                    print(f"   Output: {result.stdout.strip()}")
            else:
                print(f"❌ {description} failed")
                print(f"   Error: {result.stderr}")
                raise Exception(f"Migration script failed: {script_path}")
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ {description} timed out (5 minutes)")
            raise
        except Exception as e:
            print(f"❌ Error running {description}: {e}")
            raise
    
    def check_data_completeness(self):
        """Verify all data was loaded correctly."""
        print("🔍 Verifying data completeness...")
        
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check total constituencies by assembly
                cursor.execute("""
                    SELECT 
                        assembly_type,
                        COUNT(*) as constituencies,
                        COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) as mapped,
                        ROUND(COUNT(CASE WHEN lat IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as mapped_pct
                    FROM constituencies 
                    WHERE election_year = 2025
                    GROUP BY assembly_type
                    ORDER BY assembly_type
                """)
                
                results = cursor.fetchall()
                
                print("📊 Data Loading Summary:")
                total_constituencies = 0
                total_mapped = 0
                
                for row in results:
                    total_constituencies += row['constituencies']
                    total_mapped += row['mapped']
                    print(f"   {row['assembly_type']}: {row['constituencies']} constituencies ({row['mapped_pct']}% mapped)")
                
                mapping_pct = round(total_mapped * 100.0 / total_constituencies, 1) if total_constituencies > 0 else 0
                print(f"   TOTAL: {total_constituencies} constituencies ({mapping_pct}% mapped)")
                
                # Expected totals
                expected = {"PTHT": 330, "AMTHT": 116, "TPHT": 360, "TPTYT": 29}
                actual = {row['assembly_type']: row['constituencies'] for row in results}
                
                all_good = True
                for assembly, expected_count in expected.items():
                    actual_count = actual.get(assembly, 0)
                    if actual_count != expected_count:
                        print(f"⚠️  {assembly}: Expected {expected_count}, got {actual_count}")
                        all_good = False
                
                if all_good and total_constituencies == 835:
                    print("✅ All constituency data loaded correctly!")
                else:
                    print("❌ Data loading incomplete or incorrect")
                    
            conn.close()
            return all_good and total_constituencies == 835
            
        except Exception as e:
            print(f"❌ Error checking data: {e}")
            return False
    
    def check_schema_exists(self):
        """Check if schema is already initialized."""
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'constituencies'
                    );
                """)
                schema_exists = cursor.fetchone()[0]
            conn.close()
            return schema_exists
        except Exception:
            return False
    
    def check_data_exists(self):
        """Check if data is already loaded."""
        try:
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM constituencies WHERE election_year = 2025;")
                count = cursor.fetchone()[0]
            conn.close()
            return count > 0, count
        except Exception:
            return False, 0
    
    def initialize_complete_database(self):
        """Run complete database initialization."""
        print("🚀 Starting Complete Database Initialization")
        print("=" * 60)
        
        try:
            # Check if schema already exists
            schema_exists = self.check_schema_exists()
            
            if schema_exists:
                print("✅ Database schema already exists, skipping schema creation")
            else:
                # 1. Create schema (if not exists)
                schema_file = self.base_path / 'database' / 'init' / '01_schema.sql'
                if schema_file.exists():
                    self.run_sql_file(str(schema_file), ignore_errors=True)
            
            # 2. Run migration helper (ignore errors if already exists)
            migration_sql = self.base_path / 'database' / 'init' / '02_data_migration.sql'
            if migration_sql.exists():
                self.run_sql_file(str(migration_sql), ignore_errors=True)
            
            # Check if data already exists
            data_exists, current_count = self.check_data_exists()
            
            if data_exists:
                print(f"✅ Database already contains {current_count} constituencies")
                if current_count >= 800:  # Near complete dataset
                    print("🎯 Dataset appears complete, skipping migrations")
                    # Skip to final verification
                    if self.check_data_completeness():
                        print("\n🎉 Database already fully initialized!")
                        return True
                else:
                    print("⚠️  Dataset incomplete, running remaining migrations...")
            
            # 3. Migrate CSV data to database (PTHT base data)
            csv_migration = self.base_path / 'database' / 'migrate_csv_to_db.py'
            if csv_migration.exists() and current_count < 300:
                self.run_migration_script(str(csv_migration), "Migrating CSV data (PTHT base)")
            
            # 4. Expand to all assemblies (TPHT, TPTYT)
            expand_script = self.base_path / 'database' / 'expand_constituencies.py'
            if expand_script.exists() and current_count < 700:
                self.run_migration_script(str(expand_script), "Expanding to TPHT and TPTYT assemblies")
            
            # 5. Add Amyotha Hluttaw constituencies
            amyotha_script = self.base_path / 'database' / 'add_amyotha_hluttaw.py'
            if amyotha_script.exists() and current_count < 800:
                self.run_migration_script(str(amyotha_script), "Adding Amyotha Hluttaw constituencies")
            
            # 6. Geocode all constituencies
            geocode_script = self.base_path / 'database' / 'geocode_constituencies.py'
            if geocode_script.exists():
                self.run_migration_script(str(geocode_script), "Geocoding all constituencies")
            
            # 7. Refresh statistics
            print("🔧 Refreshing database statistics...")
            conn = psycopg2.connect(self.connection_string)
            with conn.cursor() as cursor:
                cursor.execute("SELECT refresh_all_statistics();")
            conn.commit()
            conn.close()
            print("✅ Statistics refreshed")
            
            # 8. Final verification
            if self.check_data_completeness():
                print("\n🎉 Database initialization completed successfully!")
                print("📊 Ready for production use with 835 constituencies")
                return True
            else:
                print("\n❌ Database initialization completed with issues")
                return False
                
        except Exception as e:
            print(f"\n💥 Database initialization failed: {e}")
            return False

def main():
    """Main initialization function."""
    print("Myanmar Election Database - Complete Initialization")
    print("=" * 60)
    
    # Environment check
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("⚠️  DATABASE_URL not set, using default")
    
    # Run initialization
    initializer = DatabaseInitializer()
    success = initializer.initialize_complete_database()
    
    if success:
        print("\n✅ Database ready for Myanmar Election Visualization!")
        print("🌐 Access application at: http://localhost:8501")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()