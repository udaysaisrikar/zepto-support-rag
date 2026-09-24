# Zepto Support Assistant

A RAG-based customer support API for answering questions about Zepto policies.

The application combines:

- FastAPI for the HTTP API
- Sentence Transformers with `all-MiniLM-L6-v2` for embeddings
- ChromaDB for vector storage and cosine similarity retrieval
- LangGraph for intent classification and routing
- Pydantic for request/response validation
- A deterministic mock generation mode for reproducible evaluation
- Docker for containerized deployment

---

## Architecture

```text
                         User Query
                             |
                             v
                    +------------------+
                    |    FastAPI       |
                    |    POST /ask     |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    | classify_intent  |
                    +--------+---------+
                             |
                 +-----------+-----------+
                 |                       |
          Policy question          General question
                 |                       |
                 v                       v
       +--------------------+    +----------------+
       | retrieve_and_answer|    | direct_answer  |
       +---------+----------+    +----------------+
                 |
                 v
          Query Embedding
                 |
                 v
             ChromaDB
          Top 3 Retrieval
                 |
                 v
         Context + Prompt
                 |
                 v
          Mock Generation
                 |
                 v
       Structured API Response
````

---

## RAG Pipeline

The system follows four stages:

### 1. Ingestion

The eight policy documents are stored in:

```text
docs/
├── doc_01.txt
├── doc_02.txt
├── doc_03.txt
├── doc_04.txt
├── doc_05.txt
├── doc_06.txt
├── doc_07.txt
└── doc_08.txt
```

`app/ingestion.py` loads the documents and stores their embeddings in ChromaDB.

Each document is represented as one chunk for this baseline implementation.

The ingestion process validates that exactly eight documents are present.

---

### 2. Embedding

The required embedding model is:

```text
all-MiniLM-L6-v2
```

The model produces 384-dimensional embeddings.

`app/embeddings.py` provides a cached model instance so the embedding model is loaded only once per process.

---

### 3. Retrieval

`app/retrieval.py` performs semantic search against the ChromaDB collection:

```text
zepto_policies
```

The collection uses cosine similarity.

The system retrieves the top 3 matching chunks for every policy query.

Each retrieved result contains:

* `chunk_id`
* `document_id`
* `text`
* `distance`

---

### 4. Generation

`app/prompts.py` defines the support prompt.

The prompt contains:

* Role
* Context
* Task
* Format
* Length
* Negative constraint
* Few-shot example

For the graded baseline, `MOCK_LLM=1` is used.

The mock generation response is deterministic:

```text
Based on the retrieved context: {top_chunk_text}
```

This avoids requiring an external LLM API key during evaluation.

The prompt construction is kept separate so a real LLM provider can be added later without changing the retrieval or API layers.

---

# LangGraph Flow

The LangGraph workflow is implemented in:

```text
app/graph.py
```

It contains three main nodes:

```text
classify_intent
retrieve_and_answer
direct_answer
```

### Policy route

If the query contains a supported policy keyword:

```text
classify_intent
       |
       v
retrieve_and_answer
       |
       v
      END
```

Supported keywords include:

```text
delivery
return
refund
membership
tracking
cancel
gift card
support hours
```

### General route

For queries outside the supported policy domain:

```text
classify_intent
       |
       v
direct_answer
       |
       v
      END
```

The response is:

```text
I can only answer questions about Zepto policies right now.
```

---

# API

## Start locally

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Build the vector store:

```powershell
python -m app.ingestion
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

---

## Health Check

```http
GET /health
```

Example:

```json
{
  "status": "healthy"
}
```

---

## Ask a Question

```http
POST /ask
Content-Type: application/json
```

Request:

```json
{
  "query": "How long does delivery take?"
}
```

Example response:

```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation...",
  "sources": [
    "doc_01_chunk_00",
    "doc_02_chunk_00",
    "doc_04_chunk_00"
  ],
  "confidence": 1.0
}
```

---

## General Question Example

Request:

```json
{
  "query": "What is the capital of India?"
}
```

