import logging
import os
from pathlib import Path

def setup_logging():
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,  # Уровень: INFO и выше
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',  # Формат строки
        handlers=[
            logging.StreamHandler()  # В консоль
        ]
    )

    logging.info("Логирование инициализировано")
    logging.getLogger("httpx").setLevel(logging.WARNING)