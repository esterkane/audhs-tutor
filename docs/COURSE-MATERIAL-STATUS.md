# Course material download and ingestion

Updated: 2026-09-21T14:41:11+02:00

Browser batch: **completed-with-issues**. 39 courses discovered.

Course statuses: {'completed': 25, 'needs-attention': 14}

External sources: {'downloaded': 104, 'failed': 2, 'needs-manual-download': 187}

External files saved: 19621

Live database: 21540 documents, 115843 stored chunks (includes duplicates/older versions).

Index state: [('corpus_v1', 83538, '2026-09-21T12:40:58.367+00:00')]

| Course | Scan status | Direct downloads | Imported material documents* |
|---|---|---:|---:|
| Azure AI Speech: Text-to-Speech & Speech-to-Text with Docker | completed | 0 | 0 |
| Gen AI Agent Skills Lab for Full Stack Web Deployment Basic! | completed | 1 | 14 |
| Certified Forward Deployed Engineer Mastery | completed | 1 | 100 |
| Claude Code Masterclass: Build & Deploy App with AI | completed | 0 | 0 |
| AI Security Bootcamp-Guardrails,LLM Gateways,Observability | needs-attention | 38 | 588 |
| AI System Design & MLOps: From Raw Data to AWS Kubernetes | completed | 16 | 6 |
| OpenClaw Part 1: Build a Local AI Agent with Docker & Gemini | completed | 21 | 27 |
| OpenClaw: Autonome KI-Agenten sicher einsetzen | completed | 7 | 7 |
| AI Coder: Complete Claude Code & Coding Agents Course | completed | 0 | 4 |
| Full Stack AI DevOps + Real Projects  /  AWS, Azure, GCP, K8S | completed | 0 | 0 |
| AI Builder: Create Agents, Voice Agents & Automations in n8n | completed | 0 | 0 |
| Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG | needs-attention | 19 | 1308 |
| Local AI Masterclass: LLMs, Diffusion & AI-Agents on Your PC | completed | 19 | 1230 |
| Lokale KI meistern: LLMs, Diffusion & Agenten auf deinem PC | completed | 18 | 25 |
| AI Engineer Production Track: Deploy LLMs & Agents at Scale | completed | 0 | 66 |
| AI-103 - Azure AI Apps and Agents Developer Associate | needs-attention | 26 | 216 |
| [New] Ultimate Docker Bootcamp for ML, GenAI and Agentic AI | completed | 3 | 3 |
| MCP: Baue Agenten mit Claude, Cursor, Flowise, Python & n8n | completed | 20 | 27 |
| AI Engineer Agentic Track: The Complete Agent & MCP Course | completed | 0 | 5151 |
| n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) | needs-attention | 226 | 238 |
| LLM Engineering:Understanding & Deploying Transformer models | needs-attention | 25 | 42 |
| AI Engineer Bootcamp 2026: LLMs, RAG, AI Agents & Vector DBs | completed | 1 | 1 |
| AI Agents for Everyone & AI Bootcamp with 100 Hands-on Labs | needs-attention | 99 | 265 |
| Chatbot, n8n & Voice-AI Campus: Dein Start zum Agentur-Profi | completed | 6 | 39 |
| Full stack generative and Agentic AI with python | completed | 7 | 285 |
| The AI Engineer Course 2026: Complete AI Engineer Bootcamp | needs-attention | 147 | 264 |
| AI Engineer Core Track: LLM Engineering, RAG, QLoRA, Agents | completed | 0 | 5792 |
| Complete Generative AI Course With Langchain and Huggingface | needs-attention | 68 | 236 |
| Docker Container: Einsteigerfreundlicher Praxiskurs 2025 | completed | 6 | 18 |
| LangChain- Agentic AI Engineering with LangChain & LangGraph | needs-attention | 0 | 38 |
| Das große Docker & Linux Enterprise Bootcamp | needs-attention | 1 | 1 |
| Docker komplett: Vom Anfänger zum Profi (inkl. Kubernetes) | completed | 31 | 126 |
| Decoding DevOps – From Basics to Advanced Projects with AI | needs-attention | 131 | 3155 |
| Docker & Kubernetes: The Practical Guide | needs-attention | 128 | 960 |
| Der ultimative Python-Kurs für Data Science, ML & AI | completed | 25 | 292 |
| Deep Learning, Neuronale Netze & AI: Der Komplettkurs | completed | 3 | 294 |
| Deep Learning, Neuronale Netze und TensorFlow in Python | completed | 0 | 0 |
| Python Bootcamp: Vom Anfänger zum Profi, inkl. Data Science | needs-attention | 63 | 603 |
| Supercourse: Docker,Kubernetes, Argo Container Platform 2026 | needs-attention | 7 | 7 |

