-- Initial database setup for ASM project
CREATE DATABASE asm;
\c asm;

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
    result_id SERIAL PRIMARY KEY,
    scan_id INTEGER REFERENCES scans(scan_id),
    target TEXT,
    port INTEGER,
    protocol VARCHAR(10),
    status VARCHAR(20),
    additional_data JSONB,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Convert scan_results to a TimescaleDB hypertable
SELECT create_hypertable('scan_results', 'discovered_at');

-- Create an index on target for faster lookups
CREATE INDEX idx_scan_results_target ON scan_results(target);