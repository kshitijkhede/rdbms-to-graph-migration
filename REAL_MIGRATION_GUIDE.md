# Real Database Migration - Quick Setup Guide

This guide will help you migrate a real MySQL/PostgreSQL database to Neo4j.

## 📋 Prerequisites

### 1. Install Required Databases

**MySQL** (if using MySQL as source):
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation

# macOS
brew install mysql
brew services start mysql
```

**PostgreSQL** (alternative to MySQL):
```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# macOS
brew install postgresql
brew services start postgresql
```

**Neo4j** (target database):
```bash
# Download Neo4j Community Edition from:
# https://neo4j.com/download/

# Or use Docker:
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

### 2. Verify Python Dependencies

```bash
cd /home/student/DBMS/final
source venv/bin/activate
pip install -r requirements.txt
```

## 🗄️ Setup Source Database

### Option A: Create Sample MySQL Database

```bash
# Login to MySQL
mysql -u root -p

# Create database and sample data
CREATE DATABASE university_db;
USE university_db;

-- Create tables
CREATE TABLE departments (
    department_id INT PRIMARY KEY AUTO_INCREMENT,
    department_name VARCHAR(100) NOT NULL,
    building VARCHAR(50)
);

CREATE TABLE students (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    enrollment_date DATE
);

CREATE TABLE courses (
    course_id INT PRIMARY KEY AUTO_INCREMENT,
    course_name VARCHAR(100) NOT NULL,
    credits INT,
    department_id INT,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE professors (
    professor_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    department_id INT,
    hire_date DATE,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE enrollments (
    student_id INT,
    course_id INT,
    enrollment_date DATE,
    grade VARCHAR(2),
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- Insert sample data
INSERT INTO departments (department_name, building) VALUES
    ('Computer Science', 'Engineering Hall'),
    ('Mathematics', 'Science Building'),
    ('Physics', 'Science Building');

INSERT INTO students (first_name, last_name, email, enrollment_date) VALUES
    ('John', 'Doe', 'john.doe@university.edu', '2023-09-01'),
    ('Jane', 'Smith', 'jane.smith@university.edu', '2023-09-01'),
    ('Bob', 'Johnson', 'bob.johnson@university.edu', '2023-09-01');

INSERT INTO courses (course_name, credits, department_id) VALUES
    ('Database Systems', 3, 1),
    ('Data Structures', 4, 1),
    ('Calculus I', 4, 2);

INSERT INTO professors (first_name, last_name, department_id, hire_date) VALUES
    ('Dr. Alice', 'Brown', 1, '2020-08-15'),
    ('Dr. Charlie', 'Davis', 2, '2019-01-10');

INSERT INTO enrollments (student_id, course_id, enrollment_date, grade) VALUES
    (1, 1, '2023-09-05', 'A'),
    (1, 2, '2023-09-05', 'B+'),
    (2, 1, '2023-09-05', 'A-'),
    (3, 3, '2023-09-05', 'B');
```

### Option B: Use Your Existing Database

Just update the credentials in `config/my_migration.yml`

## ⚙️ Configuration

Edit `config/my_migration.yml`:

```yaml
source:
  type: mysql
  host: localhost
  port: 3306
  database: university_db
  username: root
  password: YOUR_MYSQL_PASSWORD  # ⚠️ Change this!

target:
  neo4j:
    uri: bolt://localhost:7687
    username: neo4j
    password: YOUR_NEO4J_PASSWORD  # ⚠️ Change this!
    database: neo4j
```

## 🚀 Run Migration

### Step 1: Test Database Connections

```bash
# Test source database
python -m src.cli test-connection -c config/my_migration.yml -t source

# Test Neo4j connection
python -m src.cli test-connection -c config/my_migration.yml -t target
```

### Step 2: Analyze Schema

```bash
python -m src.cli analyze -c config/my_migration.yml -o schema_analysis.json
```

### Step 3: Perform Semantic Enrichment (Optional)

```bash
python -m src.cli enrich -c config/my_migration.yml -o conceptual_model.json
```

### Step 4: Run Full Migration with S→C→T

```bash
# This performs the complete migration with semantic enrichment
python -m src.cli migrate-sct -c config/my_migration.yml
```

**Or use the direct S→T migration (faster but less semantic information):**

```bash
python -m src.cli migrate -c config/my_migration.yml
```

### Step 5: Validate Results

```bash
python -m src.cli validate -c config/my_migration.yml --check-counts
```

## 🔍 Verify in Neo4j

Open Neo4j Browser: http://localhost:7474

Run these queries:

```cypher
// Count all nodes
MATCH (n) RETURN labels(n) as NodeType, count(n) as Count

// Count all relationships
MATCH ()-[r]->() RETURN type(r) as RelType, count(r) as Count

// View sample data
MATCH (s:Students)-[e:ENROLLED_IN]->(c:Courses)
RETURN s.firstName, s.lastName, c.courseName
LIMIT 10

// View complete graph
MATCH (n) RETURN n LIMIT 50
```

## 📊 Migration Options

### Dry Run (No Data Migration)
```bash
python -m src.cli migrate-sct -c config/my_migration.yml --dry-run
```

### Migrate Specific Tables
```bash
python -m src.cli migrate-sct -c config/my_migration.yml -t students,courses
```

### Clear Neo4j Before Migration
```bash
python -m src.cli migrate-sct -c config/my_migration.yml --clear-target
```

## 🐛 Troubleshooting

### Connection Issues

**MySQL Connection Failed:**
```bash
# Check MySQL is running
sudo systemctl status mysql

# Test connection manually
mysql -u root -p -h localhost university_db
```

**Neo4j Connection Failed:**
```bash
# Check Neo4j is running
# For Docker:
docker ps | grep neo4j

# Access Neo4j browser:
open http://localhost:7474
```

### Permission Issues

```bash
# Grant MySQL permissions
mysql -u root -p
GRANT ALL PRIVILEGES ON university_db.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

## 📝 Logs

Check migration logs at:
```bash
cat logs/migration.log
```

## 🎯 Next Steps

After successful migration:
1. Explore your graph in Neo4j Browser
2. Run analytics queries
3. Create custom indexes for performance
4. Set up graph algorithms (PageRank, Community Detection, etc.)

## 💡 Tips

- Start with a **small dataset** to test
- Use **--dry-run** first to verify schema mapping
- Check **logs/** directory for detailed information
- Use **semantic enrichment (S→C→T)** for better relationship names
- Enable **indexes** in configuration for better Neo4j performance

## 📚 Documentation

- Full API: `docs/api_reference.md`
- S→C→T Architecture: `docs/semantic_enrichment.md`
- Troubleshooting: `docs/troubleshooting.md`
