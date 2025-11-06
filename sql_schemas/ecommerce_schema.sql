-- ===============================================
-- E-Commerce Sample Schema
-- Demonstrates: AGGREGATION Pattern
-- ===============================================
-- This schema models an aggregation (or composition) relationship.
-- An Order is an aggregate, and Order_Items are part of that aggregate.
-- The Order_Items table, with its composite key, is the critical pattern to detect.

CREATE DATABASE IF NOT EXISTS migration_source_ecommerce;
USE migration_source_ecommerce;

-- Entity Table: Customers
CREATE TABLE Customers (
    customer_id VARCHAR(255) NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    PRIMARY KEY (customer_id)
);

-- Entity Table: Products
CREATE TABLE Products (
    product_id VARCHAR(255) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    PRIMARY KEY (product_id)
);

-- Entity Table: Orders (Aggregate Root)
CREATE TABLE Orders (
    order_id VARCHAR(255) NOT NULL,
    customer_id VARCHAR(255) NOT NULL,
    order_date DATE NOT NULL,
    PRIMARY KEY (order_id),
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);

-- Junction Table: Order_Items (Represents Aggregation)
CREATE TABLE Order_Items (
    order_id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    quantity INT NOT NULL,
    price_at_purchase DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id), -- Composite Primary Key
    FOREIGN KEY (order_id) REFERENCES Orders(order_id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);

-- Insert Sample Data
INSERT INTO Customers VALUES 
    ('C100', 'Customer A', 'a@example.com'), 
    ('C200', 'Customer B', 'b@example.com');

INSERT INTO Products VALUES 
    ('P1', 'Laptop', 1200.00, 'Electronics'), 
    ('P2', 'Mouse', 45.00, 'Electronics'), 
    ('P3', 'Book', 30.00, 'Books');

INSERT INTO Orders VALUES 
    ('O1000', 'C100', '2024-01-15'), 
    ('O2000', 'C200', '2024-01-17'),
    ('O3000', 'C100', '2024-01-20');

INSERT INTO Order_Items VALUES 
    ('O1000', 'P1', 1, 1200.00), 
    ('O1000', 'P2', 1, 45.00),
    ('O2000', 'P3', 2, 30.00),
    ('O3000', 'P2', 3, 45.00), 
    ('O3000', 'P3', 5, 30.00);
