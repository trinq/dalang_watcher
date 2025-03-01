-- Initial database setup for Dalang Watcher project
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dalang_watcher') THEN
        CREATE DATABASE dalang_watcher;
    END IF;
END
$$;

\c dalang_watcher;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create tables
CREATE TABLE IF NOT EXISTS scans (
    scan_id SERIAL PRIMARY KEY,
    scan_type VARCHAR(50),
    target TEXT,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scan_results (
    result_id SERIAL,
    scan_id INTEGER REFERENCES scans(scan_id),
    target TEXT,
    port INTEGER,
    protocol VARCHAR(10),
    status VARCHAR(20),
    additional_data JSONB,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (result_id, discovered_at)
);

-- Convert scan_results to a TimescaleDB hypertable
SELECT create_hypertable('scan_results', 'discovered_at', if_not_exists => TRUE);

-- Create an index on target for faster lookups
CREATE INDEX IF NOT EXISTS idx_scan_results_target ON scan_results(target);