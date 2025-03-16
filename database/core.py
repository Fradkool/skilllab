"""
Core database functionality for SkillLab
Provides base classes and utilities for database operations
"""

import os
import sqlite3
import contextlib
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple, Union, Generator
from datetime import datetime
import json

from config import get_config

# Setup logger
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection manager for SQLite"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database (None to use configured path)
        """
        config = get_config()
        self.db_path = db_path or config.database.main_db_path
        self.timeout = config.database.timeout
        
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get connection to database
        
        Returns:
            SQLite connection object
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Use Row for easier column access
            self._local.connection.row_factory = sqlite3.Row
        
        return self._local.connection
    
    def close(self):
        """Close all connections"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
    
    @contextlib.contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for transactions
        
        Yields:
            SQLite connection object with active transaction
        """
        conn = self.get_connection()
        
        try:
            yield conn
            conn.commit()
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            conn.rollback()
            raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query cursor
        """
        conn = self.get_connection()
        return conn.execute(query, params)
    
    def execute_many(self, query: str, params_list: list) -> sqlite3.Cursor:
        """
        Execute a SQL query with multiple parameter sets
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Query cursor
        """
        conn = self.get_connection()
        return conn.executemany(query, params_list)
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Fetch a single result from a query
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Result as a dictionary or None if no result
        """
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return {key: row[key] for key in row.keys()}
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Fetch all results from a query
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of result dictionaries
        """
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        
        return [{key: row[key] for key in row.keys()} for row in rows]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert data into a table
        
        Args:
            table: Table name
            data: Data to insert
            
        Returns:
            Row ID of inserted row
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())
        
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, values)
        
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple) -> int:
        """
        Update data in a table
        
        Args:
            table: Table name
            data: Data to update
            where: WHERE clause
            params: WHERE parameters
            
        Returns:
            Number of rows affected
        """
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        values = tuple(data.values()) + params
        
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        cursor = self.execute(query, values)
        
        return cursor.rowcount

class BaseRepository:
    """Base repository for database operations"""
    
    def __init__(self, db_connection: Optional[DatabaseConnection] = None):
        """
        Initialize repository
        
        Args:
            db_connection: Database connection (None to create new connection)
        """
        self.db = db_connection or DatabaseConnection()
    
    def close(self):
        """Close database connection"""
        self.db.close()
    
    def _create_database(self, schema_sql: str):
        """
        Create database schema
        
        Args:
            schema_sql: SQL schema definition
        """
        with self.db.transaction() as conn:
            conn.executescript(schema_sql)
    
    def _get_now(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def _serialize_json(self, obj: Any) -> str:
        """
        Serialize object to JSON string
        
        Args:
            obj: Object to serialize
            
        Returns:
            JSON string
        """
        return json.dumps(obj) if obj is not None else None
    
    def _deserialize_json(self, json_str: str) -> Any:
        """
        Deserialize JSON string to object
        
        Args:
            json_str: JSON string
            
        Returns:
            Deserialized object or None if input is None
        """
        return json.loads(json_str) if json_str is not None else None