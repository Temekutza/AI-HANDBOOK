import sqlite3
import hashlib
import logging  # <--- Импорт
from cachetools import LRUCache

# Создаем логгер для этого файла
logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, db_path="cache.db", l1_size=100):
        self.l1_cache = LRUCache(maxsize=l1_size)
        self.db_path = db_path
        self._init_sqlite()

    def _init_sqlite(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            with self.conn:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS llm_cache (
                        query_hash TEXT PRIMARY KEY,
                        query_text TEXT,
                        response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            logger.info("L2 Cache (SQLite) инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации SQLite: {e}")

    def _get_hash(self, text: str) -> str:
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    def get(self, query: str):
        key = self._get_hash(query)

        # 1. L1 Check
        if key in self.l1_cache:
            logger.info("L1 Cache HIT (RAM)")
            return self.l1_cache[key]

        # 2. L2 Check
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT response FROM llm_cache WHERE query_hash = ?", (key,))
            row = cursor.fetchone()

            if row:
                response = row[0]
                self.l1_cache[key] = response
                logger.info("L2 Cache HIT (Disk)")
                return response
        except Exception as e:
            logger.error(f"Ошибка чтения из SQLite: {e}")
        
        return None

    def set(self, query: str, response: str):
        key = self._get_hash(query)
        self.l1_cache[key] = response

        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO llm_cache (query_hash, query_text, response) VALUES (?, ?, ?)",
                    (key, query, response)
                )
            logger.debug("Ответ сохранен в кэш")
        except Exception as e:
            logger.error(f"Не удалось сохранить в SQLite: {e}")

    def clear(self):
        self.l1_cache.clear()
        with self.conn:
            self.conn.execute("DELETE FROM llm_cache")
        logger.warning("Кэш полностью очищен")