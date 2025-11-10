-- Swarm Dice Rolls Database
-- Created: 2024-11-09
-- Schema for storing agent names and dice rolls from simulation
-- Run with: sqlite3 db.sql or import to PostgreSQL/MySQL

CREATE TABLE IF NOT EXISTS swarm_rolls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    roll_number INTEGER NOT NULL,
    notation TEXT NOT NULL,
    individual_rolls TEXT NOT NULL,  -- JSON-like string: '[3,5]'
    total INTEGER NOT NULL,
    modifier INTEGER DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sample Data from Swarm Simulation (12 Agents, 3 Rolls Each)

-- Agent Alice
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Alice', 1, '12d18', '[15,7,12,9,4,16,3,11,14,8,2,13]', 114, 0),
('Alice', 2, '7d15+3', '[10,5,12,8,14,2,11]', 65, 3),
('Alice', 3, '3d6-1', '[4,1,6]', 10, -1);

-- Agent Bob
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Bob', 1, '18d7', '[3,5,2,6,1,4,7,3,5,2,6,1,4,7,3,5,2,6]', 81, 0),
('Bob', 2, '1d3', '[2]', 2, 0),
('Bob', 3, '15d20+4', '[18,12,5,9,16,3,11,7,14,19,8,2,13,6,10]', 157, 4);

-- Agent Charlie
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Charlie', 1, '9d10-2', '[7,4,9,2,8,5,1,6,3]', 43, -2),
('Charlie', 2, '20d4', '[2,1,3,4,2,1,3,4,2,1,3,4,2,1,3,4,2,1,3,4]', 50, 0),
('Charlie', 3, '4d19+1', '[12,15,8,17]', 53, 1);

-- Agent Diana
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Diana', 1, '16d9', '[5,8,2,7,4,1,6,3,9,5,8,2,7,4,1,6]', 78, 0),
('Diana', 2, '2d5-3', '[3,1]', 1, -3),
('Diana', 3, '11d16', '[10,14,7,12,3,15,8,5,11,9,4]', 98, 0);

-- Agent Eve
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Eve', 1, '6d12+2', '[9,5,11,3,7,8]', 45, 2),
('Eve', 2, '13d3', '[2,1,3,2,1,3,2,1,3,2,1,3,2]', 29, 0),
('Eve', 3, '8d11-1', '[6,9,4,10,2,7,5,8]', 50, -1);

-- Agent Frank (Sample varied rolls)
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Frank', 1, '5d20', '[15,8,19,3,12]', 57, 0),
('Frank', 2, '10d6+1', '[4,2,6,5,1,3,4,5,6,2]', 38, 1),
('Frank', 3, '2d12-2', '[10,7]', 15, -2);

-- Agent Grace
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Grace', 1, '14d8', '[5,3,7,2,6,4,8,1,5,3,7,2,6,4]', 63, 0),
('Grace', 2, '1d20+5', '[14]', 19, 5),
('Grace', 3, '19d5-3', '[3,1,4,2,5,3,1,4,2,5,3,1,4,2,5,3,1,4,2]', 58, -3);

-- Agent Henry
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Henry', 1, '4d3', '[2,1,3,2]', 8, 0),
('Henry', 2, '17d19+2', '[12,16,9,18,5,14,11,7,15,13,8,17,6,10,4,19,2]', 188, 2),
('Henry', 3, '9d7-1', '[4,6,2,5,3,7,1,4,6]', 35, -1);

-- Agent Ivy
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Ivy', 1, '11d10', '[8,3,9,5,2,7,1,6,4,10,8]', 63, 0),
('Ivy', 2, '3d20+4', '[13,18,7]', 42, 4),
('Ivy', 3, '15d4-2', '[3,2,4,1,3,2,4,1,3,2,4,1,3,2,4]', 40, -2);

-- Agent Jack
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Jack', 1, '20d20', '[10,15,5,18,12,8,16,3,19,7,14,11,9,6,17,4,13,2,1,20]', 190, 0),
('Jack', 2, '6d5', '[4,2,5,3,1,4]', 19, 0),
('Jack', 3, '8d16+3', '[12,9,14,5,11,7,15,8]', 81, 3);

-- Agent Kara
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Kara', 1, '7d9-4', '[6,8,3,7,2,9,5]', 28, -4),
('Kara', 2, '2d3+1', '[3,2]', 6, 1),
('Kara', 3, '16d12', '[11,7,14,4,9,5,13,8,10,6,15,3,12,2,1,16]', 136, 0);

-- Agent Leo
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier) VALUES
('Leo', 1, '10d19+5', '[13,8,16,4,17,11,9,14,2,18]', 112, 5),
('Leo', 2, '4d6', '[5,3,6,2]', 16, 0),
('Leo', 3, '18d8-2', '[7,4,8,3,6,5,2,1,7,4,8,3,6,5,2,1,7,4]', 83, -2);

-- Query Examples
-- SELECT * FROM swarm_rolls WHERE agent_name = 'Alice';
-- SELECT AVG(total) FROM swarm_rolls GROUP BY agent_name;
-- SELECT * FROM swarm_rolls ORDER BY total DESC LIMIT 5;  -- Highest rolls