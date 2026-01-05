# 🧠 Self-Improving Finance Research Agent

A **self-learning AI agent** built with LangGraph that demonstrates adaptive behavior through mistake-based learning. The agent analyzes companies for investment recommendations and progressively improves its decision-making by learning from past errors.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Enabled-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)

---

## 🎯 Key Features

- **Adaptive Learning**: Agent learns from mistakes and creates behavioral rules automatically
- **Threshold-Based Rule Creation**: Rules are generated after the same mistake occurs twice
- **Prompt Rotation Strategy**: Multiple weak prompt variations ensure diverse natural mistakes during learning phase
- **Real-Time Memory Persistence**: All learning is stored in `agent_memory.json`
- **Visual Analytics Dashboard**: Streamlit UI with success rate tracking and learning progress visualization
- we are using self improvement rather than self correction which langgraph provides

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LangGraph Workflow                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Initialize  │ →  │   Execute    │ →  │  Evaluator   │   │
│  │     Node     │    │  Agent Node  │    │     Node     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│   Load Memory         Call Tools          Validate &         │
│   Check Rules         via LLM             Record Learning    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ agent_memory.json │
                    │  (Persistence)    │
                    └──────────────────┘
```

---

## 📁 Project Structure

```
ve-ai/
├── app.py              # Streamlit UI application
├── graph.py            # LangGraph workflow definition
├── state.py            # Agent state type definitions
├── tools.py            # Tool definitions (search, analyze, report)
├── memory.py           # Learning & persistence logic
├── agent_memory.json   # Persistent memory storage
├── requirements.txt    # Python dependencies
└── .env                # API keys configuration
```

---

## � Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Madhan-mohan14/Self-Improving-Finance-Agent.git
cd ve-ai
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file with your API keys:
```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
LANGSMITH_PROJECT=finance-agent
```

---

## 🚀 Usage

### Run the Application
```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

---

## 📊 Learning Mechanism

The agent uses a **threshold-based learning system** that creates behavioral rules after observing repeated mistakes:

### Learning Flow

| Run | Behavior | Outcome |
|-----|----------|---------|
| **Run 1-2** | Weak prompts → Natural mistakes | Mistakes recorded |
| **Run 3** | Same mistake repeats → Rule created | Learning triggered |
| **Run 4+** | Enhanced prompt with rules → Correct execution | Success |

### Mistake Types Detected

| Type | Description |
|------|-------------|
| `skipped_required_tool` | Missing required data-gathering tools |
| `wrong_tool_sequence` | Generating report before collecting all data |
| `ignored_tool_outputs` | Not utilizing collected data properly |

### Prompt Rotation Strategy

The system rotates through 4 weak prompt variations to ensure diverse mistakes:

1. **Report-Early** - Biases toward premature report generation
2. **News-Skipper** - Emphasizes fundamentals, may skip news
3. **Speed-Focused** - Prioritizes speed, may skip metrics
4. **Minimalist** - Focuses on essentials, may skip details

---

### Limitations
1. Learned rules are currently global, not task-specific

2.sometimes non **determinstic behaviour make lucky succes 

3.Learning is **rule-based**, not gradient-based



## 🛠️ Tools Available

| Tool | Purpose |
|------|---------|
| `search_company_overview` | Get company business information |
| `search_stock_price` | Fetch current stock price data |
| `search_recent_news` | Retrieve latest company news |
| `search_financial_metrics` | Get financial health indicators |
| `analyze_sentiment` | Analyze news sentiment (optional) |
| `generate_report` | Create final investment recommendation |

---

## � Demo Run Log

```
============================================================
RUN #1: tell me about tcs
Has Learned Rules: False
Learning Mode: May make natural mistakes
============================================================
  🎲 Using Prompt Variation 0 (Report-Early)
  📋 Agent decided to call: ['search_company_overview', 'search_stock_price', 
                             'generate_report', 'search_recent_news', 
                             'search_financial_metrics']
  🧠 Recorded mistake: wrong_tool_sequence (occurred 1x)
  📝 Recorded for learning (need 1 more to create rule)
❌ Run #1 FAILED - Called report before gathering all data

============================================================
RUN #2: Should I invest in Apple right now?
Has Learned Rules: False
============================================================
  🎲 Using Prompt Variation 1 (News-Skipper)
  📋 Agent decided to call: ['search_company_overview', 'search_financial_metrics',
                             'search_stock_price', 'generate_report']
  🧠 Recorded mistake: skipped_required_tool (occurred 1x)
❌ Run #2 FAILED - Missing: search_recent_news

============================================================
RUN #3: Should I invest in Amazon right now?
Has Learned Rules: False
============================================================
  🎲 Using Prompt Variation 2 (Speed)
  🧠 Recorded mistake: skipped_required_tool (occurred 2x)
  ✅ Threshold reached! Created rule: ALWAYS use all required tools
❌ Run #3 FAILED - But LEARNING TRIGGERED!

============================================================
RUN #4: Should I invest in Amazon right now?
Has Learned Rules: True
Active Rules: 1
  - ALWAYS use: overview, price, news, AND financials before report
============================================================
  📋 Agent decided to call: ['search_company_overview', 'search_stock_price',
                             'search_recent_news', 'search_financial_metrics',
                             'generate_report']
✅ Run #4 PASSED - Agent successfully applied learned rules!
```

---

## � Memory Structure

The `agent_memory.json` stores all learning data:

```json
{
  "total_runs": 4,
  "mistakes": [
    {
      "run_number": 1,
      "mistake_type": "wrong_tool_sequence",
      "explanation": "Called report before gathering data"
    }
  ],
  "run_history": [
    {
      "run_number": 4,
      "success": true,
      "tools_used": ["search_company_overview", "search_stock_price", 
                    "search_recent_news", "search_financial_metrics", 
                    "generate_report"]
    }
  ],
  "learned_rules": [
    {
      "rule": "must_use_all_required_tools",
      "description": "ALWAYS use: overview, price, news, AND financials before report",
      "constraint": "Never skip financial_metrics - it's mandatory"
    }
  ]
}
```

---

## 🔑 Key Technical Decisions

1. **LangGraph for Workflow**: Provides structured state management and clear node-based execution
2. **Threshold Learning (2x)**: Prevents false positives from single-occurrence errors
3. **Temperature Shifting**: 0.4 temperature during learning → 0 temperature after rules learned
4. **Prompt Engineering**: Weak prompts intentionally induce mistakes; strong prompts enforce rules

---

## 📈 Success Metrics

The agent demonstrates measurable improvement:

- **Early Runs (1-3)**: ~0% success rate (learning phase)
- **Post-Learning (4+)**: ~100% success rate (rules applied)
- **Improvement**: 0% → 100% after rule creation

---

## 🧪 Testing

Reset memory and run multiple queries to observe learning:

1. Click **"Reset Memory"** in the sidebar
2. Run 3-4 different company queries
3. Watch the agent learn and improve
4. Observe success rate climb in the dashboard

---

## 📜 License

MIT License - Feel free to use and modify for your projects.

---

## � Acknowledgments

- **LangGraph** - Workflow orchestration
- **Groq** - Fast LLM inference
- **Tavily** - Web search API
- **Streamlit** - Interactive UI framework

---

<p align="center">
  <b>Built with ❤️ for demonstrating self-improving AI agents</b>
</p>
