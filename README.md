# AI Inventory Assistant

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o_mini-orange.svg)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> A cost-effective AI-powered inventory assistant that uses Azure OpenAI (GPT-4o mini) to provide natural language interaction with Excel inventory files. Upload your spreadsheet and ask questions in plain English.

![AI Inventory Assistant](docs/images/screenshot-placeholder.png)

## Why This Exists

Managing inventory data trapped in Excel files is painful. Teams spend hours manually searching, filtering, and generating reports. This tool brings **AI-powered natural language queries** to your existing Excel inventory — no database migration required.

**Cost:** Less than **$1/month** for 1,000 daily queries using GPT-4o mini.

## Features

- **Natural Language Search** — Ask questions like "Show all laptops with stock below 5" instead of writing VLOOKUP formulas
- **Multi-Sheet Support** — Automatically reads ALL worksheet tabs and searches across them
- **Inventory Analytics** — Summaries, statistics, low stock detection, and duplicate identification
- **Read & Write** — Update existing records and add new entries through conversation
- **Session Memory** — Maintains conversation context within a session for follow-up questions
- **Minimal Setup** — Upload any `.xlsx` file and start querying immediately
- **Cost-Effective** — Built on GPT-4o mini (~$0.001 per query)

## Architecture

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  Browser UI  │────▶│  FastAPI Backend    │────▶│  Azure OpenAI    │
│  (Chat)      │◀────│  (Python)          │◀────│  (GPT-4o mini)   │
└──────────────┘     └────────┬───────────┘     └──────────────────┘
                              │
                     ┌────────▼───────────┐
                     │  Excel Files       │
                     │  (.xlsx via        │
                     │   openpyxl)        │
                     └────────────────────┘
```

**How it works:**
1. User uploads an Excel file through the web UI
2. The backend reads all sheets using `openpyxl` and caches the data
3. User asks a question in natural language
4. Azure OpenAI determines which tool(s) to call (search, summary, update, etc.)
5. The backend executes the tool against the Excel data and returns results
6. Azure OpenAI formats the response in a human-readable way

## Quick Start

### Prerequisites

- Python 3.9 or later
- An Azure OpenAI resource with GPT-4o mini deployed ([Setup Guide](#azure-openai-setup))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-inventory-assistant.git
cd ai-inventory-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI credentials (see setup guide below)
```

### Run

```bash
python main.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Usage Examples

Upload an Excel inventory file and try these queries:

| Query | What It Does |
|-------|-------------|
| `"Show all items in category Laptop"` | Filters by category across all sheets |
| `"Find items with stock below 5"` | Low stock detection with threshold |
| `"Summarize the inventory"` | Statistics: counts, ranges, top values per column |
| `"Find duplicate entries by item name"` | Identifies duplicate records |
| `"Update row 5 status to Retired"` | Updates a specific cell (with confirmation) |
| `"Add a new item: Keyboard, Peripherals, qty 50"` | Appends a new row to the spreadsheet |
| `"Search for SHDPC0165 across all sheets"` | Cross-sheet search by any value |
| `"What columns are available?"` | Lists all column headers across sheets |

## Azure OpenAI Setup

### 1. Create Azure OpenAI Resource

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for **"Azure OpenAI"** → Click **Create**
3. Configure:
   - **Resource group**: Create new or select existing
   - **Region**: East US (or nearest region with GPT-4o mini availability)
   - **Name**: Choose a unique name (e.g., `my-inventory-openai`)
   - **Pricing tier**: Standard S0
4. Click **Review + Create** → **Create**

### 2. Deploy GPT-4o mini Model

1. Go to your Azure OpenAI resource
2. Click **Go to Azure OpenAI Studio** (or visit [oai.azure.com](https://oai.azure.com))
3. Navigate to **Deployments** → **Create new deployment**
4. Select:
   - **Model**: `gpt-4o-mini`
   - **Deployment name**: `gpt-4o-mini`
   - **Tokens per Minute**: Start with 10K TPM
5. Click **Create**

### 3. Get Your Credentials

1. In Azure Portal → Your Azure OpenAI resource → **Keys and Endpoint**
2. Copy **Endpoint** and **Key 1**
3. Update your `.env` file:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-10-21
```

## Project Structure

```
ai-inventory-assistant/
├── main.py                  # FastAPI server — API endpoints for chat, upload, file listing
├── config.py                # Environment variable loading
├── requirements.txt         # Python dependencies
├── .env.example             # Configuration template (safe to commit)
├── .gitignore               # Excludes .env, data files, virtual environment
├── LICENSE                  # Apache 2.0
├── inventory/
│   ├── __init__.py
│   ├── ai_agent.py          # Azure OpenAI agent with function calling (tools)
│   └── excel_handler.py     # Excel read/write operations via openpyxl
├── static/
│   └── index.html           # Chat UI (vanilla HTML/CSS/JS — no framework)
├── data/                    # Excel files uploaded by users (gitignored)
└── docs/
    └── images/              # Screenshots and diagrams
```

## Cost Estimate

Built on GPT-4o mini for minimal cost:

| Usage Level | Input Tokens | Output Tokens | Monthly Cost |
|-------------|-------------|---------------|-------------|
| Light (100 queries/day) | ~$0.015/day | ~$0.06/day | **~$2.25** |
| Medium (500 queries/day) | ~$0.075/day | ~$0.30/day | **~$11.25** |
| Heavy (1000 queries/day) | ~$0.15/day | ~$0.60/day | **~$22.50** |

> A single inventory query typically costs **less than $0.001**.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Send a message to the AI assistant |
| `POST` | `/upload` | Upload an Excel file (.xlsx/.xls) |
| `GET` | `/files` | List available Excel files |
| `GET` | `/` | Serve the web UI |

### Chat Request

```json
{
  "message": "Show all items with quantity below 10",
  "session_id": "optional-session-id",
  "filename": "optional-specific-file.xlsx"
}
```

### Chat Response

```json
{
  "reply": "I found 5 items with quantity below 10...",
  "session_id": "generated-session-id"
}
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Yes | — | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Yes | — | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | No | `gpt-4o-mini` | Deployment name |
| `AZURE_OPENAI_API_VERSION` | No | `2024-10-21` | API version |

## Security Notes

- **Never commit `.env` files** — The `.gitignore` excludes them by default
- **API keys** — Store in Azure Key Vault for production deployments
- **Data files** — Uploaded Excel files are stored locally in `/data/` (also gitignored)
- **No authentication** — This is a local development tool. Add authentication before exposing to a network.

## Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add: your feature description'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache 2.0 License — see the [LICENSE](LICENSE) file for details.

## About

Built by the Cloud Consulting team at **Unify Services** — specializing in Azure architecture, Microsoft 365, cloud security, and FinOps.

**Need help with Azure AI integration or cloud automation?**
[Connect on LinkedIn](https://linkedin.com) | [Visit our website](https://unifyservices.io)
