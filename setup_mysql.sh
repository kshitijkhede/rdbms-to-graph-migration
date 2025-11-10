#!/bin/bash
# MySQL Setup Script for Migration Engine

echo "=========================================="
echo "  MySQL Setup for Migration Engine"
echo "=========================================="
echo ""

echo "Step 1: Setting up MySQL user with password authentication"
echo "-----------------------------------------------------------"
echo ""
echo "We'll create a dedicated user for the migration engine."
echo "This is more secure than using the root account."
echo ""

# Prompt for password
read -sp "Enter a password for the migration user (e.g., migration123): " MYSQL_PASSWORD
echo ""

# Connect to MySQL and set up user
sudo mysql << EOF
-- Create migration user with password
CREATE USER IF NOT EXISTS 'migration'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';

-- Grant all privileges (needed for creating databases and tables)
GRANT ALL PRIVILEGES ON *.* TO 'migration'@'localhost';

-- Also set up root with password (if you want)
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$MYSQL_PASSWORD';

-- Apply changes
FLUSH PRIVILEGES;

-- Show users
SELECT User, Host, plugin FROM mysql.user WHERE User IN ('root', 'migration');
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  ✓ MySQL Setup Complete!"
    echo "=========================================="
    echo ""
    echo "User 'migration' created successfully!"
    echo "Password: $MYSQL_PASSWORD"
    echo ""
    echo "Next steps:"
    echo "1. Update config/config.py with these credentials:"
    echo "   'user': 'migration'"
    echo "   'password': '$MYSQL_PASSWORD'"
    echo ""
    echo "2. Test the connection:"
    echo "   mysql -u migration -p"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "  ✗ Setup Failed"
    echo "=========================================="
    echo ""
    echo "Please try running commands manually."
fi
