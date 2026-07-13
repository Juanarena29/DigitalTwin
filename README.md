# Digital Twin

Un **digital twin** conversacional: un agente de IA que representa a una persona en su sitio web, responde sobre su carrera y ejecuta acciones mediante tools.

Este proyecto parte del ejercicio de la **Semana 1** del *AI Engineer Agentic Core Track*, pero lo extiende hacia algo más cercano a un producto mínimo deployable — sin perder el foco en los conceptos centrales del curso: **agent loop, system prompt, tools y orquestación**.

---

## Relación con el proyecto del curso

El baseline del curso (`twin/`) es deliberadamente simple:

| Curso (`twin/`) | Este proyecto (`DigitalTwin/`) |
|---|---|
| Un solo `app.py` con el chat loop | Arquitectura por capas (`agent/`, `ui/`, `memory/`, etc.) |
| 2 tools (email + pregunta sin respuesta) | 7 tools (contacto, scheduling, feedback, checklist) |
| Pushover para notificaciones | Pushover + persistencia en SQLite |
| Prompt básico con summary + LinkedIn | Grounding estricto + evaluator + guardrails |
| Sin memoria ni métricas | Memoria, dashboard y aprendizaje de comportamiento |

La complejización extra responde problemas reales que el proyecto simple no cubre: alucinaciones, seguridad, observabilidad y mejora iterativa del agente.

---

## Core value

### 1. Agente con tool loop

El twin no solo chatea: **decide cuándo usar herramientas**, ejecuta el loop hasta obtener una respuesta final y mantiene estado de sesión (checklist, `session_id`).

**Tools disponibles:**

- `record_user_details` — captura email de visitantes interesados
- `record_unknown_question` — registra preguntas que no puede responder (obligatorio antes de declinar)
- `record_feedback_tool` — guarda rating y comentario del visitante
- `check_availability_tool` / `schedule_call_tool` — flujo de agendamiento
- `create_checklist` / `mark_complete` — tareas multi-paso en conversaciones complejas

### 2. Grounding estricto

Las únicas fuentes de verdad son `data/summary.txt` y `data/linkedin.pdf`. El system prompt prohíbe inventar, inferir o extrapolar hechos. Si algo no está en el perfil, el agente debe usar `record_unknown_question` y declinar.

### 3. Evaluator con reintentos

Un segundo LLM revisa cada respuesta antes de enviarla al usuario. Si falla (alucinación, tono, longitud, tool faltante), el agente reescribe hasta **3 veces** con feedback específico. Esto es el patrón *generate → evaluate → revise* típico de sistemas agentic robustos.

### 4. Guardrails

Capa de seguridad previa al agente:

- **Rate limiting** por sesión
- **Clasificador de mensajes** para bloquear prompts maliciosos (jailbreak, extracción de system prompt, etc.)

### 5. Memoria persistente

Cada turno se guarda en SQLite (`data/twin.db`):

- Mensajes user/assistant
- Tools invocadas (`tool_log`)
- Resultados del evaluator (`evaluator_log`)
- Bloqueos de guardrails (`guardrail_log`)

Esto habilita analytics y el ciclo de mejora sin depender solo de logs en consola.

### 6. Dashboard de analytics

Pestaña protegida por contraseña con métricas de negocio:

- Sesiones, conversión a lead, calls agendadas, brechas de perfil
- Actividad diaria (mensajes y sesiones)
- Top preguntas sin respuesta
- Distribución de feedback

Componentes nativos de Gradio (`Number`, `LinePlot`, `BarPlot`) — sin CSS custom.

### 7. Improver de comportamiento (bonus)

Cuando el evaluator agota los 3 reintentos en un turno:

1. Se guarda el failure completo (pregunta, borradores rechazados, feedback)
2. Un LLM regenera reglas de **comportamiento** (no hechos) en `data/behavior_addendum.txt`
3. Ese texto se concatena al system prompt en cada mensaje

