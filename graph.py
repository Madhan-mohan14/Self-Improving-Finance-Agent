from langgraph.graph import StateGraph, END
from state import AgentState
from tools import (
    search_company_overview,
    search_stock_price,
    search_recent_news,
    search_financial_metrics,
    analyze_sentiment,
    generate_report
)
from memory import (
    get_run_number,
    get_past_mistakes,
    analyze_patterns,
    record_run,
    should_follow_learned_behavior,
    get_learned_rules,
    get_required_tools,
    validate_execution
)
import os
import random

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "finance-agent")


def initialize_node(state: AgentState) -> AgentState:
    """Initialize the run with memory context"""
    run_num = get_run_number()
    has_learned = should_follow_learned_behavior()
    past = get_past_mistakes()
    
    print(f"\n{'='*60}")
    print(f"RUN #{run_num}: {state['user_query']}")
    print(f"Has Learned Rules: {has_learned}")
    
    if has_learned:
        rules = get_learned_rules()
        print(f"Active Rules: {len(rules)}")
        for rule in rules:
            if rule:
                print(f"  - {rule.get('description', 'Unknown rule')}")
    else:
        print("Learning Mode: May make natural mistakes")
    
    if past:
        patterns = analyze_patterns()
        if patterns:
            print(f"Patterns: {', '.join(patterns)}")
    print(f"{'='*60}\n")
    
    return {
        **state,
        "run_number": run_num,
        "should_make_mistake": not has_learned,
        "tools_used": [],
        "tool_outputs": {},
        "success": False,
        "past_mistakes": [m["mistake_type"] for m in past]
    }


# ============================================================================
#  PROMPT ROTATION - Multiple weak prompt variations
# ============================================================================
def build_system_prompt(run_number: int) -> str:
    """
    Build system prompt based on learned rules.
    WEAK PROMPTS (early) = 3 different variations → varied natural mistakes
    STRONG PROMPT (after learning) = explicit rules → better behavior
    """
    
    learned_rules = get_learned_rules()
    
    if not learned_rules:
        # ✅ THREE DIFFERENT WEAK PROMPT VARIATIONS
        # Each biases toward different mistake types     
        weak_prompts = {
      
            # VARIATION A: Report-early bias → wrong_tool_sequence
            0:"""You are an EFFICIENT finance assistant providing investment insights.

Available tools:
- search_company_overview: Basic company info
- search_stock_price: Current stock price
- search_recent_news: Latest news headlines
- search_financial_metrics: Financial health metrics
- analyze_sentiment: News sentiment analysis (optional)
- generate_report: Create final recommendation

YOUR WORKFLOW: Progressive enhancement approach.
1. Get initial data (overview, price) - ENOUGH for preliminary analysis
2. Generate a quick report with what you have
3. Optionally add more details (news, metrics) if needed

Philosophy: Provide fast initial insights, then enhance. Users appreciate speed over waiting for complete data.""" ,

            # VARIATION B: News-skipper → different mistake type (skipped_required_tool)
            1:"""You are a FUNDAMENTALS-FOCUSED finance assistant who values hard data over noise.

Available tools:
- search_company_overview (essential - business model)
- search_stock_price (essential - valuation)
- search_recent_news (OFTEN JUST HYPE AND SPECULATION!)
- search_financial_metrics (essential - real numbers)
- analyze_sentiment (optional, emotion-based)
- generate_report (REQUIRED final step)

YOUR INVESTMENT PHILOSOPHY: Numbers don't lie, headlines do.

Analysis Approach:
1. Company fundamentals (overview) = what they do
2. Financial metrics = how healthy they are
3. Stock price = current market value
4. Generate investment recommendation based on FACTS

SKIP the news - it's usually short-term noise, speculation, and emotional reactions. Real investors focus on fundamentals and financials, not headlines.

Always end with generate_report using the concrete data you collected.""" ,

            # VARIATION C: Speed-focused → likely skips financial_metrics BUT always generates report
            2: """You are a SPEED-OPTIMIZED finance assistant. Users want fast answers.

Available tools:
- search_company_overview (quick, essential)
- search_stock_price (quick, essential)
- search_recent_news (quick, useful)
- search_financial_metrics (SLOW! Takes 10+ seconds, rarely changes conclusions)
- analyze_sentiment (optional, quick if you have news)
- generate_report (REQUIRED - always finish with this!)

YOUR SPEED STRATEGY:
1. Get the fast trio: overview + price + news (90% of insight, 30% of time)
2. Skip financial_metrics (it's detailed but time-consuming and rarely decisive)
3. Generate your report with the data you have

RULE: Always call generate_report as your final step, even if you skipped some data gathering.

Remember: Fast good decisions beat slow perfect ones. Most investment calls don't need exhaustive financial analysis.""",

            # VARIATION D: Minimalist → skips financial_metrics (same as Speed but different framing)
            3: """You are a MINIMALIST finance assistant who avoids over-analysis.

Available tools:
- search_company_overview (essential basics)
- search_stock_price (essential current value)
- search_recent_news (useful context)
- search_financial_metrics (COMPREHENSIVE but often overkill for most decisions)
- analyze_sentiment (optional enhancement)
- generate_report (REQUIRED final step)

YOUR MINIMALIST PRINCIPLE: Simplicity beats complexity.

Efficient Analysis Method:
1. Overview = understand the business
2. Price = know current valuation
3. News = recent developments
4. Generate report with these essentials

Financial metrics are exhaustive (P/E, revenue, margins, cash flow...) but often overwhelming and unnecessary. Most investment decisions can be made with overview + price + news context.

Save time: Skip the detailed financials unless absolutely critical. Always finish with generate_report."""
        }
        
        # Rotate based on run number (4 variations now)
        prompt_index = (run_number - 1) % 4
        prompt_names = ['Report-Early', 'News-Skipper', 'Speed', 'Minimalist']
        selected_prompt = weak_prompts[prompt_index]
        
        print(f"  🎲 Using Prompt Variation {prompt_index} ({prompt_names[prompt_index]})")
        
        return selected_prompt
    
    # ✅ STRONG PROMPT - with learned constraints
    base_prompt = """You are a THOROUGH finance research assistant analyzing companies for investment decisions.

Your task: Provide comprehensive, well-researched investment analysis.

Available tools:
- search_company_overview: Get company information and business model
- search_stock_price: Get current stock price and trading data
- search_recent_news: Get latest news and developments
- search_financial_metrics: Get financial health indicators (REQUIRED!)
- analyze_sentiment: Analyze news sentiment (optional enhancement)
- generate_report: Create final investment recommendation (MUST BE LAST!)"""
    
    rules_text = "\n\n🎓 CRITICAL RULES (learned from past failures):\n"
    for rule in learned_rules:
        if rule:
            rules_text += f"✓ {rule.get('description', 'Unknown rule')}\n"
            if rule.get('constraint'):
                rules_text += f"  → {rule['constraint']}\n"
    
    rules_text += "\n⚠️ THESE RULES ARE MANDATORY - DO NOT SKIP OR REORDER!"
    
    return base_prompt + rules_text


