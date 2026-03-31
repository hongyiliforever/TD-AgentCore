import configparser
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config import settings
from src.utils.logger import agent_logger as logger


class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                user=settings.database.user,
                password=settings.database.password,
                database=settings.database.database
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def _reconnect_if_needed(self):
        if self.conn is None or self.conn.closed != 0:
            logger.info("Database connection closed, reconnecting...")
            self.connect()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        self._reconnect_if_needed()
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        self._reconnect_if_needed()
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor.rowcount
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Update execution failed: {e}")
            return 0
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute_update(query, tuple(data.values()))
    
    def find_one(self, table: str, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
        query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 1"
        results = self.execute_query(query, tuple(conditions.values()))
        return results[0] if results else None
    
    def find_many(self, table: str, conditions: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if conditions:
            where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
            query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT {limit}"
            return self.execute_query(query, tuple(conditions.values()))
        else:
            query = f"SELECT * FROM {table} LIMIT {limit}"
            return self.execute_query(query)


class ExampleCore:
    def __init__(self):
        self.db = DatabaseManager()
    
    def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Processing data: {data}")
        return {
            "status": "success",
            "processed_at": datetime.now().isoformat(),
            "data": data
        }
    
    def save_result(self, table: str, result: Dict[str, Any]) -> int:
        result["created_at"] = datetime.now()
        return self.db.insert(table, result)
    
    def get_result(self, table: str, record_id: int) -> Optional[Dict[str, Any]]:
        return self.db.find_one(table, {"id": record_id})
