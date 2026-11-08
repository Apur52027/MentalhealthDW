-- Portable star-schema DDL (PostgreSQL / MySQL friendly) matching the proposal's diagram.
-- The app itself uses SQLite (zero setup); use this file to deploy on PostgreSQL / MySQL.

CREATE TABLE dim_student (
    student_id VARCHAR(20) PRIMARY KEY, gender VARCHAR(10) NOT NULL, age INT,
    department VARCHAR(40) NOT NULL, semester INT);

CREATE TABLE dim_academic (
    academic_id SERIAL PRIMARY KEY, gpa NUMERIC(3,2) NOT NULL, attendance_pct NUMERIC(5,1) NOT NULL,
    study_hours NUMERIC(4,1) NOT NULL, gpa_band VARCHAR(20) NOT NULL, attendance_band VARCHAR(20) NOT NULL,
    UNIQUE (gpa, attendance_pct, study_hours));

CREATE TABLE dim_lifestyle (
    lifestyle_id SERIAL PRIMARY KEY, sleep_hours NUMERIC(3,1) NOT NULL, exercise_days INT NOT NULL,
    social_media_hours NUMERIC(4,1) NOT NULL, sleep_band VARCHAR(30) NOT NULL,
    exercise_band VARCHAR(30) NOT NULL, social_media_band VARCHAR(30) NOT NULL,
    UNIQUE (sleep_hours, exercise_days, social_media_hours));

CREATE TABLE dim_mentalhealth (
    mentalhealth_id SERIAL PRIMARY KEY, anxiety_score INT NOT NULL, stress_score INT NOT NULL,
    counseling_status VARCHAR(20) NOT NULL, anxiety_level VARCHAR(20) NOT NULL, stress_level VARCHAR(20) NOT NULL,
    UNIQUE (anxiety_score, stress_score, counseling_status));

CREATE TABLE dim_time (
    time_id SERIAL PRIMARY KEY, date DATE NOT NULL UNIQUE, month INT NOT NULL,
    month_name VARCHAR(12) NOT NULL, semester VARCHAR(10) NOT NULL, year INT NOT NULL);

CREATE TABLE fact_depression (
    fact_id SERIAL PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL REFERENCES dim_student(student_id),
    academic_id INT NOT NULL REFERENCES dim_academic(academic_id),
    lifestyle_id INT NOT NULL REFERENCES dim_lifestyle(lifestyle_id),
    mentalhealth_id INT NOT NULL REFERENCES dim_mentalhealth(mentalhealth_id),
    time_id INT NOT NULL REFERENCES dim_time(time_id),
    depression_score INT NOT NULL CHECK (depression_score BETWEEN 0 AND 27),
    stress_score INT NOT NULL CHECK (stress_score BETWEEN 0 AND 40),
    anxiety_score INT NOT NULL CHECK (anxiety_score BETWEEN 0 AND 21),
    risk_level VARCHAR(6) NOT NULL CHECK (risk_level IN ('Low','Medium','High')),
    UNIQUE (student_id, time_id));
