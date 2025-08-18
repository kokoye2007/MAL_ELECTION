-- Myanmar Election Visualization Database Schema
-- PostGIS-enabled database for handling geographic and electoral data

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Create enum types for better data integrity
CREATE TYPE assembly_type AS ENUM ('PTHT', 'AMTHT', 'TPHT', 'TPTYT');
CREATE TYPE electoral_system AS ENUM ('FPTP', 'PR');
CREATE TYPE coordinate_source AS ENUM ('geocoded', 'manual', 'estimated', 'mimu');
CREATE TYPE validation_status AS ENUM ('verified', 'pending', 'needs_review', 'rejected');

-- Main constituencies table
CREATE TABLE constituencies (
    id SERIAL PRIMARY KEY,
    
    -- Identification
    constituency_code VARCHAR(20) UNIQUE NOT NULL,
    constituency_en VARCHAR(200) NOT NULL,
    constituency_mm VARCHAR(200) NOT NULL,
    
    -- Administrative division
    state_region_en VARCHAR(100) NOT NULL,
    state_region_mm VARCHAR(100) NOT NULL,
    
    -- Electoral information
    assembly_type assembly_type NOT NULL,
    electoral_system electoral_system DEFAULT 'FPTP',
    representatives INTEGER NOT NULL DEFAULT 1,
    
    -- Geographic data
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    coordinate_source coordinate_source,
    validation_status validation_status DEFAULT 'pending',
    
    -- Additional information
    areas_included_en TEXT,
    areas_included_mm TEXT,
    ethnic_group VARCHAR(50), -- For TPTYT constituencies
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    election_year INTEGER NOT NULL DEFAULT 2025,
    
    -- Geographic point for spatial queries
    geom GEOMETRY(POINT, 4326)
);

-- Create spatial index
CREATE INDEX idx_constituencies_geom ON constituencies USING GIST (geom);

-- Create other indexes for performance
CREATE INDEX idx_constituencies_assembly ON constituencies(assembly_type);
CREATE INDEX idx_constituencies_state_region ON constituencies(state_region_en);
CREATE INDEX idx_constituencies_electoral_system ON constituencies(electoral_system);
CREATE INDEX idx_constituencies_validation ON constituencies(validation_status);
CREATE INDEX idx_constituencies_year ON constituencies(election_year);

-- Historical constituencies table for 2020 data
CREATE TABLE historical_constituencies (
    id SERIAL PRIMARY KEY,
    constituency_code VARCHAR(20) NOT NULL,
    constituency_en VARCHAR(200) NOT NULL,
    constituency_mm VARCHAR(200),
    state_region_en VARCHAR(100) NOT NULL,
    state_region_mm VARCHAR(100),
    assembly_type assembly_type NOT NULL,
    representatives INTEGER NOT NULL DEFAULT 1,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    areas_included_en TEXT,
    election_year INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(POINT, 4326)
);

CREATE INDEX idx_historical_constituencies_geom ON historical_constituencies USING GIST (geom);
CREATE INDEX idx_historical_constituencies_year ON historical_constituencies(election_year);

-- MIMU boundaries table for geographic reference
CREATE TABLE mimu_boundaries (
    id SERIAL PRIMARY KEY,
    fid INTEGER,
    st_pcode VARCHAR(20),
    ts_pcode VARCHAR(20),
    township_name_en VARCHAR(100),
    township_name_mm VARCHAR(100),
    state_region_en VARCHAR(100),
    state_region_mm VARCHAR(100),
    boundary_geom GEOMETRY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mimu_boundaries_geom ON mimu_boundaries USING GIST (boundary_geom);
CREATE INDEX idx_mimu_ts_pcode ON mimu_boundaries(ts_pcode);

-- Assembly metadata table
CREATE TABLE assemblies (
    id SERIAL PRIMARY KEY,
    assembly_type assembly_type UNIQUE NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    name_mm VARCHAR(100) NOT NULL,
    total_seats INTEGER NOT NULL,
    electoral_system electoral_system NOT NULL,
    description TEXT,
    election_year INTEGER NOT NULL DEFAULT 2025
);

-- Insert assembly metadata
INSERT INTO assemblies (assembly_type, name_en, name_mm, total_seats, electoral_system, description) VALUES
('PTHT', 'Pyithu Hluttaw', 'ပြည်သူ့လွှတ်တော်', 330, 'FPTP', 'House of Representatives (Lower House)'),
('AMTHT', 'Amyotha Hluttaw', 'အမျိုးသားလွှတ်တော်', 110, 'FPTP', 'House of Nationalities (Upper House)'),
('TPHT', 'State/Regional Assemblies', 'တိုင်း/ပြည်နယ်လွှတ်တော်များ', 296, 'FPTP', 'Local legislative assemblies'),
('TPTYT', 'Ethnic Affairs', 'လူမျိုးရေးရာ', 29, 'PR', 'Ethnic minority representation');

-- Statistics and caching table
CREATE TABLE cached_statistics (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(100) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    election_year INTEGER NOT NULL DEFAULT 2025
);

CREATE INDEX idx_cached_statistics_key ON cached_statistics(cache_key);
CREATE INDEX idx_cached_statistics_expires ON cached_statistics(expires_at);

-- Audit log table for data changes
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_changed_at ON audit_log(changed_at);

-- Function to automatically update geom column when lat/lng changes
CREATE OR REPLACE FUNCTION update_constituency_geom()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.lat IS NOT NULL AND NEW.lng IS NOT NULL THEN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.lng, NEW.lat), 4326);
    END IF;
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update geometry
CREATE TRIGGER tr_constituencies_update_geom
    BEFORE INSERT OR UPDATE ON constituencies
    FOR EACH ROW
    EXECUTE FUNCTION update_constituency_geom();

-- Function for audit logging
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, record_id, action, old_data, new_data, changed_by)
    VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END,
        current_user
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Add audit triggers to important tables
CREATE TRIGGER tr_constituencies_audit
    AFTER INSERT OR UPDATE OR DELETE ON constituencies
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Views for common queries
CREATE VIEW v_constituency_summary AS
SELECT 
    assembly_type,
    state_region_en,
    COUNT(*) as constituency_count,
    SUM(representatives) as total_representatives,
    COUNT(CASE WHEN validation_status = 'verified' THEN 1 END) as verified_count,
    COUNT(CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 1 END) as mapped_count
FROM constituencies
WHERE election_year = 2025
GROUP BY assembly_type, state_region_en
ORDER BY assembly_type, state_region_en;

-- Performance optimization: Materialized view for expensive aggregations
CREATE MATERIALIZED VIEW mv_regional_statistics AS
SELECT 
    state_region_en,
    state_region_mm,
    COUNT(*) as total_constituencies,
    SUM(representatives) as total_representatives,
    COUNT(DISTINCT assembly_type) as assembly_types,
    ST_Centroid(ST_Collect(geom)) as region_center,
    ST_Extent(geom) as region_bounds
FROM constituencies
WHERE election_year = 2025 AND geom IS NOT NULL
GROUP BY state_region_en, state_region_mm;

CREATE INDEX idx_mv_regional_statistics_region ON mv_regional_statistics(state_region_en);

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_regional_statistics;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions for application user
GRANT USAGE ON SCHEMA public TO election_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO election_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO election_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO election_user;