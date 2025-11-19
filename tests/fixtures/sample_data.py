"""Test fixtures and sample data."""

# Sample MySQL schema SQL
MYSQL_SAMPLE_SCHEMA = """
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE tags (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE post_tags (
    post_id INT,
    tag_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
"""

# Sample data
SAMPLE_USERS = [
    {'id': 1, 'name': 'Alice Smith', 'email': 'alice@example.com'},
    {'id': 2, 'name': 'Bob Jones', 'email': 'bob@example.com'},
    {'id': 3, 'name': 'Charlie Brown', 'email': 'charlie@example.com'}
]

SAMPLE_POSTS = [
    {'id': 1, 'user_id': 1, 'title': 'First Post', 'content': 'Hello World'},
    {'id': 2, 'user_id': 1, 'title': 'Second Post', 'content': 'More content'},
    {'id': 3, 'user_id': 2, 'title': 'Bob Post', 'content': 'Bob content'}
]