Response:

```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```

---

# Project Structure

```text
support_assistant/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── embeddings.py
│   ├── ingestion.py
│   ├── retrieval.py
│   ├── prompts.py
│   ├── graph.py
│   └── main.py
│
├── docs/
│   ├── doc_01.txt
│   ├── doc_02.txt
│   ├── doc_03.txt
│   ├── doc_04.txt
│   ├── doc_05.txt
│   ├── doc_06.txt
│   ├── doc_07.txt
│   └── doc_08.txt
│
├── data/
│   └── chroma/
│
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```

---

# File Responsibilities

| File            | Responsibility                                     |
| --------------- | -------------------------------------------------- |
| `config.py`     | Paths, model name, Chroma collection and mock mode |
| `models.py`     | Graph state and API schemas                        |
| `embeddings.py` | Cached embedding model                             |
| `ingestion.py`  | Document loading and Chroma indexing               |
| `retrieval.py`  | Semantic top-3 retrieval                           |
| `prompts.py`    | RAG prompt template                                |
| `graph.py`      | LangGraph routing and generation                   |
| `main.py`       | FastAPI application and `/ask` endpoint            |

---

# ChromaDB

The ChromaDB collection is:

```text
zepto_policies
```

The database is persisted under:

```text
data/chroma/
```

The Docker image intentionally does not copy an existing local Chroma database.

Instead, the container creates and populates its own vector store from the eight documents.

This makes the image reproducible across environments.

---

# Mock LLM Configuration

The default mode is:

```text
MOCK_LLM=1
```

It can also be configured through an environment variable:

```powershell
$env:MOCK_LLM="1"
```

The mock mode is deterministic and does not require an external LLM provider.

The generation boundary is intentionally isolated so a real provider such as Groq/OpenAI can be added in a future phase.

---

# Docker

Build the image:

```powershell
docker build -t zepto-support-assistant .
```

Run the container:

```powershell
docker run --name zepto-support -p 8000:8000 zepto-support-assistant
```

The API is then available at:

```text
http://localhost:8000
```

Health check:

```powershell
Invoke-RestMethod `
  -Uri http://localhost:8000/health `
  -Method Get
```

Policy test:

```powershell
$body = @{
    query = "How long does delivery take?"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://localhost:8000/ask `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json
```

---

# Future Extension Points

The baseline is intentionally simple while keeping clear boundaries for future phases.

Possible extensions include:

1. Real LLM generation
2. Streaming responses
3. More sophisticated intent classification
4. Better document chunking
5. Metadata filtering
6. Conversation memory
7. Evaluation datasets
8. Retrieval quality metrics
9. Authentication and rate limiting
10. Production observability
11. Feedback-driven retrieval improvement
12. Additional policy documents

These extensions can be added without changing the basic FastAPI → LangGraph → Retrieval architecture.

````

---

# 3. Final Docker rebuild

After changing `config.py` and `graph.py`:

```powershell
docker rm -f zepto-support
docker build -t zepto-support-assistant .
docker run --name zepto-support -p 8000:8000 zepto-support-assistant
````

Then test **both** routes one final time:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

```powershell
$body = @{ query = "How long does delivery take?" } | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://localhost:8000/ask `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json
```

And:

```powershell
$body = @{ query = "What is the capital of India?" } | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://localhost:8000/ask `
  -Method Post `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json
```

### Final expected checklist

```text
[✓] 8 policy documents
[✓] all-MiniLM-L6-v2
[✓] ChromaDB
[✓] cosine similarity
[✓] top-3 retrieval
[✓] LangGraph StateGraph
[✓] classify_intent
[✓] retrieve_and_answer
[✓] direct_answer
[✓] conditional routing
[✓] prompt template
[✓] mock LLM
[✓] Pydantic response
[✓] FastAPI /ask
[✓] Docker
[✓] README
[✓] policy query tested
[✓] general query tested
```

**At this point, don't add extra features.** The right move is to lock the baseline, rebuild once, run those final three tests, and submit. 🚀
