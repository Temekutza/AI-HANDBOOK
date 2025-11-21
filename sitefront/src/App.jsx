import { useEffect, useMemo, useState } from 'react'
import './App.css'

// Демонстрационный список документов.
// Используется до загрузки данных с сервера и как фолбэк, если API недоступно или вернуло ошибку.
const MOCK_DOCUMENTS = [
  {
    id: '1',
    title: 'Порядок оформления служебной записки',
    category: 'Кадры',
    tags: ['служебная записка', 'документооборот', 'внутренние коммуникации'],
    summary:
      'Краткая инструкция по подготовке и согласованию служебной записки внутри администрации.',
    updatedAt: '2025-10-02',
    readingTime: '4 мин',
    importance: 'Высокий приоритет',
    content:
      'Служебная записка используется для внутренней коммуникации между подразделениями администрации... (демонстрационный текст).',
  },
  {
    id: '2',
    title: 'Отпуск: какие заявления нужны сотруднику',
    category: 'Кадры',
    tags: ['отпуск', 'кадры', 'заявление'],
    summary:
      'Какие типы отпусков существуют, какие заявления требуются и кому их подавать.',
    updatedAt: '2025-09-15',
    readingTime: '6 мин',
    importance: 'Рекомендуется к прочтению',
    content:
      'Для оформления отпуска сотрудник подаёт заявление на имя руководителя, после чего документ проходит согласование в кадровой службе... (демонстрационный текст).',
  },
  {
    id: '3',
    title: 'Регистрация обращений граждан',
    category: 'Обращения граждан',
    tags: ['обращения', 'граждане', 'регистрация'],
    summary: 'Пошаговый порядок регистрации письменных и электронных обращений.',
    updatedAt: '2025-08-22',
    readingTime: '5 мин',
    importance: 'Критично для приёмной',
    content:
      'Все обращения граждан подлежат обязательной регистрации в день поступления в журнале или информационной системе... (демонстрационный текст).',
  },
  {
    id: '4',
    title: 'Командировки: приказы и авансовые отчёты',
    category: 'Финансы',
    tags: ['командировка', 'финансы', 'аванс'],
    summary: 'Что нужно оформить до, во время и после служебной командировки.',
    updatedAt: '2025-07-30',
    readingTime: '7 мин',
    importance: 'Важно для бухгалтерии и руководителей',
    content:
      'Перед командировкой оформляется приказ, служебное задание и выдаётся аванс. По возвращении сотрудник предоставляет авансовый отчёт... (демонстрационный текст).',
  },
  {
    id: '5',
    title: 'Шаблоны часто используемых документов',
    category: 'Общее',
    tags: ['шаблоны', 'унифицированные формы'],
    summary:
      'Подборка шаблонов служебных записок, приказов, заявлений и других документов.',
    updatedAt: '2025-06-10',
    readingTime: '3 мин',
    importance: 'Быстрый доступ',
    content:
      'Здесь собраны ссылки на актуальные шаблоны документов, утверждённые внутренними регламентами администрации... (демонстрационный текст).',
  },
]

// Список доступных разделов для фильтрации в левом сайдбаре.
// id должен совпадать со значением поля category в документе.
const CATEGORIES = [
  { id: 'all', label: 'Все разделы' },
  { id: 'Кадры', label: 'Кадры' },
  { id: 'Финансы', label: 'Финансы' },
  { id: 'Обращения граждан', label: 'Обращения граждан' },
  { id: 'Общее', label: 'Общее' },
]

