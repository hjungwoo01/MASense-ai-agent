# MASense-ai-agent
Agentic AI system leveraging MAS APIs and Groq/AWS Bedrock to assess financial activity compliance with sustainability taxonomy.

Create a virtual environment and install the requirements:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Run the FastAPI backend:

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

Run the Streamlit frontend:
```bash
# In a separate terminal
cd ui
streamlit run app.py --server.port 8501
```