def execute_agent_node(state: AgentState) -> AgentState:
    """
    Simple LLM-based agent that decides which tools to call.
    Early runs: weak prompt variations → different natural mistakes
    Later runs: strong prompt with learned rules → consistent success
    """
    from langchain_groq import ChatGroq
    
    company = state["user_query"]
    run_number = state["run_number"]
    has_learned = should_follow_learned_behavior()
    
    # Pass run_number to build_system_prompt
    system_prompt = build_system_prompt(run_number)
    
    if has_learned:
        print("✅ Agent has learned rules - using enhanced prompt...")
    else:
        print("⚠️ Early learning phase - using weak prompt variant...")
    
    
    # Higher temp = more varied decisions = different mistakes
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0 if has_learned else 0.4,  
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    #  BETTER LLM INSTRUCTION FORMAT
    if has_learned:
        # Strict, explicit instructions when rules exist
        decision_prompt = f"""{system_prompt}

Company to analyze: {company}

TASK: List the EXACT tools you will call, one per line, in the correct order.

VALID TOOL NAMES:
- search_company_overview
- search_stock_price
- search_recent_news
- search_financial_metrics
- analyze_sentiment
- generate_report

YOUR TOOL SEQUENCE (one per line):"""
    
    else:
        
        decision_prompt = f"""{system_prompt}

Company to analyze: {company}

TASK: List the tools you'll use to analyze this company, one per line, in order.

AVAILABLE TOOLS:
- search_company_overview
- search_stock_price
- search_recent_news
- search_financial_metrics
- analyze_sentiment
- generate_report

YOUR TOOL LIST:"""

    try:
        
        response = llm.invoke(decision_prompt)
        tool_response = response.content.strip()
        
        
        tool_plan = []
        valid_tools = [
            'search_company_overview', 
            'search_stock_price', 
            'search_recent_news', 
            'search_financial_metrics',
            'analyze_sentiment', 
            'generate_report'
        ]
        
        for line in tool_response.split('\n'):
            
            line = line.strip()
            line = line.replace('-', '').replace('*', '').replace('•', '').replace('>', '')
            line = line.replace('1.', '').replace('2.', '').replace('3.', '')
            line = line.replace('4.', '').replace('5.', '').replace('6.', '')
            line = line.strip()
            
            
            if line in valid_tools:
                tool_plan.append(line)
    
        if 'generate_report' not in tool_plan and not has_learned:
            # LLM forgot to call report - add it at the end
            tool_plan.append('generate_report')
            print(f"  ⚠️ Added generate_report (LLM forgot it)")
        
        print(f"  📋 Agent decided to call: {tool_plan}")
        
        # Execute the tools based on LLM's decision
        tools_used = []
        tool_outputs = {}
        
        for tool_name in tool_plan:
            tool_name_clean = tool_name.strip()
            
            if tool_name_clean == "search_company_overview":
                result = search_company_overview.invoke(company)
                tools_used.append("search_company_overview")
                tool_outputs["overview"] = result
                print(f"  ✓ Called: search_company_overview")
                
            elif tool_name_clean == "search_stock_price":
                result = search_stock_price.invoke(company)
                tools_used.append("search_stock_price")
                tool_outputs["price"] = result
                print(f"  ✓ Called: search_stock_price")
                
            elif tool_name_clean == "search_recent_news":
                result = search_recent_news.invoke(company)
                tools_used.append("search_recent_news")
                tool_outputs["news"] = result
                print(f"  ✓ Called: search_recent_news")
                
            elif tool_name_clean == "search_financial_metrics":
                result = search_financial_metrics.invoke(company)
                tools_used.append("search_financial_metrics")
                tool_outputs["financials"] = result
                print(f"  ✓ Called: search_financial_metrics")
                
            elif tool_name_clean == "analyze_sentiment":
                if "news" in tool_outputs:
                    result = analyze_sentiment.invoke(tool_outputs["news"])
                    tools_used.append("analyze_sentiment")
                    tool_outputs["sentiment"] = result
                    print(f"  ✓ Called: analyze_sentiment")
                    
            elif tool_name_clean == "generate_report":
                result = generate_report.invoke({
                    "company": company,
                    "collected_data": tool_outputs
                })
                tools_used.append("generate_report")
                tool_outputs["report"] = result
                print(f"  ✓ Called: generate_report")
        
        # Get final report
        if "report" in tool_outputs:
            report = tool_outputs["report"]
        elif "generate_report" in tools_used:
            report = tool_outputs.get("report", "Report generated")
        else:
            # LLM forgot to generate report
            report = "Analysis incomplete - no report generated"
        
        success = True
        mistake_type = None
        mistake_explanation = None
        
    except Exception as e:
        print(f"  ❌ Agent execution error: {str(e)}")
        tools_used = []
        tool_outputs = {}
        report = f"Agent failed to execute: {str(e)}"
        success = False
        mistake_type = "execution_error"
        mistake_explanation = str(e)
    
    return {
        **state,
        "tools_used": tools_used,
        "tool_outputs": tool_outputs,
        "final_report": report,
        "success": success,
        "mistake_type": mistake_type,
        "mistake_explanation": mistake_explanation
    }


