# MySQL Password Reset and Setup Guide

## Problem: Cannot Access MySQL

If you get `ERROR 1045 (28000): Access denied`, it means MySQL requires a password but you don't know it.

## Solution: Reset MySQL Root Password

### Method 1: Stop MySQL and Reset (Recommended)

**Step 1: Stop MySQL**
```bash
sudo systemctl stop mysql
```

**Step 2: Start MySQL in Safe Mode (skip grant tables)**
```bash
sudo mkdir -p /var/run/mysqld
sudo chown mysql:mysql /var/run/mysqld
sudo mysqld_safe --skip-grant-tables &
```

**Step 3: Connect to MySQL (no password needed in safe mode)**
```bash
mysql -u root
```

**Step 4: Reset the root password**
```sql
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'migration123';
FLUSH PRIVILEGES;
EXIT;
```

**Step 5: Kill the safe mode process and restart MySQL normally**
```bash
sudo pkill mysqld
sudo systemctl start mysql
```

**Step 6: Test the new password**
```bash
mysql -u root -p
# Enter password: migration123
```

---

### Method 2: Use mysqladmin (If you remember the old password)

```bash
mysqladmin -u root -p password 'migration123'
# Enter OLD password when prompted
```

---

### Method 3: Reconfigure MySQL Package

```bash
sudo dpkg-reconfigure mysql-server
```

---

## After Resetting Password

### Create Migration User

```bash
# Login with root
mysql -u root -p
# Password: migration123
```

Inside MySQL:
```sql
-- Create dedicated migration user
CREATE USER 'migration'@'localhost' IDENTIFIED BY 'migration123';

-- Grant all privileges
GRANT ALL PRIVILEGES ON *.* TO 'migration'@'localhost' WITH GRANT OPTION;

-- Verify
FLUSH PRIVILEGES;
SELECT User, Host FROM mysql.user WHERE User IN ('root', 'migration');

EXIT;
```

### Test the migration user
```bash
mysql -u migration -p
# Password: migration123
```

---

## Update Your Project Configuration

Edit `config/config.py`:
```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'migration',
    'password': 'migration123',
    'database': 'migration_source_ecommerce',
}
```

---

## Load Sample Data

```bash
cd /home/student/DBMS/Project/rdbms-to-graph-migration
mysql -u migration -p < sql_schemas/ecommerce_schema.sql
```

---

## Quick Commands Reference

```bash
# Check MySQL status
sudo systemctl status mysql

# Start MySQL
sudo systemctl start mysql

# Stop MySQL
sudo systemctl stop mysql

# Restart MySQL
sudo systemctl restart mysql

# Login to MySQL
mysql -u migration -p

# Show databases
mysql -u migration -p -e "SHOW DATABASES;"

# Show users
mysql -u root -p -e "SELECT User, Host FROM mysql.user;"
```

---

## Troubleshooting

### Error: "Can't connect to local MySQL server through socket"
```bash
sudo systemctl start mysql
```

### Error: "Access denied"
- Follow the password reset steps above
- Make sure you're using the correct username and password

### Error: "Unknown database"
- Load the schema first: `mysql -u migration -p < sql_schemas/ecommerce_schema.sql`

---

## Security Note

For production systems:
- Use strong passwords (not 'migration123')
- Create separate users with limited privileges
- Don't use root for applications
- Restrict network access

For this educational project, 'migration123' is fine for local development.
