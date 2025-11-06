-- ===============================================
-- University Sample Schema
-- Demonstrates: INHERITANCE Pattern (Class Table Inheritance)
-- ===============================================
-- This schema models Class Table Inheritance (CTI).
-- A Person is the base entity. Student and Professor are specialized sub-types.
-- The key pattern is the 1-to-1 relationship where the child table's Primary Key 
-- is also a Foreign Key to the parent table.

CREATE DATABASE IF NOT EXISTS migration_source_university;
USE migration_source_university;

-- Base Entity Table
CREATE TABLE Person (
    person_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    PRIMARY KEY (person_id)
);

-- Sub-Type Table: Student
CREATE TABLE Student (
    person_id VARCHAR(255) NOT NULL, -- PK and FK
    major VARCHAR(255) NOT NULL,
    gpa DECIMAL(3, 2),
    PRIMARY KEY (person_id),
    FOREIGN KEY (person_id) REFERENCES Person(person_id)
);

-- Sub-Type Table: Professor
CREATE TABLE Professor (
    person_id VARCHAR(255) NOT NULL, -- PK and FK
    department VARCHAR(255) NOT NULL,
    title VARCHAR(100),
    PRIMARY KEY (person_id),
    FOREIGN KEY (person_id) REFERENCES Person(person_id)
);

-- A table for relationships
CREATE TABLE Enrolled_In (
    student_id VARCHAR(255) NOT NULL,
    course_code VARCHAR(100) NOT NULL,
    grade VARCHAR(2),
    PRIMARY KEY (student_id, course_code),
    FOREIGN KEY (student_id) REFERENCES Student(person_id)
);

-- Insert Sample Data
INSERT INTO Person VALUES 
    ('ID1', 'Alice', 'alice@uni.edu'), 
    ('ID2', 'Bob', 'bob@uni.edu'), 
    ('ID3', 'Charlie', 'charlie@uni.edu');

INSERT INTO Student VALUES 
    ('ID1', 'Computer Science', 3.9),
    ('ID3', 'Physics', 3.5);

INSERT INTO Professor VALUES 
    ('ID2', 'Computer Science', 'Full Professor');

INSERT INTO Enrolled_In VALUES 
    ('ID1', 'CS101', 'A'), 
    ('ID1', 'PHY300', 'B+'), 
    ('ID3', 'PHY300', 'A-');
