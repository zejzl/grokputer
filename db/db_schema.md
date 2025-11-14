# Grokputer Database Schema Documentation

## Overview

Grokputer uses a hybrid Redis + SQLite database architecture for optimal performance and persistence. This document details all database schemas, tables, and their purposes.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│     Redis       │    │     SQLite      │
│  (Fast Cache)   │    │ (Persistence)   │
│                 │    │                 │
│ • Active convos │    │ • All history   │
│ • User sessions │    │ • Analytics     │
│ • Preferences   │    │ • Messages      │
│ • Real-time     │    │ • Long-term     │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┘
              Hybrid Manager
```

## SQLite Tables

### Core Tables

#### `swarm_rolls`
**Purpose**: Store dice roll results from multi-agent simulations
**Primary Use**: Analytics and testing data

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique roll ID |
| agent_name | TEXT | NOT NULL | Name of the agent (Alice, Bob, etc.) |
| roll_number | INTEGER | NOT NULL | Sequential roll number per agent |
| notation | TEXT | NOT NULL | Dice notation (e.g., '3d6+2') |
| individual_rolls | TEXT | NOT NULL | JSON array of individual die results |
| total | INTEGER | NOT NULL | Total result after modifiers |
| modifier | INTEGER | DEFAULT 0 | Modifier applied to roll |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | When roll was made |

**Indexes**:
- Primary key on `id`
- Implicit indexes on unique constraints

**Sample Data**:
```sql
-- Agent Alice's rolls
INSERT INTO swarm_rolls (agent_name, roll_number, notation, individual_rolls, total, modifier)
VALUES ('Alice', 1, '12d18', '[15,7,12,9,4,16,3,11,14,8,2,13]', 114, 0);
```

#### `dnd_characters`
**Purpose**: Store D&D character stats derived from dice rolls
**Status**: Legacy table with foreign key issues

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| agent_name | TEXT | PRIMARY KEY | Character/agent name |
| STR | INTEGER | NOT NULL | Strength score |
| DEX | INTEGER | NOT NULL | Dexterity score |
| CON | INTEGER | NOT NULL | Constitution score |
| INT_ | INTEGER | NOT NULL | Intelligence score (INT is SQL keyword) |
| WIS | INTEGER | NOT NULL | Wisdom score |
| CHA | INTEGER | NOT NULL | Charisma score |

**Note**: Has foreign key constraint to `swarm_rolls(agent_name)` which may cause issues.

### Natural Language Interface (NLI) Tables

#### `conversations`
**Purpose**: Track conversation sessions and metadata
**Primary Use**: Conversation management and analytics

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Internal ID |
| conversation_id | TEXT | UNIQUE NOT NULL | Public conversation identifier |
| user_id | TEXT | NOT NULL | User who started conversation |
| start_time | DATETIME | DEFAULT CURRENT_TIMESTAMP | When conversation began |
| end_time | DATETIME | NULL | When conversation ended |
| status | TEXT | DEFAULT 'active' | active, completed, archived |
| total_messages | INTEGER | DEFAULT 0 | Total messages in conversation |
| last_activity | DATETIME | DEFAULT CURRENT_TIMESTAMP | Last message timestamp |
| metadata | TEXT | NULL | JSON: preferences, context_variables |

**Indexes**:
- `idx_conversations_user_id` on `user_id`
- `idx_conversations_status` on `status`
- Primary key on `id`
- Unique on `conversation_id`

#### `conversation_messages`
**Purpose**: Store all messages in conversations
**Primary Use**: Message history and context reconstruction

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Internal ID |
| conversation_id | TEXT | NOT NULL | Links to conversations table |
| message_id | TEXT | UNIQUE NOT NULL | Unique message identifier |
| role | TEXT | NOT NULL | user, assistant, system |
| content | TEXT | NOT NULL | Message text content |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | When message was sent |
| metadata | TEXT | NULL | JSON: intent, task_data, etc. |

**Indexes**:
- `idx_messages_conversation_id` on `conversation_id`
- `idx_messages_timestamp` on `timestamp DESC`
- Foreign key to `conversations(conversation_id)` with CASCADE delete

#### `user_preferences`
**Purpose**: Store learned user preferences for personalization
**Primary Use**: NLI personalization and DPO training

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Internal ID |
| user_id | TEXT | NOT NULL | User identifier |
| preference_key | TEXT | NOT NULL | Preference name (e.g., 'response_style') |
| preference_value | TEXT | NOT NULL | Preference value (e.g., 'concise') |
| confidence | REAL | DEFAULT 1.0 | How confident we are (0.0-1.0) |
| last_updated | DATETIME | DEFAULT CURRENT_TIMESTAMP | When preference was updated |
| source | TEXT | DEFAULT 'nli' | How preference was learned |

**Indexes**:
- `idx_preferences_user_id` on `user_id`
- Unique constraint on `(user_id, preference_key)`

#### `conversation_analytics`
**Purpose**: Track conversation performance metrics
**Primary Use**: Analytics and continuous improvement

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Internal ID |
| conversation_id | TEXT | NOT NULL | Links to conversations table |
| user_id | TEXT | NOT NULL | User who had conversation |
| metric_name | TEXT | NOT NULL | Metric type (response_time, task_success, etc.) |
| metric_value | REAL | NOT NULL | Numeric metric value |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | When metric was recorded |
| metadata | TEXT | NULL | JSON: additional context |

**Indexes**:
- `idx_analytics_conversation_id` on `conversation_id`
- `idx_analytics_user_id` on `user_id`
- `idx_analytics_metric` on `metric_name`
- Foreign key to `conversations(conversation_id)` with CASCADE delete

### Testing and Monitoring Tables

#### `selenium_tests`
**Purpose**: Store results from Selenium browser automation tests
**Primary Use**: Web testing and performance monitoring

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Test run ID |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | When test ran |
| url | TEXT | NOT NULL | URL that was tested |
| load_time | REAL | NOT NULL | Page load time in seconds |
| passed | BOOLEAN | NOT NULL | Whether test passed |
| screenshot_size | INTEGER | NULL | Size of screenshot in bytes |
| total_time | REAL | NULL | Total test execution time |
| notes | TEXT | NULL | Additional test notes |

**Indexes**:
- `idx_selenium_timestamp` on `timestamp DESC`

#### `agent_events`
**Purpose**: Log events from agent operations
**Primary Use**: Debugging and monitoring agent behavior

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Event ID |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP | When event occurred |
| agent_type | TEXT | NOT NULL | Type of agent (observer, actor, etc.) |
| event_type | TEXT | NOT NULL | Event type (task_started, error, etc.) |
| payload | TEXT | NULL | JSON event data |
| status | TEXT | DEFAULT 'success' | success, error, warning |

**Indexes**:
- `idx_agent_timestamp` on `timestamp DESC`
- `idx_agent_type` on `agent_type`

## Redis Cache Structure

### Conversation Cache Keys

#### `conv:{conversation_id}`
**Type**: Hash
**TTL**: 24 hours
**Purpose**: Active conversation metadata

**Fields**:
- `conversation_id`: Unique identifier
- `user_id`: User who owns conversation
- `start_time`: ISO timestamp
- `status`: active, completed, etc.
- `total_messages`: Message count
- `metadata`: JSON string
- `context_variables`: JSON string
- `conversation_state`: Current state
- `last_intent`: Last parsed intent

#### `conv:{conversation_id}:messages`
**Type**: Sorted Set (by timestamp)
**TTL**: 24 hours
**Purpose**: Recent message buffer (last 20 messages)

**Members**: JSON strings containing:
```json
{
  "message_id": "msg_123",
  "role": "user",
  "content": "Hello",
  "timestamp": "2025-11-12T12:00:00",
  "metadata": {"intent": "greeting"}
}
```

#### `user:{user_id}:prefs`
**Type**: Hash
**TTL**: 1 hour
**Purpose**: Cached user preferences

**Fields**: Dynamic preference keys with values

## Database Configuration

### SQLite Settings (db_config.py)
- **WAL Mode**: Enabled for concurrency
- **Foreign Keys**: Enabled
- **Synchronous**: NORMAL (balance speed/safety)
- **Connection**: Context manager with automatic commit/rollback

### Redis Settings
- **URL**: `redis://localhost:6379` (configurable)
- **TTL**: 24 hours for conversations, 1 hour for preferences
- **Codec**: JSON for complex data structures
- **Connection**: Async client with automatic reconnection

