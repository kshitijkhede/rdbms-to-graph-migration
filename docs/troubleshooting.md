# Troubleshooting Guide

## Common Issues and Solutions

### Connection Issues

#### Unable to Connect to Source Database

**Symptoms**:
- "Connection refused" error
- "Access denied" error
- Timeout errors

**Solutions**:

1. **Check database is running**:
   ```bash
   # MySQL
   systemctl status mysql
   
   # PostgreSQL
   systemctl status postgresql
   ```

2. **Verify connection details**:
   - Check host, port, username, password in config file
   - Try connecting with database client
   
3. **Check firewall settings**:
   ```bash
   # Allow MySQL port
   sudo ufw allow 3306
   
   # Allow PostgreSQL port
   sudo ufw allow 5432
   ```

4. **Test connection**:
   ```bash
   python -m src.cli test-connection --config config/migration_config.yml --type source
   ```

#### Unable to Connect to Neo4j

**Symptoms**:
- "ServiceUnavailable" error
- Authentication failed

**Solutions**:

1. **Check Neo4j is running**:
   ```bash
   systemctl status neo4j
   ```

2. **Verify URI format**:
   - Correct: `bolt://localhost:7687`
   - Incorrect: `http://localhost:7687`

3. **Check credentials**:
   - Default username: `neo4j`
   - Change password on first login

4. **Check bolt connector enabled**:
   In `neo4j.conf`:
   ```
   dbms.connector.bolt.enabled=true
   dbms.connector.bolt.listen_address=:7687
   ```

### Migration Issues

#### Out of Memory Errors

**Symptoms**:
- `MemoryError` during migration
- Process killed by OS

**Solutions**:

1. **Reduce batch size**:
   ```yaml
   migration:
     batch_size: 500  # Reduce from 1000
   ```

2. **Enable streaming mode** (if available):
   ```yaml
   migration:
     streaming: true
   ```

3. **Increase system memory**:
   - Allocate more RAM to VM
   - Close other applications

4. **Process tables separately**:
   ```bash
   python -m src.cli migrate --config config/migration_config.yml --tables users
   python -m src.cli migrate --config config/migration_config.yml --tables posts
   ```

#### Slow Migration Performance

**Symptoms**:
- Migration takes very long time
- Low CPU/memory utilization

**Solutions**:

1. **Increase batch size**:
   ```yaml
   migration:
     batch_size: 5000
   ```

2. **Increase parallelism**:
   ```yaml
   migration:
     max_workers: 8
   ```

3. **Create indexes after migration**:
   ```yaml
   migration:
     create_indexes: false
   ```
   Then create indexes manually after data load.

4. **Use APOC procedures** (if available):
   Install APOC plugin in Neo4j for bulk loading.

#### Foreign Key Constraint Violations

**Symptoms**:
- Relationships not created
- "Node not found" errors

**Solutions**:

1. **Load tables in dependency order**:
   - Parent tables first
   - Child tables later

2. **Check for orphaned foreign keys**:
   ```sql
   SELECT * FROM child_table c
   LEFT JOIN parent_table p ON c.parent_id = p.id
   WHERE p.id IS NULL;
   ```

3. **Enable cascade options**:
   Ensure foreign keys have appropriate ON DELETE/UPDATE actions.

### Validation Issues

#### Row Count Mismatch

**Symptoms**:
- Source has more rows than target
- Validation fails

**Possible Causes and Solutions**:

1. **Incomplete migration**:
   - Check logs for errors during migration
   - Re-run migration

2. **Duplicate data**:
   - Check for duplicate primary keys
   - Clean source data

3. **Junction tables counted**:
   - Junction tables become relationships, not nodes
   - This is expected behavior

4. **Null foreign keys**:
   - Rows with NULL foreign keys don't create relationships
   - Check if this is expected

#### Data Type Conversion Errors

**Symptoms**:
- "Invalid property value" errors
- Date/time conversion failures

**Solutions**:

1. **Check data type mapping**:
   Review `convert_sql_type_to_graph_type()` in helpers.py

2. **Custom type conversion**:
   Extend `GraphTransformer._convert_value()` method

3. **Handle NULL values**:
   Ensure NULL handling is appropriate for your data

### Neo4j Specific Issues

#### Heap Size Errors

**Symptoms**:
- "Java heap space" error
- Neo4j crashes during load

