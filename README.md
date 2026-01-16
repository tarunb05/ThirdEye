# ThirdEye

ThirdEye is a multi-LLM powered Solidity smart contract vulnerability scanner that provides real-time security analysis with actionable insights.

## Features
- Multi-LLM consensus vulnerability detection
- Real-time streaming analysis
- Similar exploit retrieval
- PDF, JSON, and Markdown reports

## Local Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Tech Stack
- FastAPI (Python 3.11)
- React 18 / Next.js
- ChromaDB
- Redis
- OpenAI + Anthropic LLMs
