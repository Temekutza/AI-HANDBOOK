from ollama import AsyncClient 
import logging

# Логгер
logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, model_name: str = 'llama3.1:8b'):
        self.model_name = model_name
        self.client = AsyncClient() 
        logger.info(f"LLM клиент инициализирован: {model_name}")

    async def generate_answer_stream(self, question: str, context_docs: list):
        context_str = "\n\n---\n\n".join(context_docs)
        
        if not context_str:
            logger.warning("Пустой контекст")
            yield "К сожалению, в базе знаний нет информации по этому вопросу."
            return
        
        system_prompt = (
            "Ты — аналитик документов администрации. Твоя задача — отвечать на вопросы, используя ТОЛЬКО предоставленный контекст.\n"
            "ВАЖНО:\n"
            "1. Если пользователь спрашивает дату события, а в тексте есть только 'Дата принятия' документа — используй её как ответ.\n"
            "2. Отвечай кратко и точно.\n"
            "3. Списки и таблицы из текста преобразуй в понятный вид."
        )

        user_message = f"""
        КОНТЕКСТ ИЗ БАЗЫ ДАННЫХ:
        {context_str}

        ВОПРОС ПОЛЬЗОВАТЕЛЯ:
        {question}
        """

        try:
            logger.info("Start streaming generation...")
            # stream=True — ключевой момент для скорости восприятия
            async for part in await self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                options={"temperature": 0.1, "num_ctx": 4096},
                stream=True
            ):
                # Возвращаем кусочек текста, как только он готов
                token = part['message']['content']
                yield token

        except Exception as e:
            logger.error(f"Ошибка генерации: {e}")
            yield f"\n[Ошибка]: {str(e)}"