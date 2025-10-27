-- PostgreSQL + JSONB Schema for BrokerCursor
-- Created: 2025-01-22
-- Purpose: Centralized storage for broker reports with flexible JSONB data

-- Main table for broker reports
CREATE TABLE IF NOT EXISTS broker_reports (
    id SERIAL PRIMARY KEY,
    broker VARCHAR(50) NOT NULL,
    account VARCHAR(50),
    period CHAR(7) NOT NULL, -- YYYY-MM
    report_date DATE,
    client_name VARCHAR(255),
    
    -- Source file information
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),
    file_size BIGINT,
    file_hash VARCHAR(64), -- SHA-256 for deduplication
    
    -- Content storage
    html_content TEXT,
    raw_content TEXT, -- For non-HTML files
    
    -- Processed data (JSONB for flexibility)
    parsed_data JSONB,
    metadata JSONB, -- Additional metadata
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'raw' CHECK (processing_status IN ('raw', 'processing', 'parsed', 'error')),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    
    -- Versioning and error tracking
    parser_version VARCHAR(20),
    error_log TEXT,
    
    -- Constraints
    -- Uniqueness is enforced via a functional unique index on (broker, COALESCE(account,'∅'), period)
);

-- Import log table for tracking operations
CREATE TABLE IF NOT EXISTS import_log (
    id SERIAL PRIMARY KEY,
    operation_type VARCHAR(20) NOT NULL CHECK (operation_type IN ('import', 'update', 'delete', 'archive')),
    broker VARCHAR(50),
    -- Per-file context (nullable for aggregate entries)
    file_name VARCHAR(500),
    account VARCHAR(50),
    period CHAR(7),
    file_hash VARCHAR(64),
    status VARCHAR(40), -- e.g., success, duplicate_detected, collision_mismatch, failure
    files_processed INTEGER DEFAULT 0,
    files_success INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    error_summary TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_broker_reports_broker_period ON broker_reports(broker, period);
CREATE INDEX IF NOT EXISTS idx_broker_reports_status ON broker_reports(processing_status);
CREATE INDEX IF NOT EXISTS idx_broker_reports_created_at ON broker_reports(created_at);
CREATE INDEX IF NOT EXISTS idx_broker_reports_file_hash ON broker_reports(file_hash);
-- Functional unique index to prevent duplicates with NULL account treated as a sentinel
CREATE UNIQUE INDEX IF NOT EXISTS ux_broker_reports_broker_account_period
    ON broker_reports (broker, COALESCE(account, '∅'), period);

-- Semantic duplicate index on parsed_data fields for deep validation
CREATE UNIQUE INDEX IF NOT EXISTS ux_semantic_duplicate 
    ON broker_reports ((parsed_data->>'broker'), (parsed_data->>'account_number'), (parsed_data->>'period_start'), (parsed_data->>'period_end')) 
    WHERE parsed_data IS NOT NULL;

-- JSONB indexes for flexible querying
CREATE INDEX IF NOT EXISTS idx_broker_reports_parsed_data ON broker_reports USING GIN(parsed_data);
CREATE INDEX IF NOT EXISTS idx_broker_reports_metadata ON broker_reports USING GIN(metadata);

-- Import log indexes
CREATE INDEX IF NOT EXISTS idx_import_log_operation_type ON import_log(operation_type);
CREATE INDEX IF NOT EXISTS idx_import_log_started_at ON import_log(started_at);
CREATE INDEX IF NOT EXISTS idx_import_log_status ON import_log(status);
CREATE INDEX IF NOT EXISTS idx_import_log_file_hash ON import_log(file_hash);
CREATE INDEX IF NOT EXISTS idx_import_log_broker_period ON import_log(broker, period);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_broker_reports_updated_at 
    BEFORE UPDATE ON broker_reports 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE broker_reports IS 'Main table storing broker reports with flexible JSONB data';
COMMENT ON COLUMN broker_reports.parsed_data IS 'Structured data extracted from reports (JSONB)';
COMMENT ON COLUMN broker_reports.metadata IS 'Additional metadata and processing info (JSONB)';
COMMENT ON COLUMN broker_reports.processing_status IS 'Report processing status: raw, processing, parsed, error';
COMMENT ON COLUMN broker_reports.file_hash IS 'SHA-256 hash for deduplication';
