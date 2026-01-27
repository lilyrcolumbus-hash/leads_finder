# Lead Generation App

Aplicacion modular para generacion de leads que busca dueños de negocios con problemas de comunicacion (llamadas perdidas, necesidad de recepcionista, problemas de citas).

## Estructura del Proyecto

```
lead-generation/
├── main.py                 # Punto de entrada con menu interactivo
├── requirements.txt        # Dependencias
├── .env.example           # Template de configuracion
├── logs/                  # Logs de ejecucion
└── src/
    ├── config.py          # Configuracion central
    ├── scrapers/          # Modulos de scraping
    │   ├── reddit_scraper.py
    │   ├── hackernews_scraper.py
    │   ├── google_scraper.py
    │   └── producthunt_scraper.py
    ├── filters/
    │   └── ai_filter.py   # Filtrado con AI
    ├── crm/
    │   └── hubspot.py     # Integracion HubSpot
    └── utils/
        ├── logger.py      # Sistema de logging
        └── models.py      # Modelos de datos
```

## Instalacion

1. Clonar el repositorio
2. Crear entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   .\venv\Scripts\activate   # Windows
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   # Editar .env con tus API keys
   ```

## Configuracion

Edita el archivo `.env` con tus credenciales:

```env
HUBSPOT_API_KEY=tu_api_key_de_hubspot
GOOGLE_API_KEY=tu_api_key_de_google
GOOGLE_SEARCH_ENGINE_ID=tu_search_engine_id
OPENAI_API_KEY=tu_api_key_de_openai      # Opcional
ANTHROPIC_API_KEY=tu_api_key_anthropic   # Opcional
```

## Uso

### Menu Interactivo

```bash
python main.py
```

Opciones disponibles:
1. **Buscar nuevos leads** - Scraping de todas las fuentes o individual
2. **Ver mis leads** - Lista contactos del CRM
3. **Actualizar lead** - Cambiar etapa, agregar notas, marcar ganado/perdido
4. **Ver estadisticas** - Dashboard con metricas
5. **Buscar lead** - Buscar por nombre o email
6. **Configuracion** - Ver estado de APIs

### Linea de Comandos

```bash
# Solo scraping
python main.py --scrape

# Ver estadisticas
python main.py --stats

# Modo no interactivo
python main.py --scrape --no-interactive
```

## Fuentes de Leads

### Reddit (RSS Feeds)
Subreddits monitoreados:
- r/smallbusiness, r/sweatystartup
- r/HVAC, r/Plumbing, r/electricians
- r/Roofing, r/landscaping
- r/dentistry, r/realtors

### Hacker News
- API de Algolia
- Posts "Ask HN" sobre negocios
- Discusiones sobre atencion al cliente

### Google Search
- "receptionist needed"
- "need answering service"
- "never answers phone" reviews
- Y mas...

### Product Hunt
- Topics de customer service
- Founders buscando soluciones
- Discusiones sobre scheduling

## Keywords de Dolor

```
missed calls, losing customers, need receptionist
can't answer phone, overwhelmed, scheduling nightmare
no one answers, bad reviews, customer complaints
```

## Filtrado con AI

El sistema usa OpenAI o Anthropic para:
- Identificar si es dueño de negocio vs empleado
- Evaluar urgencia del problema
- Score de 0-1 para calificacion
- Solo leads con score >= 0.6 se califican

## Funciones del CRM

- Ver todos los leads/contactos
- Ver leads por etapa (nuevo, contactado, demo, cerrado)
- Mover lead a otra etapa
- Agregar notas
- Marcar como ganado o perdido
- Eliminar leads
- Buscar por nombre o email
- Ver estadisticas y conversion

## Logs

Los logs se guardan en `logs/` con formato:
```
logs/lead_gen_YYYYMMDD_HHMMSS.log
```