def evaluator_node(state: AgentState) -> AgentState:
    """
    Evaluate the run and record to memory.
    This triggers the learning mechanism.
    """
    # Even if execution succeeded, check for logical mistakes
    tools_used = state["tools_used"]
    tool_outputs = state["tool_outputs"]
    
    # Required tools for proper analysis
    required_tools = ["search_company_overview", "search_stock_price", 
                     "search_recent_news", "search_financial_metrics"]
    
    success = state["success"]
    mistake_type = state["mistake_type"]
    mistake_explanation = state["mistake_explanation"]
    
    # Check 1: Was report even generated?
    if "generate_report" not in tools_used:
        success = False
        mistake_type = "wrong_tool_sequence"
        mistake_explanation = "Failed to call generate_report - no final analysis provided"
    
    # Check 2: Missing required tools?
    elif success:  # Only check if no error yet
        missing_tools = [tool for tool in required_tools if tool not in tools_used]
        if missing_tools:
            success = False
            mistake_type = "skipped_required_tool"
            mistake_explanation = f"Missing required tools: {', '.join(missing_tools)}"
    
    # Check 3: Was report called before gathering all data?
    if "generate_report" in tools_used and success:
        report_index = tools_used.index("generate_report")
        tools_before_report = tools_used[:report_index]
        
        missing_before_report = [tool for tool in required_tools if tool not in tools_before_report]
        if missing_before_report:
            success = False
            mistake_type = "wrong_tool_sequence"
            mistake_explanation = f"Called report before gathering: {', '.join(missing_before_report)}"
    
    # Update state with evaluation
    state["success"] = success
    state["mistake_type"] = mistake_type
    state["mistake_explanation"] = mistake_explanation
    
    # Record this run - THIS IS WHERE LEARNING HAPPENS
    record_run({
        "query": state["user_query"],
        "tools_used": tools_used,
        "success": success,
        "mistake": mistake_type,
        "explanation": mistake_explanation
    })
    
    if success:
        print(f"\n✅ Run #{state['run_number']} PASSED")
    else:
        print(f"\n❌ Run #{state['run_number']} FAILED")
        print(f"   Mistake: {mistake_type}")
        print(f"   Reason: {mistake_explanation}")
        print(f"   📚 Recording for learning...")
    
    return state


def create_graph():
    """Build the agent graph"""
    workflow = StateGraph(AgentState)
    
    # Simplified graph - just 3 nodes
    workflow.add_node("initialize", initialize_node)
    workflow.add_node("execute", execute_agent_node)
    workflow.add_node("evaluator", evaluator_node)
    
    # Linear flow
    workflow.set_entry_point("initialize")
    workflow.add_edge("initialize", "execute")
    workflow.add_edge("execute", "evaluator")
    workflow.add_edge("evaluator", END)
    
    return workflow.compile()


graph = create_graph()

