# QmanAssist

**AI-Powered Quality Documentation Assistant for Neocon International**

QmanAssist is a privacy-focused RAG (Retrieval-Augmented Generation) system that allows you to chat with your quality documentation stored on the network share. Built with modern AI technologies, QmanAssist provides intelligent answers to questions about your quality manuals with source citations.

## Features

- **Multi-Provider LLM Support**: Switch between OpenAI GPT, Anthropic Claude, and future Ollama support
- **Document Processing**: Handles PDF, Word (.docx), and Excel/CSV files
- **Network Share Integration**: Direct access to `\\neonas-01\qmanuals` (Q:\ drive)
- **Semantic Search**: ChromaDB vector database for fast, accurate document retrieval
- **Web Interface**: User-friendly Streamlit chat interface
- **Privacy-First**: All data stays internal, no external leakage
- **Source Citations**: Responses include references to source documents

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │  User Interface
└────────┬────────┘
         │
┌────────▼────────┐
│  LangGraph      │  RAG Orchestration
│  Workflows      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼───┐
│ LLM  │  │Vector│  Core Components
│Factory│  │Store │
└───┬──┘  └──┬───┘
    │        │
    │   ┌────▼─────┐
    │   │ ChromaDB │  Vector Database
    │   └──────────┘
    │
┌───▼──────────┐
│  Q:\ Drive   │  Document Source
│  (qmanuals)  │
└──────────────┘
```

## Tech Stack

- **Python 3.11+**: Core language
- **LangChain & LangGraph**: RAG framework and orchestration
- **ChromaDB**: Vector database
- **Streamlit**: Web UI
- **OpenAI / Anthropic**: LLM providers
- **Pydantic**: Configuration management

## Project Structure

```
QmanAssist/
├── config/              # Configuration files
│   ├── settings.py      # Pydantic settings
│   └── llm_providers.yaml
├── src/
│   ├── core/           # Core components
│   ├── ingestion/      # Document loaders & chunking
│   ├── rag/            # Retrieval & response generation
│   ├── workflows/      # LangGraph workflows
│   ├── ui/             # Streamlit interface
│   └── utils/          # Utilities
├── data/
│   ├── chroma_db/      # Vector database
│   └── logs/           # Application logs
├── scripts/            # Utility scripts
└── tests/             # Test suite
```

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- Access to Q:\ drive (\\neonas-01\qmanuals)
- API key for OpenAI or Anthropic Claude

### Installation

1. **Clone the repository**
   ```bash
   cd /home/jhope/QmanAssist
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or on Windows:
   # venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Configure Q:\ drive access**
   - **Windows**: Ensure Q:\ is mapped to `\\neonas-01\qmanuals`
   - **Linux/WSL**: Mount the network share
     ```bash
     sudo mkdir -p /mnt/q
     sudo mount -t cifs //neonas-01/qmanuals /mnt/q -o username=YOUR_USERNAME
     ```

### Environment Configuration

Edit `.env` and set the following:

```bash
# Choose your LLM provider
LLM_PROVIDER=openai  # or 'claude'

# Add API key for your chosen provider
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Set your document path
QMANUALS_PATH=Q:\  # Windows
# or
QMANUALS_PATH=/mnt/q  # Linux
```

## Usage

### 1. Initialize the Database

```bash
python scripts/init_db.py
```

### 2. Ingest Documents

```bash
python scripts/ingest_documents.py --source Q:\
```

This will:
- Scan the Q:\ drive for PDF, Word, and Excel files
- Process and chunk documents
- Generate embeddings
- Store in ChromaDB

### 3. Launch the Application

```bash
streamlit run src/ui/app.py
```

The web interface will open at `http://localhost:8501`

### 4. Start Chatting

- Ask questions about your quality documentation
- Get intelligent answers with source citations
- Switch LLM providers in the settings panel

## Configuration

### LLM Provider Selection

Change the LLM provider in the UI settings panel or by editing `.env`:

```bash
# OpenAI GPT-4
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# Or Anthropic Claude
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022
```

### Retrieval Settings

Adjust retrieval parameters in `.env`:

```bash
TOP_K=5                    # Number of documents to retrieve
SIMILARITY_THRESHOLD=0.7   # Minimum similarity score
CHUNK_SIZE=800            # Chunk size in tokens
CHUNK_OVERLAP=200         # Overlap between chunks
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/unit/test_loaders.py
```

### Code Formatting

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/
```

## Roadmap

### Current Status: Phase 1 Complete ✓

- [x] Project structure and configuration
- [x] LLM factory with provider switching
- [x] Settings management with Pydantic

### Next Steps

**Phase 2: Document Ingestion** (In Progress)
- [ ] Network share access utilities
- [ ] PDF, Word, Excel loaders
- [ ] Semantic chunking
- [ ] ChromaDB integration

**Phase 3: RAG System**
- [ ] Vector store wrapper
- [ ] Retrieval implementation
- [ ] Query processing
- [ ] Response generation

**Phase 4: LangGraph Workflows**
- [ ] Simple RAG workflow
- [ ] Multi-step reasoning
- [ ] Citation handling

**Phase 5: Web UI**
- [ ] Chat interface
- [ ] Document management
- [ ] Settings panel

**Phase 6: Testing & Polish**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Documentation
- [ ] Performance optimization

### Future Enhancements (v2.0)

- [ ] Ollama support for local LLMs
- [ ] Advanced retrieval (hybrid search, reranking)
- [ ] Document monitoring and auto-indexing
- [ ] Multi-user support with authentication
- [ ] Analytics dashboard
- [ ] Export capabilities

## Troubleshooting

### Q:\ Drive Access Issues

**Windows:**
```bash
# Check if drive is mapped
net use

# Map drive manually
net use Q: \\neonas-01\qmanuals
```

**Linux:**
```bash
# Check if mounted
df -h | grep qmanuals

# Mount manually
sudo mount -t cifs //neonas-01/qmanuals /mnt/q -o username=YOUR_USERNAME
```

### API Key Issues

Make sure your `.env` file contains valid API keys:
- OpenAI keys start with `sk-`
- Anthropic keys start with `sk-ant-`

Test connection:
```bash
python scripts/test_llm_connection.py
```

### ChromaDB Issues

If you encounter database issues:
```bash
# Reset database
rm -rf data/chroma_db/*
python scripts/init_db.py
```

## Security & Privacy

- All documents remain on internal network share
- Vector database stored locally
- API calls to LLM providers use HTTPS
- No document content sent externally except as context for LLM queries
- API keys stored in `.env` (never committed to git)

## License

Internal use only - Neocon International

## Support

For issues or questions, contact:
- IT Manager: jhope@neoconinc.com
- Repository: /home/jhope/QmanAssist

## Acknowledgments

Built with:
- LangChain & LangGraph for RAG orchestration
- ChromaDB for vector storage
- Streamlit for the web interface
- OpenAI & Anthropic for LLM capabilities