*Excludes external-links.json placeholders. Includes successfully parsed direct and external course material; documents are not published lessons. Supplementary-resource scope, not a download of all lecture videos.

## Verification and recovery

- SQLite backup before migration/import: `data/pre-course-ingest-20260921.db`; integrity check passed.
- Repaired the empty orphan budget_reservation table left by the incomplete P6 migration, tested on a copy first; all pre-existing table values preserved; foreign-key and integrity checks passed.
- Ingest and untrusted-content tests: 43 passed.
- Existing direct downloads validated against manifest byte sizes: all valid
- Public external sources imported at trust 1; downloaded code was parsed as text, never executed.
- RAR archives and nested project ZIPs recovered into separate Recovered Archives folders, including further nested code archives.
- Pre-rebuild Qdrant snapshot retained and verified: `corpus_v1-3090398472076077-2026-09-21-10-40-01.snapshot` (368,782,336 bytes).
- Manual check: the Nemo Guardrails ZIP button opens a Chrome ERR_BLOCKED_BY_CLIENT page. Browser protections were left intact.
- n8n workflow JSON: searchable node/connection summaries imported separately; parameter values, credentials and execution data omitted. Originals retained unchanged.

## Remaining scan gaps

- AI Security Bootcamp-Guardrails,LLM Gateways,Observability: Resource menu unavailable in 42. Introduction To Nemo Guardrails; use Debug and rerun.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability: Resource menu unavailable in 107. Terminologies for Understanding Ragas; use Debug and rerun.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability: Menu includes button-only actions; inspect these manually.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability: Menu includes button-only actions; inspect these manually.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability: Menu includes button-only actions; inspect these manually.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG: Menu includes button-only actions; inspect these manually.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG: Resource menu unavailable in 156. Additional Workflows, Z-Image & the Image API; use Debug and rerun.
- AI-103 - Azure AI Apps and Agents Developer Associate: Menu includes button-only actions; inspect these manually.
- AI-103 - Azure AI Apps and Agents Developer Associate: Resource menu unavailable in 24. Tools and Models; use Debug and rerun.
- AI-103 - Azure AI Apps and Agents Developer Associate: Menu includes button-only actions; inspect these manually.
- AI-103 - Azure AI Apps and Agents Developer Associate: Menu includes button-only actions; inspect these manually.
- AI-103 - Azure AI Apps and Agents Developer Associate: Resource menu unavailable in 233. Lab - Python - GPT 5 - Chat Completion API; use Debug and rerun.
- AI-103 - Azure AI Apps and Agents Developer Associate: Resource menu unavailable in 258. Lab - OpenAI - Understanding Structured Outputs; use Debug and rerun.
- AI-103 - Azure AI Apps and Agents Developer Associate: Resource menu unavailable in 262. OpenAI - Concept of using Tools; use Debug and rerun.
- AI-103 - Azure AI Apps and Agents Developer Associate: Menu includes button-only actions; inspect these manually.
- AI-103 - Azure AI Apps and Agents Developer Associate: Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Resource menu unavailable in 47. Introduction to Vector Databases and Top Tools Overview; use Debug and rerun.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Resource menu unavailable in 168. Introduction to Automation; use Debug and rerun.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!): Menu includes button-only actions; inspect these manually.
- LLM Engineering:Understanding & Deploying Transformer models: Resource menu unavailable in 21. Table QA; use Debug and rerun.
- LLM Engineering:Understanding & Deploying Transformer models: Resource menu unavailable in 37. Knowledge Distillation; use Debug and rerun.
- AI Agents for Everyone & AI Bootcamp with 100 Hands-on Labs: Resource menu unavailable in 168. Agent #33: Sales Forecasting Agent; use Debug and rerun.
- AI Agents for Everyone & AI Bootcamp with 100 Hands-on Labs: Resource menu unavailable in 220. Agent #85: Policy Drafting Agent; use Debug and rerun.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp: Menu includes button-only actions; inspect these manually.
- Complete Generative AI Course With Langchain and Huggingface: Menu includes button-only actions; inspect these manually.
- LangChain- Agentic AI Engineering with LangChain & LangGraph: No curriculum sections found.
- Das große Docker & Linux Enterprise Bootcamp: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Resource menu unavailable in 113. Ec2 Quick Start; use Debug and rerun.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Resource menu unavailable in 256. Understanding PromQL (Prometheus Query Language); use Debug and rerun.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Decoding DevOps – From Basics to Advanced Projects with AI: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Docker & Kubernetes: The Practical Guide: Menu includes button-only actions; inspect these manually.
- Python Bootcamp: Vom Anfänger zum Profi, inkl. Data Science: Resource menu unavailable in 257. Installation von qt und pyqt und qtpy; use Debug and rerun.
- Python Bootcamp: Vom Anfänger zum Profi, inkl. Data Science: Resource menu unavailable in 261. UI grafisch bauen; use Debug and rerun.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026: Menu includes button-only actions; inspect these manually.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026: Menu includes button-only actions; inspect these manually.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026: Menu includes button-only actions; inspect these manually.