## Data Flow Architecture

### Message Storage Flow
```
User Message
    ↓
NLI Processing (intent, context)
    ↓
Redis Cache (immediate storage)
    ↓
SQLite Persistence (long-term)
    ↓
Analytics Recording
    ↓
DPO Training (preference learning)
```

### Conversation Lifecycle
```
Create Conversation → Redis Cache
    ↓
Exchange Messages → Cache + SQLite
    ↓
End Conversation → Mark complete
    ↓
Archive Old → Cleanup policy
```

## Query Examples

### Recent Conversations
```sql
SELECT conversation_id, user_id, total_messages, last_activity
FROM conversations
WHERE user_id = ?
ORDER BY last_activity DESC
LIMIT 10;
```

### Message History
```sql
SELECT role, content, timestamp, metadata
FROM conversation_messages
WHERE conversation_id = ?
ORDER BY timestamp ASC;
```

### User Preferences
```sql
SELECT preference_key, preference_value, confidence
FROM user_preferences
WHERE user_id = ?
ORDER BY confidence DESC;
```

### Analytics Summary
```sql
SELECT metric_name, AVG(metric_value) as avg_value, COUNT(*) as count
FROM conversation_analytics
WHERE user_id = ?
GROUP BY metric_name;
```

## Maintenance

### Cleanup Policies
- **Active Conversations**: Keep in Redis for 24 hours
- **Completed Conversations**: Archive after 30 days
- **Old Messages**: Keep last 1000 per conversation
- **Analytics**: Aggregate and archive after 90 days

### Backup Strategy
- **SQLite**: Daily automated backups
- **Redis**: RDB snapshots for memory state
- **Combined**: Full conversation export weekly

## Performance Optimizations

### Indexes
- All foreign keys indexed
- Timestamp columns indexed for time-based queries
- User IDs indexed for personalization queries
- Composite indexes on common query patterns

### Caching Strategy
- **Hot Data**: Active conversations in Redis
- **Warm Data**: Recent conversations in SQLite with indexes
- **Cold Data**: Archived conversations compressed

### Connection Pooling
- SQLite: Single-writer, multi-reader with WAL
- Redis: Async connection pool with automatic failover

## Migration Notes

### From In-Memory to Persistent
- All conversations now persist across restarts
- Message history maintained indefinitely
- User preferences learned and retained
- Analytics available for continuous improvement

### Schema Evolution
- Tables use `IF NOT EXISTS` for safe updates
- Foreign keys with CASCADE for data integrity
- Indexes added incrementally for performance

## Future Enhancements

### Planned Features
- **Vector Embeddings**: Message similarity search
- **Conversation Summaries**: AI-generated conversation summaries
- **Multi-modal Storage**: Images, files, and rich media
- **Federated Learning**: Cross-user preference aggregation
- **Real-time Analytics**: Live dashboards and monitoring

---

**Last Updated**: November 12, 2025
**Database Version**: 2.0 (NLI Integration)
**Total Tables**: 9
