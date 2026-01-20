-- Script de création de base de données OWASP ZAP
-- Compatible MySQL/MariaDB et PostgreSQL

-- ==============================================
-- CRÉATION DE LA BASE DE DONNÉES
-- ==============================================

-- Pour MySQL/MariaDB :
CREATE DATABASE IF NOT EXISTS owasp_zap 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Pour PostgreSQL (décommentez si nécessaire) :
-- CREATE DATABASE owasp_zap WITH ENCODING 'UTF8';

USE owasp_zap;

-- ==============================================
-- CRÉATION DE L'UTILISATEUR DÉDIÉ
-- ==============================================

-- Pour MySQL/MariaDB :
CREATE USER IF NOT EXISTS 'zap_user'@'%' IDENTIFIED BY 'SecurePassword123!';
GRANT ALL PRIVILEGES ON owasp_zap.* TO 'zap_user'@'%';

-- Pour PostgreSQL (décommentez si nécessaire) :
-- CREATE USER zap_user WITH PASSWORD 'SecurePassword123!';
-- GRANT ALL PRIVILEGES ON DATABASE owasp_zap TO zap_user;

-- ==============================================
-- TABLES PRINCIPALES
-- ==============================================

-- Table des projets de scan
CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    target_url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status ENUM('active', 'completed', 'archived') DEFAULT 'active',
    INDEX idx_name (name),
    INDEX idx_status (status)
);

-- Table des sessions de scan
CREATE TABLE scan_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    session_name VARCHAR(255) NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    duration_seconds INT DEFAULT 0,
    status ENUM('running', 'completed', 'failed', 'cancelled') DEFAULT 'running',
    scan_type ENUM('active', 'passive', 'spider', 'ajax_spider', 'full') DEFAULT 'passive',
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_project (project_id),
    INDEX idx_status (status),
    INDEX idx_scan_type (scan_type)
);

-- Table des vulnérabilités détectées
CREATE TABLE vulnerabilities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    alert_id INT NOT NULL,
    name VARCHAR(500) NOT NULL,
    risk_level ENUM('High', 'Medium', 'Low', 'Informational') NOT NULL,
    confidence ENUM('High', 'Medium', 'Low') NOT NULL,
    url VARCHAR(1000) NOT NULL,
    method VARCHAR(10) DEFAULT 'GET',
    parameter_name VARCHAR(255),
    attack_vector TEXT,
    evidence TEXT,
    description TEXT,
    solution TEXT,
    reference TEXT,
    cwe_id INT,
    wasc_id INT,
    source_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_risk (risk_level),
    INDEX idx_confidence (confidence),
    INDEX idx_cwe (cwe_id),
    INDEX idx_url (url(255))
);

-- Table des URLs découvertes
CREATE TABLE discovered_urls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    url VARCHAR(1000) NOT NULL,
    method VARCHAR(10) DEFAULT 'GET',
    status_code INT,
    response_time_ms INT,
    content_type VARCHAR(100),
    content_length INT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_session_url_method (session_id, url(500), method),
    INDEX idx_session (session_id),
    INDEX idx_status_code (status_code),
    INDEX idx_method (method)
);

-- Table des rapports générés
CREATE TABLE reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    report_type ENUM('HTML', 'XML', 'JSON', 'PDF') NOT NULL,
    file_path VARCHAR(500),
    file_size_bytes INT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    generated_by VARCHAR(100),
    FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE CASCADE,
    INDEX idx_session (session_id),
    INDEX idx_type (report_type)
);

-- Table de configuration
CREATE TABLE zap_configuration (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_key (config_key)
);

-- Table des logs d'activité
CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    severity ENUM('INFO', 'WARNING', 'ERROR', 'DEBUG') DEFAULT 'INFO',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent VARCHAR(500),
    ip_address VARCHAR(45),
    FOREIGN KEY (session_id) REFERENCES scan_sessions(id) ON DELETE SET NULL,
    INDEX idx_session (session_id),
    INDEX idx_action (action),
    INDEX idx_severity (severity),
    INDEX idx_timestamp (timestamp)
);