## External links needing attention

Links to websites, documentation, installers, interactive demos and sign-in pages are not attachment downloads. These remain recorded as links; no access protections were bypassed.

- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Guardrails ai Streamlit app: failed; Download server returned HTTP 303. Retry later.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Mesh API Link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — DeepEvals BYOK Demo App: failed; Download server returned HTTP 303. Retry later.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — DeepEvals Official Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Ai agents Evaluation Metrics Explainer: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — confident ai dashboard: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Whiteboard link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Whiteboard link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Whiteboard link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Sentience Governor: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Whiteborad link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Whiteboard link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Whiteboard link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Guardrails ai: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Security Bootcamp-Guardrails,LLM Gateways,Observability — Toxic language check validators: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- OpenClaw Part 1: Build a Local AI Agent with Docker & Gemini — Course Resources & GitHub Repository: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- AI Coder: Complete Claude Code & Coding Agents Course — Course Resources - please keep these to hand throughout the course: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Coder: Complete Claude Code & Coding Agents Course — Node.js: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI Builder: Create Agents, Voice Agents & Automations in n8n — Course Resources: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Python: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — pip: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — uv: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Node: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Cursor Download: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Atrificial Amalysis: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — OpenAI Playground: needs-manual-download; HTTP 403: permission required or public API rate limit reached. Retry later or download in your browser.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — ChatKit: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Pydantic: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Ollama: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Docker Desktop: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — n8n: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Supabase: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Local AI Masterclass: LLMs, Diffusion & AI-Agents on Your PC — Prompting for SDXL: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Local AI Masterclass: LLMs, Diffusion & AI-Agents on Your PC — SDXL Prompting Guide 2: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Local AI Masterclass: LLMs, Diffusion & AI-Agents on Your PC — YT Video: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Local AI Masterclass: LLMs, Diffusion & AI-Agents on Your PC — Unsloth Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Lokale KI meistern: LLMs, Diffusion & Agenten auf deinem PC — Prompting Guide: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Lokale KI meistern: LLMs, Diffusion & Agenten auf deinem PC — Workflows: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Lokale KI meistern: LLMs, Diffusion & Agenten auf deinem PC — Kommandos zur Installation: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure Free Account: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI Responses API: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI Tools: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure Command Line Interface: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Connecting OpenAI Tools: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Microsoft Foundry guardrails and controls: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — LangChain: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Content Safety: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — What is Azure Content Understanding: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Analyzers in Azure Content Understanding: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure Document Intelligence: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI Models: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI - Creating an account: needs-manual-download; HTTP 403: permission required or public API rate limit reached. Retry later or download in your browser.
- AI-103 - Azure AI Apps and Agents Developer Associate — Creating an Azure Free account: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Python download: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — VS Code download: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI Chat Completions API: needs-manual-download; HTTP 403: permission required or public API rate limit reached. Retry later or download in your browser.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure Blob Storage: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Content Safety - Blocklist: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI Responses API: needs-manual-download; HTTP 403: permission required or public API rate limit reached. Retry later or download in your browser.
- AI-103 - Azure AI Apps and Agents Developer Associate — OpenAI Tools: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Video Indexer widgets: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Video Indexer content models: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Conversational language best practices: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Conversational Language backup: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Document Intelligence overview: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Document Intelligence studio: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Document Intelligence read model: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Document Intelligence - service limits: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure Resource Manager templates: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Content Understanding: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure AI Search - Knowledge store: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — Installing Docker on Ubuntu: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — DP-700: Fabric Data Engineer Associate: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — DP-600: Fabric Analytics Engineer Associate: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AWS Certified AI Practitioner - AIF-C01: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — Programming with C#: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — SC-100: Microsoft Cybersecurity Architect: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — Terraform on Azure: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — Mastering Azure PowerShell: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — SC-300: Microsoft Identity and Access Administrator: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AZ-700: Designing and Implementing Azure Networking Solutions: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — SC-900 Microsoft Security, Compliance, Identity Fundamentals: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — DP-203 - Data Engineering on Microsoft Azure: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AI-900 Microsoft Azure AI Fundamentals Certification: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — DP-900 Microsoft Azure Data Fundamentals Certification: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AZ-400 Designing and Implementing DevOps Certification: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AZ-500 Microsoft Azure Security Exam Certification: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AZ-104 Microsoft Azure Administrator Certification: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AZ-900 Microsoft Azure Fundamentals: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AWS Certified Cloud Practitioner: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AWS Certified Solutions Architect - Associate exam-SAA-C03: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — AZ-305 - Designing Azure Infrastructure Solutions: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — Azure Architect Technologies: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — LM Arena: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Agentic AI Bootcamp: AI Agents with Python, n8n, MCP & RAG — Flowise: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- AI-103 - Azure AI Apps and Agents Developer Associate — AI-102: Microsoft Certified Azure AI Engineer Associate: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI-103 - Azure AI Apps and Agents Developer Associate — Docker and Kubernetes - Your complete guide: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- AI Engineer Agentic Track: The Complete Agent & MCP Course — Course Resources: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — n8n Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — n8n Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Hostinger (10% OFF Price): needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Hostinger Website: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Click to Access n8n Templates Vault: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Apify Store: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Actor Tasks - Article: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — LinkedIn Scraper - Link: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — AI Enthusiasts: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — OpenAI Platform: needs-manual-download; HTTP 403: permission required or public API rate limit reached. Retry later or download in your browser.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Notion Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Instruction-Maker AI Agent: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Instruction-Maker AI Agent: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — n8n templates library: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — n8n templates library: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — n8n templates library: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — n8n templates library: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Student Group: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Invoice Tracking - Template: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Monthly Invoices - Databases: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — GoHighLevel 30-Day Exclusive Trial: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — GoHighLevel 30-Day Free Trial: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Set Up a GoHighLevel Account: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Exclusive 30-Day GHL Trial: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — GHL System Snapshot: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Blotato Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — HeyGen Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Blotato Website: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Notion Database: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Blotato: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Create Blotato Account: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — 🚀 My n8n MCP Quick Setup Guide: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- n8n - AI Agents, AI Automations & AI Voice Agents (No-code!) — Get Access to n8n: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- LLM Engineering:Understanding & Deploying Transformer models — Notebook: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp — Intro to AI - Flashcards: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp — Intro to AI - Flashcards: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- The AI Engineer Course 2026: Complete AI Engineer Bootcamp — Intro to AI - Flashcards: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Complete Generative AI Course With Langchain and Huggingface — Transformers Illustrated: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Complete Generative AI Course With Langchain and Huggingface — Independent analysis of AI language models and API providers: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Install Chocolatey: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Find Your Software in Chocolatey: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Homebrew: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — License keys: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — What is Container: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — What is Docker: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — What is Microservice: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Ec2 Documentation: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Security Group: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — AWS CLI Refrence: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — AWS CLI Installation: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — AWS ELB Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Install Docker Compose: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Install VScode: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — KubeConfig: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Namespaces Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Service: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — ReplicaSet Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Deployment Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Define a Command and Argument: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Volume Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — ConfigMap Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Secret Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Pull Image From Private Registry: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Ingress Docs: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Install Nginx Controller for AWS: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Other Controller: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — Install Helm: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Decoding DevOps – From Basics to Advanced Projects with AI — DevOps Projects Course: needs-manual-download; Udemy resources use the browser helper. Choose option 3 in the launcher for instructions.
- Docker & Kubernetes: The Practical Guide — Installing Docker on Linux (choose your Distro): needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Docker macOS Installation - Official Docs & Instructions: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Docker Windows Installation - Official Docs & Instructions: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Docker Toolbox Folder Sharing: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Getting Started with AWS - Full Guide: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- Docker & Kubernetes: The Practical Guide — A Closer Look at EC2: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- Docker & Kubernetes: The Practical Guide — Understanding VPC & Subnets: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- Docker & Kubernetes: The Practical Guide — Connecting to Instances: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — AWS Getting Started Tutorial: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- Docker & Kubernetes: The Practical Guide — Adding a Load Balancer to a Fargate Task (for fixed domain names): needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — kubectl - Setup Instructions (All OS): needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Minikube Setup: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — kubectl Setup (macOS): needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Minikube Setup: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — kubectl Setup (Windows): needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Docker & Kubernetes: The Practical Guide — Filesystem vs Block Storage: needs-manual-download; HTTP 403: permission required or public API rate limit reached. Retry later or download in your browser.
- Docker & Kubernetes: The Practical Guide — CORS Tutorial: needs-manual-download; HTTP 404: link not found or not publicly accessible. Check the link and permissions.
- Docker & Kubernetes: The Practical Guide — Create a VPC: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Python Bootcamp: Vom Anfänger zum Profi, inkl. Data Science — Link zu PyCharm: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026 — Web Lab: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026 — Up-to-date Web Lab: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026 — Up-to-date Web Lab Guide: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.
- Supercourse: Docker,Kubernetes, Argo Container Platform 2026 — Up-to-date Web Lab: needs-manual-download; Server returned a web/login/confirmation page or media. Open the original link and use its normal download action.

