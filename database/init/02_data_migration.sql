-- Myanmar Election Data Migration Script
-- Consolidated data population for all 835 constituencies

-- First, create a temporary function to help with data insertion
CREATE OR REPLACE FUNCTION insert_constituency_batch(
    assembly_code assembly_type,
    data_file TEXT,
    default_source coordinate_source DEFAULT 'estimated'
) RETURNS void AS $$
BEGIN
    -- This function will be called from Python migration scripts
    -- to insert constituency data in batches
    RETURN;
END;
$$ LANGUAGE plpgsql;

-- Insert assembly information (already exists from schema)
-- PTHT, AMTHT, TPHT, TPTYT data will be populated via Python scripts

-- Create indexes for performance during bulk inserts
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_constituencies_bulk_insert 
ON constituencies(assembly_type, state_region_en, constituency_code);

-- Function to refresh all statistics after migration
CREATE OR REPLACE FUNCTION refresh_all_statistics()
RETURNS void AS $$
BEGIN
    -- Refresh materialized views
    REFRESH MATERIALIZED VIEW mv_regional_statistics;
    
    -- Clear cached statistics to force recalculation
    DELETE FROM cached_statistics WHERE cache_key LIKE '%_summary_%';
    
    -- Log completion
    INSERT INTO audit_log (table_name, record_id, action, new_data, changed_by)
    VALUES ('migration', 0, 'REFRESH_STATS', 
            json_build_object('timestamp', NOW(), 'action', 'statistics_refresh'),
            'migration_script');
END;
$$ LANGUAGE plpgsql;

-- Grant execution permissions
GRANT EXECUTE ON FUNCTION insert_constituency_batch(assembly_type, TEXT, coordinate_source) TO election_user;
GRANT EXECUTE ON FUNCTION refresh_all_statistics() TO election_user;