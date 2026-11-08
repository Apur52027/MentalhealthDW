-- Student Mental Health Data Warehouse - BI queries
-- Each query starts with `-- name: <id>`; filters use :dept and :year (NULL = all).

-- name: kpi_summary
-- Headline numbers
SELECT COUNT(DISTINCT f.student_id) AS students_assessed,
       COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(AVG(f.stress_score), 2)     AS avg_stress,
       ROUND(AVG(f.anxiety_score), 2)    AS avg_anxiety,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'Medium' THEN 1 ELSE 0 END) / COUNT(*), 1) AS medium_risk_pct,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' AND m.counseling_status = 'None' THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END), 0), 1) AS high_risk_without_counseling_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year);

-- name: risk_distribution
-- Count of each risk level
SELECT f.risk_level AS risk_level, COUNT(*) AS assessments,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY f.risk_level
ORDER BY CASE f.risk_level WHEN 'Low' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END;

-- name: risk_by_department
-- Scores and risk by department
SELECT s.department AS department, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(AVG(f.stress_score), 2)     AS avg_stress,
       ROUND(AVG(f.anxiety_score), 2)    AS avg_anxiety,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY s.department
ORDER BY high_risk_pct DESC;

-- name: trend_by_period
-- Trend over assessment dates (year filter ignored)
SELECT t.date AS assessment_date, t.semester AS term, t.year AS year, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(AVG(f.stress_score), 2)     AS avg_stress,
       ROUND(AVG(f.anxiety_score), 2)    AS avg_anxiety,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
GROUP BY t.time_id, t.date, t.semester, t.year
ORDER BY t.date;

-- name: factor_sleep
-- Risk by sleep duration
SELECT l.sleep_band AS band, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY l.sleep_band
ORDER BY MIN(l.sleep_hours);

-- name: factor_social_media
-- Risk by social media usage
SELECT l.social_media_band AS band, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY l.social_media_band
ORDER BY MIN(l.social_media_hours);

-- name: factor_exercise
-- Risk by exercise frequency
SELECT l.exercise_band AS band, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY l.exercise_band
ORDER BY MIN(l.exercise_days);

-- name: factor_gpa
-- Risk by GPA
SELECT a.gpa_band AS band, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY a.gpa_band
ORDER BY MIN(a.gpa);

-- name: factor_attendance
-- Risk by attendance
SELECT a.attendance_band AS band, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY a.attendance_band
ORDER BY MIN(a.attendance_pct);

-- name: gender_comparison
-- Scores and risk by gender
SELECT s.gender AS gender, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(AVG(f.stress_score), 2)     AS avg_stress,
       ROUND(AVG(f.anxiety_score), 2)    AS avg_anxiety,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY s.gender
ORDER BY high_risk_pct DESC;

-- name: semester_level_risk
-- Risk by the student's academic semester
SELECT s.semester AS student_semester, COUNT(*) AS assessments,
       ROUND(AVG(f.depression_score), 2) AS avg_depression,
       ROUND(100.0 * SUM(CASE WHEN f.risk_level = 'High' THEN 1 ELSE 0 END) / COUNT(*), 1) AS high_risk_pct
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY s.semester
ORDER BY s.semester;

-- name: counseling_coverage
-- Counseling status within each risk level
SELECT f.risk_level AS risk_level, m.counseling_status AS counseling_status, COUNT(*) AS assessments
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
GROUP BY f.risk_level, m.counseling_status
ORDER BY CASE f.risk_level WHEN 'Low' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
         CASE m.counseling_status WHEN 'None' THEN 1 WHEN 'Occasional' THEN 2 ELSE 3 END;

-- name: at_risk_students
-- High-risk students at their LATEST assessment (anonymised IDs)
SELECT f.student_id AS student_id, s.department AS department, s.semester AS student_semester,
       t.date AS assessment_date, f.depression_score, f.stress_score, f.anxiety_score,
       l.sleep_hours, l.social_media_hours, a.gpa, a.attendance_pct,
       m.counseling_status AS counseling_status
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
WHERE (:dept IS NULL OR s.department = :dept)
  AND (:year IS NULL OR t.year = :year)
  AND f.risk_level = 'High'
  AND t.date = (SELECT MAX(t2.date) FROM fact_depression f2
                JOIN dim_time t2 ON t2.time_id = f2.time_id
                WHERE f2.student_id = f.student_id)
ORDER BY (m.counseling_status = 'None') DESC, f.depression_score DESC
LIMIT 50;