`summary.txt` y LinkedIn **nunca se modifican**. El improver solo ajusta *cómo* responder (cuándo usar tools, cómo declinar, redirigir, tono). El addendum se regenera consolidado — no crece linealmente con cada error.

---

## Arquitectura

```
app.py                 # Composition root: conecta UI ↔ lógica de negocio
├── agent/
│   ├── loop.py        # Chat loop, tool calls, evaluator, improver trigger
│   ├── evaluator.py   # Quality gate con reintentos
│   └── guardrails.py  # Rate limit + clasificador de seguridad
├── context.py         # System prompt (summary + LinkedIn + addendum dinámico)
├── tools/             # Definición e implementación de cada tool
├── memory/            # SQLite: schema, inserts, queries
├── dashboard/         # Agregación de métricas desde la DB
├── improver/          # Generación del behavior addendum
├── ui/                # Gradio: chat, analytics, layout
└── data/
    ├── summary.txt
    ├── linkedin.pdf   # (agregar manualmente)
    ├── twin.db        # generado en runtime
    └── behavior_addendum.txt
```

La UI recibe comportamiento como callables (`AnalyticsPorts`, `ChatConfig`) — el presentation layer no importa el LLM ni la DB directamente.

---

## Requisitos

- Python 3.11+
- Cuenta OpenAI con API key
- (Opcional) Cuenta Pushover para notificaciones en tiempo real
- (Opcional) `data/linkedin.pdf` — export de tu perfil de LinkedIn

---

## Setup

```bash
cd DigitalTwin
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copiá el archivo de entorno y completá los valores:

```bash
cp .env.example .env
```

| Variable | Requerida | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | Sí | API key de OpenAI |
| `DASHBOARD_PASSWORD` | No | Contraseña para la pestaña Analytics |
| `PUSHOVER_TOKEN` | No | Token de Pushover |
| `PUSHOVER_USER` | No | User key de Pushover |

Colocá tu perfil en `data/`:

- `data/summary.txt` — resumen personal en primera persona (ya incluido como ejemplo)
- `data/linkedin.pdf` — PDF exportado de LinkedIn

---

## Uso

```bash
python app.py
```

Abrí la URL que muestra Gradio (por defecto `http://127.0.0.1:7860`).

- **Chat** — conversación con el twin; ejemplos precargados para empezar
- **Analytics** — requiere `DASHBOARD_PASSWORD` en `.env`; métricas + aprendizaje de comportamiento

---

## Flujo de un mensaje

```
Usuario escribe mensaje
        ↓
   Guardrails (rate limit + safety)
        ↓
   Agent genera respuesta (system prompt + history + tools)
        ↓
   ¿Tool calls? → ejecutar → volver a generar
        ↓
   Evaluator revisa la respuesta
        ↓
   ¿Falló? → hasta 3 reintentos con feedback
        ↓
   Guardar turno en SQLite
        ↓
   ¿3 reintentos agotados? → regenerar behavior addendum
        ↓
   Responder al usuario
```

---

## Qué demuestra respecto al curso

| Concepto del curso | Implementación aquí |
|---|---|
| System prompt con contexto personal | `context.py` + grounding estricto |
| Tool calling loop | `agent/loop.py` |
| Tools como extensión del agente | `tools/` (7 herramientas) |
| UI con Gradio | `ui/` con componentes nativos |
| Acciones fuera del chat (notificaciones) | Pushover + SQLite |

**Extras respecto al baseline:** evaluator, guardrails, memoria, dashboard, improver de comportamiento.

---

## Posibles siguientes pasos (fuera de scope semana 1)

- Tope hard en el improver (últimos N failures, máx. palabras)
- Historial de versiones del behavior addendum
- Aprendizaje desde feedback negativo del usuario
- Deploy en Hugging Face Spaces o similar
- RAG sobre documentos adicionales (manteniendo fuentes de verdad explícitas)

---

## Licencia y contexto

Proyecto educativo personal — extensión del ejercicio de Semana 1 del *AI Engineer Agentic Core Track*. El código del curso original vive en `../twin/` como referencia.