**Solutions**:

1. **Increase Neo4j heap size**:
   In `neo4j.conf`:
   ```
   dbms.memory.heap.initial_size=2g
   dbms.memory.heap.max_size=4g
   ```

2. **Adjust page cache**:
   ```
   dbms.memory.pagecache.size=2g
   ```

#### Transaction Size Limits

**Symptoms**:
- "Transaction timeout" errors
- "Transaction too large" errors

**Solutions**:

1. **Reduce batch size**:
   ```yaml
   migration:
     batch_size: 500
   ```

2. **Increase transaction timeout**:
   In `neo4j.conf`:
   ```
   dbms.transaction.timeout=300s
   ```

### Configuration Issues

#### Invalid YAML Configuration

**Symptoms**:
- "Error parsing YAML" error
- Configuration validation fails

**Solutions**:

1. **Check YAML syntax**:
   - Use proper indentation (2 spaces)
   - Quote special characters
   - Validate with online YAML validator

2. **Verify required fields**:
   Ensure all required fields are present:
   ```yaml
   source:
     type: mysql
     host: localhost
     database: mydb
     username: user
     password: pass
   ```

3. **Use example config**:
   ```bash
   cp config/migration_config.example.yml config/migration_config.yml
   ```

#### Permission Issues

**Symptoms**:
- "Permission denied" when creating logs
- Cannot read configuration file

**Solutions**:

1. **Check file permissions**:
   ```bash
   chmod 644 config/migration_config.yml
   mkdir -p logs
   chmod 755 logs
   ```

2. **Run with appropriate user**:
   Don't run as root unless necessary

### Debugging Tips

#### Enable Debug Logging

```yaml
logging:
  level: DEBUG
  file: logs/migration_debug.log
```

#### Check Logs

```bash
# View logs in real-time
tail -f logs/migration.log

# Search for errors
grep -i error logs/migration.log

# View last 100 lines
tail -n 100 logs/migration.log
```

#### Dry Run First

Always test with dry run:
```bash
python -m src.cli migrate --config config/migration_config.yml --dry-run
```

#### Test with Small Dataset

Create a test database with subset of data:
```sql
CREATE DATABASE test_db;
INSERT INTO test_db.users SELECT * FROM production.users LIMIT 100;
```

#### Use Python Debugger

```python
import pdb; pdb.set_trace()
```

### Performance Monitoring

#### Monitor Resource Usage

```bash
# CPU and memory
htop

# Disk I/O
iotop

# Network
nethogs
```

#### Neo4j Monitoring

```cypher
// Check database stats
CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Store sizes')
YIELD attributes
RETURN attributes;

// Check active queries
CALL dbms.listQueries();
```

### Getting Help

1. **Check logs** in `logs/` directory
2. **Review documentation** in `docs/` folder
3. **Search issues** on GitHub
4. **Create issue** with:
   - Error messages
   - Configuration file
   - System information
   - Steps to reproduce

### Emergency Recovery

#### Rollback Migration

If migration fails partially:

1. **Clear Neo4j database**:
   ```cypher
   MATCH (n) DETACH DELETE n;
   ```

2. **Or drop and recreate database**:
   ```cypher
   CREATE OR REPLACE DATABASE mydb;
   ```

3. **Re-run migration**:
   ```bash
   python -m src.cli migrate --config config/migration_config.yml --clear-target
   ```

#### Backup Before Migration

Always backup before migrating:

```bash
# MySQL
mysqldump -u user -p database > backup.sql

# PostgreSQL
pg_dump -U user database > backup.sql

# Neo4j
neo4j-admin dump --database=neo4j --to=/backup/neo4j.dump
```

### Platform-Specific Issues

#### Windows

- Use forward slashes in paths: `logs/migration.log`
- ODBC driver required for SQL Server
- May need to run as Administrator

#### macOS

- Homebrew packages may need linking
- Use `localhost` instead of `127.0.0.1`
- Check SSL certificate issues

#### Linux

- Install database client libraries:
  ```bash
  sudo apt-get install libmysqlclient-dev
  sudo apt-get install postgresql-client
  ```
- Check SELinux if enabled
- Verify systemd services

## Still Having Issues?

If these solutions don't resolve your issue:

1. Enable DEBUG logging
2. Collect error messages and logs
3. Document steps to reproduce
4. Open an issue on GitHub with all details
