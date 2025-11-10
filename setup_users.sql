-- MySQL User Setup Script
-- Run this after connecting to MySQL in safe mode

FLUSH PRIVILEGES;

-- Use a strong password that meets policy requirements
-- Password: Migration@123

-- Set root password
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Migration@123';

-- Create migration user
CREATE USER IF NOT EXISTS 'migration'@'localhost' IDENTIFIED BY 'Migration@123';

-- Grant privileges
GRANT ALL PRIVILEGES ON *.* TO 'migration'@'localhost' WITH GRANT OPTION;

-- Apply changes
FLUSH PRIVILEGES;

-- Show users
SELECT User, Host, plugin FROM mysql.user WHERE User IN ('root', 'migration');
