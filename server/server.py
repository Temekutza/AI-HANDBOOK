from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import logging
import os
import re

# Импорты работают от корня проекта, так как запускаем main.py
from src.vectordb.vectordb import VectorDB
from src.llm.llm import LLMClient
from src.cache.cache import CacheManager
from src.logging.logger_config import setup_logging

setup_logging()
logger = logging.getLogger("Server")

app = FastAPI(title="AI Handbook API")

# Настройка CORS (чтобы фронт видел бэк)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для разработки можно разрешить всем
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные
db = None
llm = None
cache = None

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    action_type: Optional[str] = "search"
    # Для проверки конфликтов можно передать текст документа
    document_text: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global db, llm, cache
    logger.info(">>> Инициализация ресурсов (DB, LLM, Cache)...")
    
    # Инициализируем классы
    # Убедись, что пути внутри этих классов (к базе Chroma и т.д.) правильные
    db = VectorDB() 
    llm = LLMClient()
    cache = CacheManager()
    
    logger.info(">>> Сервер готов!")

@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    logger.info(f"Запрос: {request.query} [{request.action_type}]")
    
    # 1. ПРОВЕРКА ОРФОГРАФИИ
    if request.action_type == "check_spelling":
        # Проверка кэша
        cache_key = f"spell:{request.query}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            logger.info("Отдаем ответ из кэша (Spelling)")
            full_answer = cached_response
        else:
            full_answer = ""
            async for token in llm.check_spelling_stream(request.query):
                full_answer += token
            # Сохраняем в кэш
            cache.set(cache_key, full_answer)
            
        return {
            "title": "Проверка орфографии",
            "items": [{
                "id": "spell-check",
                "title": "Исправленный текст",
                "type": "Орфография",
                "date": "Сегодня",
                "content": full_answer
            }]
        }

    # 2. ПРОВЕРКА КОНФЛИКТОВ (Новая фича)
    elif request.action_type == "check_conflicts":
        # Если передан текст документа, ищем конфликты с ним
        # Если нет, ищем конфликты по запросу (например, "конфликты в постановлении №X")
        query_to_check = request.document_text if request.document_text else request.query
        
        # Ищем похожие документы, которые могут противоречить
        results = db.search(query_to_check, n_results=5)
        
        if not results or not results['documents']:
             return {
                "title": "Проверка конфликтов",
                "items": [{
                    "id": "no-conflicts",
                    "title": "Конфликтов не найдено",
                    "type": "Конфликты",
                    "date": "Сегодня",
                    "content": "Похожих нормативных актов в базе не найдено."
                }]
            }

        found_docs = results['documents'][0]
        found_metas = results['metadatas'][0]
        
        context_docs = []
        for doc, meta in zip(found_docs, found_metas):
             context_docs.append(f"СУЩЕСТВУЮЩИЙ ДОКУМЕНТ ({meta.get('title', 'Без названия')}):\n{doc}")
        
        full_answer = ""
        # Используем LLM для анализа противоречий
        # В реальном проекте тут нужен отдельный метод в LLMClient, но пока используем generate_answer_stream с хитрым промптом внутри
        conflict_prompt = (
            f"Проанализируй текст на предмет противоречий с существующими документами.\n"
            f"ТЕКСТ ДЛЯ ПРОВЕРКИ:\n{query_to_check}\n\n"
            f"Задача: Найди возможные юридические или логические противоречия."
        )
        
        async for token in llm.generate_answer_stream(conflict_prompt, context_docs):
            full_answer += token
            
        return {
            "title": "Анализ противоречий",
            "items": [{
                "id": "conflict-check",
                "title": "Отчет о противоречиях",
                "type": "Конфликты",
                "date": "Сегодня",
                "content": full_answer
            }]
        }

    # 3. ПОИСК ДОКУМЕНТОВ (Поиск, Примеры, Связанные)
    elif request.action_type in ["search", "find_example", "find_related"]:
        results = db.search(request.query, n_results=request.limit)
        items = []
        
        if results and results['documents']:
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            
            for doc, meta in zip(docs, metas):
                # --- УЛУЧШЕНИЕ: Чистим текст для превью ---
                clean_content = doc
                if "СОДЕРЖАНИЕ:" in doc:
                    clean_content = doc.split("СОДЕРЖАНИЕ:")[-1].strip()
                
                clean_content = clean_content.replace("\n", " ")
                
                # --- АВТОЛИНКОВКА (Идея 2) ---
                # Ищем упоминания номеров документов (например № 123) и подсвечиваем их
                # В JSON ответе мы просто возвращаем текст, но на фронте можно было бы это парсить
                # Тут мы просто добавим пометку, если нашли ссылки
                links_found = re.findall(r'№\s*\d+', clean_content)
                
                items.append({
                    "id": meta.get('number', '0'),
                    "title": meta.get('title', 'Без названия'),
                    "type": "Документ",
                    "date": meta.get('date', 'н/д'),
                    "content": clean_content[:250] + ("..." if len(clean_content)>250 else ""),
                    "path": meta.get('path', ''),
                    "links": links_found # Возвращаем найденные ссылки
                })
        
        titles = {
            "search": f"Результаты: {request.query}",
            "find_example": "Найденные примеры",
            "find_related": "Связанные документы"
        }
                
        return {"title": titles.get(request.action_type, "Результаты"), "items": items}

    # 4. ГЕНЕРАЦИЯ ОТЧЕТА (LLM)
    elif request.action_type == "report":
        # Проверка кэша
        cache_key = f"report:{request.query}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            logger.info("Отдаем ответ из кэша (Report)")
            full_answer = cached_response
        else:
            # Ищем контекст
            results = db.search(request.query, n_results=5)
            
            if not results or not results['documents']:
                 return {"title": "Ошибка", "items": [{"title": "Данные не найдены", "content": "В базе нет подходящих документов."}]}

            found_docs = results['documents'][0]
            found_metas = results['metadatas'][0]
            
            rich_context = []
            for doc, meta in zip(found_docs, found_metas):
                # --- УЛУЧШЕНИЕ: Добавляем метаданные в контекст для LLM ---
                doc_info = (
                    f"ДОКУМЕНТ №{meta.get('number', 'б/н')} от {meta.get('date', 'н/д')}\n"
                    f"Название: {meta.get('title', 'Без названия')}\n"
                    f"Текст:\n{doc}\n"
                )
                rich_context.append(doc_info)
            
            # Генерируем ответ
            full_answer = ""
            async for token in llm.generate_answer_stream(request.query, rich_context):
                full_answer += token
            
            # Сохраняем в кэш
            cache.set(cache_key, full_answer)
            
        return {
            "title": "Сгенерированный отчет",
            "items": [{
                "id": "ai-report",
                "title": "Аналитическая справка",
                "type": "AI Report",
                "date": "Сегодня",
                "content": full_answer # Тут будет текст от нейронки
            }]
        }
    
    return {"title": "Ошибка", "items": []}

@app.get("/api/download")
async def download_file(path: str):
    # Простейшая защита от выхода за пределы папки проекта
    if ".." in path:
        return {"error": "Invalid path"}
        
    file_path = os.path.join(os.getcwd(), path)
    
    if os.path.exists(file_path):
        return FileResponse(
            file_path, 
            filename=os.path.basename(file_path),
            media_type='application/octet-stream'
        )
    return {"error": "File not found"}