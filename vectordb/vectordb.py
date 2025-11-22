import chromadb
import json
import os
import hashlib
import logging
from tqdm import tqdm
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self, collection_name="admin_docs", persist_directory="./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        self.embedding_fn = embedding_functions.OllamaEmbeddingFunction(
            model_name="nomic-embed-text:latest",
            url="http://localhost:11434/api/embeddings"
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        logger.info(f"ChromaDB подключена: {persist_directory}")

    def _generate_id(self, unique_string):
        return hashlib.md5(unique_string.encode('utf-8')).hexdigest()

    def _sanitize_metadata(self, meta_dict):
        clean = {}
        for k, v in meta_dict.items():
            if v is None:
                clean[k] = "Не указано"
            elif isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                # Обрезаем слишком длинные поля в метаданных, чтобы не раздувать базу
                clean[k] = str(v)[:1000] 
        return clean

    def _flatten_json(self, data):
        if isinstance(data, dict):
            return [data]
        flat_list = []
        for item in data:
            if isinstance(item, list):
                flat_list.extend(self._flatten_json(item))
            else:
                flat_list.append(item)
        return flat_list

    def _to_str(self, value):
        if value is None:
            return "Не указано"
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return ", ".join([self._to_str(v) for v in value])
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    # --- ИЗМЕНЕНИЕ 1: Уменьшили batch_size по умолчанию до 5 ---
    def ingest_from_json(self, file_path, batch_size=5): 
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не найден.")
            return

        logger.info(f"Начало загрузки данных из {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data_dirty = json.load(f)
            
            raw_data = self._flatten_json(raw_data_dirty)
        except Exception as e:
            logger.error(f"Ошибка чтения JSON: {e}")
            return

        logger.info(f"Всего записей: {len(raw_data)}")

        try:
            existing_ids_set = set(self.collection.get()['ids'])
        except:
            existing_ids_set = set()
        
        documents, metadatas, ids = [], [], []
        skipped_count, new_count = 0, 0

        seen_ids_in_batch = set()

        for item in tqdm(raw_data, desc="Обработка"):
            if not isinstance(item, dict): continue

            time_val = self._to_str(item.get('time', 'н/д'))
            doc_num = self._to_str(item.get('number_document', 'б/н'))
            
            corr_raw = item.get('correspondence')
            sol_raw = item.get('solution')
            
            corr = self._to_str(corr_raw)
            solution = self._to_str(sol_raw)

            if (corr == "Не указано" or not corr.strip()) and (not solution.strip()):
                continue

            place_type = self._to_str(item.get('type_place', ''))
            society = self._to_str(item.get('society', ''))
            street = self._to_str(item.get('street', ''))
            floors = self._to_str(item.get('floors', ''))

            # Формируем текст
            full_text = (
                f"Тип документа: {corr}\n"
                f"Номер: {doc_num}\n"
                f"Дата принятия: {time_val}\n"
                f"Организация: {society} {place_type}\n"
                f"Адрес: {street} {floors}\n"
                f"СОДЕРЖАНИЕ:\n{solution}"
            )
            
            # ИЗМЕНЕНИЕ: Хешируем ВЕСЬ текст + номер, чтобы ID был точно уникальным для контента
            unique_key = f"{doc_num}_{full_text}"
            doc_id = self._generate_id(unique_key)

            # Проверка: есть ли в базе ИЛИ есть ли уже в текущем списке на добавление
            if doc_id in existing_ids_set or doc_id in seen_ids_in_batch:
                skipped_count += 1
                continue

            # Обрезаем текст, чтобы Ollama не упала по таймауту или контексту
            searchable_text = full_text[:8000] 
            
            meta = {
                "date": time_val,
                "number": doc_num,
                "title": corr[:100],
                "solution": solution[:200],
                "society": society,
                "address": f"{street} {floors}".strip()
            }
            
            documents.append(searchable_text)
            metadatas.append(self._sanitize_metadata(meta))
            ids.append(doc_id)
            seen_ids_in_batch.add(doc_id) # Запоминаем, что этот ID мы уже готовим к отправке
            new_count += 1

            if len(documents) >= batch_size:
                try:
                    self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
                except Exception as e:
                    logger.error(f"Ошибка при добавлении записи {ids}: {e}")
                
                # Очищаем списки
                documents, metadatas, ids = [], [], []
                # seen_ids_in_batch НЕ очищаем, чтобы ловить дубли во всем файле

        # Добавляем остатки
        if documents:
            try:
                self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            except Exception as e:
                logger.error(f"Ошибка при добавлении последних документов: {e}")

        logger.info(f"Загрузка завершена. Пропущено (дубликаты): {skipped_count}, Добавлено: {new_count}")

    def search(self, query_text, n_results=5):
        logger.info(f"Поиск в БД: '{query_text}'")
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

    def count(self):
        return self.collection.count()