-- ==============================================
-- VUES UTILES
-- ==============================================

-- Vue résumé des vulnérabilités par projet
CREATE VIEW vulnerability_summary AS
SELECT 
    p.name as project_name,
    s.session_name,
    v.risk_level,
    COUNT(*) as vulnerability_count,
    COUNT(DISTINCT v.url) as affected_urls
FROM vulnerabilities v
JOIN scan_sessions s ON v.session_id = s.id
JOIN projects p ON s.project_id = p.id
GROUP BY p.id, s.id, v.risk_level;

-- Vue des sessions actives
CREATE VIEW active_sessions AS
SELECT 
    s.id,
    s.session_name,
    p.name as project_name,
    s.start_time,
    TIMESTAMPDIFF(MINUTE, s.start_time, NOW()) as duration_minutes,
    s.scan_type,
    COUNT(v.id) as vulnerabilities_found
FROM scan_sessions s
JOIN projects p ON s.project_id = p.id
LEFT JOIN vulnerabilities v ON s.id = v.session_id
WHERE s.status = 'running'
GROUP BY s.id;

-- ==============================================
-- DONNÉES D'INITIALISATION
-- ==============================================

-- Configuration par défaut
INSERT INTO zap_configuration (config_key, config_value, description) VALUES
('max_scan_duration', '7200', 'Durée maximale d\'un scan en secondes (2h)'),
('default_scan_type', 'passive', 'Type de scan par défaut'),
('report_retention_days', '90', 'Nombre de jours de rétention des rapports'),
('max_concurrent_scans', '3', 'Nombre maximum de scans simultanés'),
('api_key_expiry_days', '30', 'Durée de validité des clés API en jours');

-- ==============================================
-- PROCÉDURES STOCKÉES
-- ==============================================

DELIMITER //

-- Procédure pour nettoyer les anciennes données
CREATE PROCEDURE CleanOldData(IN retention_days INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    
    -- Supprimer les sessions terminées anciennes
    DELETE FROM scan_sessions 
    WHERE status IN ('completed', 'failed', 'cancelled') 
    AND end_time < DATE_SUB(NOW(), INTERVAL retention_days DAY);
    
    -- Supprimer les logs anciens
    DELETE FROM activity_logs 
    WHERE timestamp < DATE_SUB(NOW(), INTERVAL retention_days DAY);
    
    COMMIT;
END//

-- Procédure pour obtenir les statistiques d'un projet
CREATE PROCEDURE GetProjectStats(IN project_id INT)
BEGIN
    SELECT 
        p.name as project_name,
        COUNT(DISTINCT s.id) as total_sessions,
        COUNT(CASE WHEN s.status = 'completed' THEN 1 END) as completed_sessions,
        COUNT(DISTINCT v.id) as total_vulnerabilities,
        COUNT(CASE WHEN v.risk_level = 'High' THEN 1 END) as high_risk_vulns,
        COUNT(CASE WHEN v.risk_level = 'Medium' THEN 1 END) as medium_risk_vulns,
        COUNT(CASE WHEN v.risk_level = 'Low' THEN 1 END) as low_risk_vulns,
        MAX(s.end_time) as last_scan_date
    FROM projects p
    LEFT JOIN scan_sessions s ON p.id = s.project_id
    LEFT JOIN vulnerabilities v ON s.id = v.session_id
    WHERE p.id = project_id
    GROUP BY p.id;
END//

DELIMITER ;

-- ==============================================
-- INDEX SUPPLÉMENTAIRES POUR PERFORMANCE
-- ==============================================

-- Index composites pour les requêtes fréquentes
CREATE INDEX idx_vuln_session_risk ON vulnerabilities(session_id, risk_level);
CREATE INDEX idx_session_project_status ON scan_sessions(project_id, status);
CREATE INDEX idx_activity_timestamp_severity ON activity_logs(timestamp DESC, severity);

-- ==============================================
-- PERMISSIONS FINALES
-- ==============================================

FLUSH PRIVILEGES;

-- Message de confirmation
SELECT 'Base de données OWASP ZAP créée avec succès!' as status;

