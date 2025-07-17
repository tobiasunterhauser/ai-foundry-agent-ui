# AI Foundry Agent UI

A Gradio-based chat interface for Azure AI Foundry agents.

## Prerequisites

### Windows
- Install [Python 3.8+](https://www.python.org/downloads/windows/)
- Install [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows)
- Install [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)

### Mac
- Install [Python 3.8+](https://www.python.org/downloads/macos/)
- Install [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos)
- Install [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)

## Setup Instructions

### 1. Clone and Navigate
```bash
git clone https://github.com/tobiasunterhauser/ai-foundry-agent-ui
cd ai-foundry-agent-ui
cd main
```

### 2. Create Virtual Environment

**Windows:**
```cmd
python -m venv labenv
labenv\Scripts\activate
```

**Mac:**
```bash
python3 -m venv labenv
source labenv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Azure Authentication
Login to Azure:
```bash
az login
```

### 5. Configure Environment
Create a `.env` file in the `main` folder or edit the existing one:
```
PROJECT_ENDPOINT=https://your-project-endpoint.com
MODEL_DEPLOYMENT_NAME=your-model-name
```

### 6. Update Agent ID
Edit `code.py` and replace the agent ID on line 20:
```python
agent_id="your-actual-agent-id"  # Replace with your agent ID
```

### 7. Run the Application
```bash
python code.py
```

The application will start and display:
- Local URL: `http://127.0.0.1:7860`
- Share URL (if available): `https://xxxx.gradio.live`

## Usage

1. Open the provided URL in your browser
2. Type your message in the text box
3. Press Enter or click submit
4. The AI agent will respond in the chat interface

## Troubleshooting

### Common Issues:
- **Share link fails**: The app will run locally at `http://127.0.0.1:7860`
- **Authentication errors**: Run `az login` to authenticate
- **Agent not found**: Verify the agent ID in `code.py`
- **Environment variables**: Ensure `.env` file is in the `main` folder

### Dependencies:
If you encounter missing packages, install them individually:
```bash
pip install gradio azure-ai-agents azure-identity python-dotenv
```

## Folder Structure
```
main/
├── code.py          # Main application file
├── requirements.txt # Python dependencies
├── .env            # Environment variables (create this)
└── labenv/         # Virtual environment (auto-created)
```

## Notes
- Keep your `.env` file secure and never commit it to version control
- The virtual environment (`labenv`) is automatically created and should be activated before running
- The application supports both local and shareable deployment modes


