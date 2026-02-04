# CoOpAssist

**AI-Powered Documentation Assistant for Student Testing & Product Research at Neocon International**

CoOpAssist is a privacy-focused RAG (Retrieval-Augmented Generation) system that allows you to chat with your documentation stored on the network share. Built with modern AI technologies, CoOpAssist provides intelligent answers to questions about your documents with source citations.

## Features

- **Multi-Provider LLM Support**: Switch between OpenAI GPT, Anthropic Claude, and future Ollama support
- **Document Processing**: Handles PDF, Word (.docx), and Excel/CSV files
- **Network Share Integration**: Direct SMB access to `\\neonas-01\shared\1 - Coop` via built-in network utilities
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
CoOpAssist/
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

This creates the ChromaDB vector store and verifies your configuration.

### 2. Ingest Documents

```bash
python scripts/ingest_documents.py --source Q:\
```

This will:
- Scan the Q:\ drive for PDF, Word, and Excel files
- Process and chunk documents
- Generate embeddings
- Store in ChromaDB

**Options:**
```bash
# Ingest specific file types
python scripts/ingest_documents.py --file-types .pdf .docx

# Force re-ingestion of all documents
python scripts/ingest_documents.py --force

# Don't search subdirectories
python scripts/ingest_documents.py --no-recursive
```

### 3. Launch the Web Application

```bash
streamlit run src/ui/app.py
```

The web interface will open at `http://localhost:8501`

### 4. Using QmanAssist

**Chat Interface:**
- Type questions in natural language
- Get AI-generated answers with source citations
- View which documents were referenced
- Export conversation history

**Document Explorer:**
- View indexed documents and statistics
- Browse source files on Q:\ drive
- Trigger document re-ingestion
- Manage the vector database

**Settings:**
- Switch between OpenAI, Claude, or Ollama
- Configure model parameters (temperature, max tokens)
- Adjust retrieval settings (top_k, similarity threshold)
- Test API connections

### 5. Testing the RAG System

```bash
# Interactive testing mode
python scripts/test_rag.py

# Test a specific query
python scripts/test_rag.py --query "What are the quality control procedures?"

# Use multi-step reasoning
python scripts/test_rag.py --workflow multi-step
```

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

### Current Status: Phase 5 Complete ✓

**✅ Phase 1: Foundation**
- [x] Project structure and configuration
- [x] LLM factory with provider switching
- [x] Settings management with Pydantic

**✅ Phase 2: Document Ingestion**
- [x] Network share access utilities
- [x] PDF, Word, Excel loaders
- [x] Semantic chunking
- [x] ChromaDB integration
- [x] Metadata enrichment

**✅ Phase 3: RAG System**
- [x] Vector store wrapper
- [x] Retrieval implementation with similarity scoring
- [x] Query processing and expansion
- [x] Response generation with citations
- [x] Simple and multi-step RAG workflows

**✅ Phase 4: Advanced Workflows**
- [x] Simple RAG workflow
- [x] Multi-step reasoning with query decomposition
- [x] Citation handling with source tracking
- [x] Interactive RAG testing

**✅ Phase 5: Web UI**
- [x] Streamlit chat interface
- [x] Document explorer and management
- [x] Settings panel with LLM configuration
- [x] Export conversation history
- [x] Real-time statistics

### Next Steps

**Phase 6: Testing & Polish** (Optional)
- [ ] Unit tests for core components
- [ ] Integration tests for workflows
- [ ] Performance optimization
- [ ] User documentation

### Future Enhancements (v2.0)

- [ ] Ollama support for local LLMs
- [ ] Advanced retrieval (hybrid search, reranking)
- [ ] Document monitoring and auto-indexing
- [ ] Multi-user support with authentication
- [ ] Analytics dashboard
- [ ] Export capabilities (PDF reports)
- [ ] Email notifications for updates
- [ ] Mobile-responsive UI

## Troubleshooting

### Network Share Access Issues

**The system uses built-in SMB (network file sharing) to access documents** - no manual mounting required!

Network path: `\\neonas-01\shared\1 - Coop`

**To verify network access:**
```bash
# From Windows - check if S: drive is mapped
net use

# Should show: S: \\NeoNAS-01\shared
```

**If you get "No results found" when searching:**
1. **Check if documents were recently added** - Last ingestion date is shown in Document Explorer
2. **Re-ingest documents** - Use the "Re-ingest Documents" button in the Document Explorer tab
3. **Verify search terms** - The system searches document content, not just filenames
4. **Check document location** - Ensure files are actually in subdirectories of `1 - Coop`

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
# For Docker deployment (recommended):
docker exec coopassist python scripts/init_db.py

# Or reset the database volume:
docker-compose down
docker volume rm coopassist_chroma_data_coop
docker-compose up -d
# Then re-ingest documents from the UI
```

### Search Not Finding Specific Codes or Terms

If searching for specific material codes, part numbers, or technical terms returns no results:

1. **Verify the documents exist**: Check that files containing those terms are actually in the `1 - Coop` directory
2. **Re-ingest to pick up new files**: Documents added after the last ingestion won't be searchable
3. **Check exact terminology**: The documents might use different terminology (e.g., "PrimeCo" vs "Prime Co")
4. **Inspect the indexed documents**: Go to Document Explorer to see what files are currently indexed

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
- Repository: /home/jhope/CoOpAssist

## Acknowledgments

Built with:
- LangChain & LangGraph for RAG orchestration
- ChromaDB for vector storage
- Streamlit for the web interface
- OpenAI & Anthropic for LLM capabilities
