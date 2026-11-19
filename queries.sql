-- phpMyAdmin madhe "client_results" database select kara, mag SQL tab madhe ek-ek query chalva.

-- 1) Sheet madhla sagla data (sheet madhle ajun rows yethe disatil)
SELECT * FROM results LIMIT 100;

-- 2) Ekun summary
SELECT COUNT(DISTINCT student_name) AS students,
       ROUND(AVG(marks), 1) AS avg_marks,
       ROUND(100 * SUM(marks >= 40) / COUNT(*), 1) AS pass_pct,
       ROUND(AVG(attendance_pct), 1) AS avg_attendance
FROM results;

-- 3) Vishayanusar average ani pass %
SELECT subject,
       ROUND(AVG(marks), 1) AS avg_marks,
       ROUND(100 * SUM(marks >= 40) / COUNT(*), 1) AS pass_pct
FROM results
GROUP BY subject
ORDER BY avg_marks DESC;

-- 4) City-nusar average
SELECT city, ROUND(AVG(marks), 1) AS avg_marks
FROM results
GROUP BY city
ORDER BY avg_marks DESC;

-- 5) Attendance kami asnare vidyarthi (75% pekshya kami)
SELECT student_name, ROUND(AVG(attendance_pct), 1) AS attendance, ROUND(AVG(marks), 1) AS avg_marks
FROM results
GROUP BY student_name
HAVING AVG(attendance_pct) < 75
ORDER BY attendance;