// Главный компонент приложения "умная база документов".
// Управляет поиском, фильтрацией, выбором документа и отображением трёхколоночного интерфейса.
function App() {
  // Текст поискового запроса из строки ввода.
  const [query, setQuery] = useState('')
  // Текущая выбранная категория в сайдбаре ("Все разделы", "Кадры" и т.п.).
  const [selectedCategory, setSelectedCategory] = useState('all')
  // Текущий список документов: сначала MOCK_DOCUMENTS, потом данные с сервера, если он доступен.
  const [documents, setDocuments] = useState(MOCK_DOCUMENTS)
  // Идентификатор выбранного документа для панели деталей справа.
  const [selectedDocId, setSelectedDocId] = useState(MOCK_DOCUMENTS[0]?.id)
  // Флаг загрузки документов с сервера.
  const [isLoading, setIsLoading] = useState(false)
  // Текст ошибки при загрузке (null, если всё хорошо).
  const [error, setError] = useState(null)

  const appName = "Умная БД документов"

  // Производное значение: список документов после применения фильтра по разделу и текстового запроса.
  // useMemo помогает не пересчитывать фильтрацию на каждый рендер, а только при изменении входных данных.
  const filteredDocs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    return documents.filter((doc) => {
      if (selectedCategory !== 'all' && doc.category !== selectedCategory) {
        return false
      }

      if (!normalizedQuery) return true

      // Формируем "поле для поиска" из нескольких текстовых полей документа,
      // приводим к нижнему регистру и ищем вхождение строки запроса.
      const haystack = [
        doc.title,
        doc.summary,
        doc.category,
        doc.importance,
        ...(doc.tags || []),
        doc.content,
      ]
        .filter(Boolean)
        .map((value) => value.toLowerCase())
        .join(' ')

      return haystack.includes(normalizedQuery)
    })
  }, [documents, query, selectedCategory])

  // Документ, который сейчас отображается в панели деталей справа.
  // Если выбранный id не найден среди отфильтрованных документов, берём первый подходящий.
  const selectedDoc =
    filteredDocs.find((doc) => doc.id === selectedDocId) ||
    filteredDocs[0] ||
    documents[0]

  // Загружаем документы с сервера один раз при монтировании компонента.
  // ВАЖНО: если URL API изменится, нужно обновить его здесь и прокси в vite.config.js (server.proxy['/api']).
  useEffect(() => {
    setIsLoading(true)

    fetch('/api/documents')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load documents')
        }
        return response.json()
      })
      .then((data) => {
        if (Array.isArray(data) && data.length) {
          setDocuments(data)
        }
        setError(null)
      })
      .catch((fetchError) => {
        console.error('Ошибка загрузки документов:', fetchError)
        setError('Не удалось загрузить данные с сервера, показаны демо-документы.')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  // Следим за изменением списка найденных документов и выбранного id.
  // Если выбранный документ больше не подходит под фильтр, автоматически выбираем первый.
  useEffect(() => {
    if (!filteredDocs.length) return

    if (!selectedDocId || !filteredDocs.some((doc) => doc.id === selectedDocId)) {
      setSelectedDocId(filteredDocs[0].id)
    }
  }, [filteredDocs, selectedDocId])

  // Быстро подставляет заранее заданный пример запроса в строку поиска.
  const handleQuickQuestion = (text) => {
    setQuery(text)
  }

  return (
    <>
      {/* Основной каркас интерфейса: шапка, поиск и три колонки (разделы, список, детали). */}
      <div className="kb-shell">
        <header className="kb-header">
          <div className="kb-title-block">
            <span className="kb-pill">Администрация · внутренняя база</span>
            <h1 className="kb-title">{appName}</h1>
            <p className="kb-subtitle">
              Задайте вопрос и получите ответ
            </p>
          </div>
        </header>

        <section className="kb-search-section">
          <div className="kb-search-box">
            <div className="kb-search-input-wrapper">
              <span className="kb-search-icon">?</span>
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Например: «Как оформить служебную записку?»"
                className="kb-search-input"
              />
              {query && (
                <button
                  type="button"
                  className="kb-clear-button"
                  onClick={() => setQuery('')}
                >
                  Очистить
                </button>
              )}
            </div>
            <div className="kb-quick-questions">
              <button
                type="button"
                className="kb-chip"
                onClick={() => handleQuickQuestion('служебная записка')}
              >
                Служебная записка
              </button>
              <button
                type="button"
                className="kb-chip"
                onClick={() => handleQuickQuestion('отпуск')}
              >
                Оформление отпуска
              </button>
              <button
                type="button"
                className="kb-chip"
                onClick={() => handleQuickQuestion('обращения граждан')}
              >
                Обращения граждан
              </button>
              <button
                type="button"
                className="kb-chip"
                onClick={() => handleQuickQuestion('командировка')}
              >
                Командировка
              </button>
            </div>
          </div>
        </section>

        <section className="kb-layout">
          <section className="kb-results">
            <div className="kb-results-header">
              <h2 className="kb-results-title">
                Найдено документов: {filteredDocs.length}
              </h2>
              {query && (
                <span className="kb-results-query">
                  По запросу «{query}»
                </span>
              )}
            </div>

            {isLoading && !error && (
              <p className="kb-hint">Обновляем список документов с сервера...</p>
            )}

            {error && <p className="kb-error">{error}</p>}

            {filteredDocs.length === 0 ? (
              <div className="kb-empty-state">
                <h3>Ничего не нашлось</h3>
                <p>
                  Попробуй переформулировать вопрос или выбрать другой раздел.
                  В реальной системе здесь бы подсказали ближайшие по смыслу документы.
                </p>
              </div>
            ) : (
              <ul className="kb-results-list">
                {filteredDocs.map((doc) => (
                  <li key={doc.id}>
                    <button
                      type="button"
                      className={
                        doc.id === selectedDocId
                          ? 'kb-result-card kb-result-card--active'
                          : 'kb-result-card'
                      }
                      onClick={() => setSelectedDocId(doc.id)}
                    >
                      <div className="kb-result-meta">
                        <span className="kb-result-category">{doc.category}</span>
                        <span className="kb-result-updated">Обновлено {doc.updatedAt}</span>
                      </div>
                      <h3 className="kb-result-title">{doc.title}</h3>
                      <p className="kb-result-summary">{doc.summary}</p>
                      <div className="kb-result-footer">
                        <span className="kb-result-pill">{doc.readingTime}</span>
                        <span className="kb-result-pill kb-result-pill--accent">{doc.importance}</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="kb-details">
            <h2 className="kb-details-title">
              {selectedDoc?.title || 'Выбери документ слева'}
            </h2>
            {selectedDoc && (
              <>
                <div className="kb-details-meta">
                  <span className="kb-details-tag">Раздел: {selectedDoc.category}</span>
                  <span className="kb-details-tag">Обновлено: {selectedDoc.updatedAt}</span>
                  <span className="kb-details-tag">Время чтения: {selectedDoc.readingTime}</span>
                </div>
                <p className="kb-details-summary">{selectedDoc.summary}</p>
                <div className="kb-details-content">
                  <p>{selectedDoc.content}</p>
                  {selectedDoc.tags && (
                    <div className="kb-details-tags">
                      {selectedDoc.tags.map((tag) => (
                        <span key={tag} className="kb-details-chip">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </section>
        </section>
      </div>
    </>
  )
}

export default App
