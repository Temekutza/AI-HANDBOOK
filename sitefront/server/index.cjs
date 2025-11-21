const express = require('express');
const fs = require('fs');
const path = require('path');
// Создаём и настраиваем приложение Express (HTTP-сервер)
const app = express();
// Порт можно переопределить через переменную окружения PORT, по умолчанию 3000
const PORT = process.env.PORT || 3000;

// Поддержка JSON-тел в запросах (POST/PUT и т.п.), пригодится при расширении API
app.use(express.json());

// Простая загрузка документов из JSON-файла.
// Текущий источник данных — локальный JSON-файл рядом с сервером.
// При переходе на БД или внешний API достаточно поменять реализацию loadDocuments ниже.
const documentsPath = path.join(__dirname, 'documents.json');

// Функция-обёртка: читает и парсит файл documents.json.
// Если файла нет или формат некорректный — не "роняет" сервер, а возвращает пустой массив.
// Здесь можно заменить реализацию на чтение из базы данных или другого источника, не трогая остальной код.
function loadDocuments() {
  try {
    const raw = fs.readFileSync(documentsPath, 'utf-8');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    return [];
  } catch (error) {
    console.error('Не удалось прочитать documents.json:', error.message);
    return [];
  }
}

// GET /api/documents — возвращает список всех документов.
// Сейчас данные читаются с диска при каждом запросе.
// Если позже появится база данных, можно вызывать её из loadDocuments или прямо здесь.
app.get('/api/documents', (req, res) => {
  const documents = loadDocuments();
  res.json(documents);
});

// GET /api/documents/:id — возвращает один документ по идентификатору.
// Подходит, если на фронте нужно загружать детали документа по id отдельным запросом.
app.get('/api/documents/:id', (req, res) => {
  const documents = loadDocuments();
  const doc = documents.find((item) => item.id === req.params.id);

  if (!doc) {
    return res.status(404).json({ message: 'Документ не найден' });
  }

  res.json(doc);
});

// В продакшене: отдаём собранный фронтенд из dist.
// После команды `npm run build` Vite собирает статику в эту папку,
// и этот же сервер начинает её раздавать.
const distPath = path.join(__dirname, '..', 'dist');

if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));

  app.get('*', (req, res) => {
    // Для любых неизвестных маршрутов отдаём index.html,
    // чтобы маршрутизация работала на стороне фронтенда (SPA).
    res.sendFile(path.join(distPath, 'index.html'));
  });
}

// Запускаем HTTP-сервер и выводим в консоль адрес, по которому он доступен.
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
