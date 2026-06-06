-- Supabase SQL Schema for SmartCaptcha
-- Run this in Supabase SQL Editor

-- Drop existing tables if they exist
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

-- Create projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    allowed_domains TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create api_keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    key_hash VARCHAR(256) UNIQUE NOT NULL,
    key_prefix VARCHAR(12) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Create sessions table
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    device_type VARCHAR(20),
    screen_width INT,
    screen_height INT,
    user_agent TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    label VARCHAR(10),
    risk_score FLOAT,
    event_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create events table with individual ML feature columns
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id),
    event_type VARCHAR(10) NOT NULL,
    t BIGINT,
    x INTEGER,
    y INTEGER,
    dist REAL,
    ang REAL,
    vel REAL,
    total_dist REAL,
    target TEXT,
    click_interval INTEGER,
    is_double BOOLEAN,
    tw INTEGER,
    th INTEGER,
    k TEXT,
    iki INTEGER,
    hold INTEGER,
    scroll_y INTEGER,
    scroll_vel REAL,
    scroll_rev BOOLEAN,
    scroll_pause BOOLEAN,
    state TEXT,
    action TEXT,
    force REAL,
    duration INTEGER,
    gesture TEXT,
    swipe_dist REAL,
    swipe_vel REAL,
    payload JSONB NOT NULL,
    received_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_received ON events(received_at);
CREATE INDEX idx_sessions_created ON sessions(created_at);
CREATE INDEX idx_sessions_label ON sessions(label);
CREATE INDEX idx_sessions_project ON sessions(project_id);