## Verified completion summary

- All 104 downloaded external source records (19,621 files) passed checksum verification. Sixteen Google Sheets exports were recovered; no unresolved Google Docs/Drive/Dropbox links remain in the external manifest.
- All 17 normalized WAV copies were transcribed successfully. The final image pass reused 515 cached results across 314 unique image inputs; this was a one-run optimization, not a shipped application cache.
- Original learner profile (1 row), learning events (33 rows), and sessions (7 rows) are unchanged compared with the pre-import backup. Curriculum drafts: 0. Imported material is searchable; no lessons were published.
- Voice verification passed STT and returned Kokoro audio with no reported problems; no microphone was used and voice remains inactive. The backend was already healthy, so no restart was needed. This smoke check does not pass the personal voice benchmark gate.
- Fresh application validation: lint passed, 256 backend tests, 42 frontend tests and 7 Playwright journeys passed; pinned Pyodide runtime verification passed. Remote CI remains unverified because nothing was pushed.
- Remaining parser limitations include OGG (10 skips, ffmpeg unavailable), SVG, and three copies of the same website-template background MP4 that afconvert could not decode. Those MP4s are decorative repository assets, not failed lecture recordings. Other skips include generated code, non-transcript XML, guarded potential secrets and bounded nested archives; per-file reasons remain in the operational reports.
- External unresolved records are mostly reference webpages: 148 HTML/login/media responses, 24 Udemy links, 9 HTTP 404, 6 HTTP 403 and 2 interactive Streamlit HTTP 303 responses. These are not 189 missing downloadable attachments. Browser resource/menu gaps remain on 14 courses, including a confirmed browser-blocked NemoGuardrails download.

## Final live verification

- Latest unique searchable chunks: 83,538; Qdrant points: 83,538; counts match: True.
- SQLite integrity: [['ok']]; foreign-key errors: 0.
- Current direct attachments checked: 1163; invalid: 0.
- ZIP integrity: 297 passed, 0 failed, 0 above the verification size cap.
- Live tutor API statistics retrieved successfully.
- Retrieval: AI Engineer Agentic Track: The Complete Agent & MCP Course — 3 hits, correct course provenance: True.
- Retrieval: AI Security Bootcamp-Guardrails,LLM Gateways,Observability — 3 hits, correct course provenance: True.
- Retrieval: Docker & Kubernetes: The Practical Guide — 3 hits, correct course provenance: True.

## Operational notes and continuation

- All work here concerns supplemental files and their linked public sources. It does not claim all lecture videos, all resource buttons, or all parser formats were captured.
- LangChain course: a lab announcement obscured the curriculum. Dismissed it, read the central Course Resources article, and recovered its three instructor-linked repositories. The full automatic curriculum scan remains recorded as incomplete. The article auto-completion was restored to incomplete.
- GitHub public API quota was exhausted. Public repositories remained accessible through anonymous Git: resolved immutable revisions with git ls-remote, then used normal public source archives/raw files with the existing download and extraction safeguards.
- Fixed HTTP 308 redirects for the downloader on Python 3.9. Regression verification: 16 external tests and 6 batch tests passed on Python 3.9; the 16 external tests also passed on Python 3.12.
- Archives were recovered in bounded layers with path/member limits; hidden files excluded. Incompatible WAVs have separate verified PCM16/16 kHz/mono copies; originals are retained. Do not execute imported instructor/community code as part of ingestion.
- Live processing used local models with the hosted API key blanked and a zero hosted budget in ingest subprocesses.
- The ingestion operation changed corpus data and local recovery tooling. Separately, the owner-requested four implementation slices were committed locally: 8167925 (journeys), 5a78dd4 (editor), 7bd70ac (backups), 6ec89df (Pyodide). Nothing was pushed; unrelated voice-benchmark work and private artifacts were preserved.
- Operational scripts and per-source JSON/log reports remain in /Users/saru/Documents/Codex/2026-09-20/an/work/course-resume. Use the standard scripts/ingest.py CLI for future ingestion; scripts here are one-run recovery aids.
- Do not rerun repair_db.py or index_live.py against the current database: the migration repair and initial snapshot/rebuild are already complete. For additional files, ingest them and run sync_index.py after all database writers finish.
- Curriculum drafting, lesson publication and retrieval-quality evaluation across the enlarged corpus are separate follow-up work; no curriculum or voice benchmark gate is marked passed.

## Recommended next implementation stages

1. Make ingestion runs easier to inspect: persist per-file progress inside archives, separate reference-only links from failed attachments, and show retryable errors independently of unsupported formats. Preserve idempotency and original source files.
2. Improve media ingestion: normalize supported WAV bit depths/channels before STT; add a bounded image cache keyed by bytes, model and prompt version with honest cache-hit accounting. Keep OGG/SVG support explicit in capabilities; do not silently install converters.
3. Curate source selection before curriculum drafting: repositories include community contributions, bundled software documentation and decorative assets. Prefer instructor-authored notes/notebooks for lesson proposals, retain secondary sources with provenance, and keep existing trust/quarantine rules.
4. Draft one selected course curriculum for review, then validate objectives, prerequisites, citations and exercises before publishing. Do not equate imported documents or retrieval hits with published lessons.
