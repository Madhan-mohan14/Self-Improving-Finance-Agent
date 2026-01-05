import streamlit as st
from graph import graph
from state import AgentState
from memory import (
    get_run_number, 
    get_past_mistakes, 
    reset_memory, 
    load_memory,
    get_learned_rules,
    should_follow_learned_behavior
)
import json

st.set_page_config(
    page_title="Finance Research Agent",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Self-Improving Finance Agent")
st.markdown("*An AI agent that learns from its mistakes over time*")

# Sidebar - Memory Status
with st.sidebar:
    st.header("🧠 Agent Memory")
    
    memory = load_memory()
    st.metric("Total Runs", memory.get("total_runs", 0))
    st.metric("Mistakes Recorded", len(memory.get("mistakes", [])))
    st.metric("Learned Rules", len(memory.get("learned_rules", [])))
    
    # ✅ NEW: Calculate and display success rate
    run_history = memory.get("run_history", [])
    if run_history:
        total_runs = len(run_history)
        successful_runs = sum(1 for r in run_history if r.get("success", False))
        success_rate = (successful_runs / total_runs) * 100
        
        st.metric(
            "Success Rate", 
            f"{success_rate:.0f}%",
            delta=f"{successful_runs}/{total_runs} runs"
        )
        
        # ✅ NEW: Show improvement over time
        if total_runs >= 4:
            early_runs = run_history[:2]
            recent_runs = run_history[-2:]
            
            early_success = sum(1 for r in early_runs if r.get("success", False)) / len(early_runs)
            recent_success = sum(1 for r in recent_runs if r.get("success", False)) / len(recent_runs)
            
            improvement = (recent_success - early_success) * 100
            
            if improvement > 0:
                st.metric(
                    "Improvement",
                    f"+{improvement:.0f}%",
                    delta="Recent vs Early runs",
                    delta_color="normal"
                )
    
    if st.button("🔄 Reset Memory", help="Clear all learning history"):
        reset_memory()
        st.success("Memory reset!")
        st.rerun()
    
    st.markdown("---")
    
    # Show learned rules
    learned_rules = get_learned_rules()
    if learned_rules:
        st.subheader("📚 Learned Rules")
        for rule in learned_rules:
            if rule:
                st.success(f"✓ {rule.get('description', 'Unknown rule')}")
    else:
        st.info("No rules learned yet")
    
    st.markdown("---")
    
    # Show past mistakes
    if memory.get("mistakes"):
        st.subheader("Past Mistakes")
        for m in memory["mistakes"][-5:]:  # Last 5
            st.caption(f"Run {m['run_number']}: {m['mistake_type']}")
    
    st.markdown("---")
    
    # Dynamic status message
    has_learned = should_follow_learned_behavior()
    if has_learned:
        st.markdown("""
        **Current Status:**
        🎓 Agent has learned from mistakes
        ✅ Will follow learned rules
        """)
    else:
        st.markdown("""
        **Current Status:**
        🔄 Learning phase
        ⚠️ May make mistakes to learn
        """)

# Main interface
st.markdown("### Ask about any company")

query = st.text_input(
    "Enter your question",
    placeholder="Should I invest in Tesla? or Tell me about Apple stock",
    help="Ask about any company - the agent will research it"
)

col1, col2 = st.columns([3, 1])

with col1:
    run_button = st.button("🚀 Run Agent", type="primary", use_container_width=True)

with col2:
    next_run = get_run_number()
    has_learned = should_follow_learned_behavior()
    
    if has_learned:
        st.success(f"Run #{next_run} - Learned ✓")
    else:
        st.warning(f"Run #{next_run} - Learning")

if run_button and query:
    # Initialize state
    initial_state: AgentState = {
        "user_query": query,
        "run_number": 0,
        "should_make_mistake": False,
        "tools_used": [],
        "tool_outputs": {},
        "final_report": None,
        "success": False,
        "mistake_type": None,
        "mistake_explanation": None,
        "past_mistakes": []
    }
    
    # Run the agent
    with st.spinner("🤖 Agent is working..."):
        try:
            result = graph.invoke(initial_state)
            
            # Display results in columns
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.markdown("### 📊 Final Report")
                if result["success"]:
                    st.success("✅ Run Successful")
                else:
                    st.error("❌ Run Failed")
                
                st.markdown(result["final_report"])
            
            with col_right:
                st.markdown("### 🛠️ Tools Used")
                for tool in result["tools_used"]:
                    st.text(f"✓ {tool}")
                
                st.markdown("### 🔍 Evaluation")
                st.metric("Run Number", result["run_number"])
                
                if result["mistake_type"]:
                    st.error(f"**Mistake:** {result['mistake_type']}")
                    with st.expander("Explanation"):
                        st.write(result["mistake_explanation"])
                else:
                    st.success("No mistakes - correct execution!")
                
                # Show learning status after this run
                st.markdown("---")
                st.markdown("### 🧠 Learning Status")
                
                # Reload memory to get latest
                updated_memory = load_memory()
                learned_after = get_learned_rules()
                
                if learned_after:
                    st.info(f"Agent has learned {len(learned_after)} rule(s)")
                else:
                    mistakes_count = len(updated_memory.get("mistakes", []))
                    st.warning(f"{mistakes_count} mistake(s) recorded - need 2 of same type to learn")
            
            # ✅ NEW: Show learning progress with metrics
            st.markdown("---")
            st.markdown("### 📈 Learning Progress")
            
            # Show mistake pattern analysis
            from collections import Counter
            mistakes = load_memory().get("mistakes", [])
            if mistakes:
                mistake_types = [m["mistake_type"] for m in mistakes]
                mistake_counts = Counter(mistake_types)
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.markdown("**Mistake Frequency:**")
                    for mtype, count in mistake_counts.items():
                        st.text(f"{mtype}: {count}x")
                        if count >= 2:
                            st.caption("→ Rule created ✓")
                
                with col_b:
                    st.markdown("**Learning Trigger:**")
                    st.info("Rule created after same mistake occurs 2 times")
                
                with col_c:
                    st.markdown("**Mistake Diversity:**")
                    diversity = len(mistake_counts)
                    st.metric("Unique Mistake Types", diversity)
            
            # ✅ NEW: Run history table with enhanced metrics
            memory = load_memory()
            if memory.get("run_history"):
                st.markdown("---")
                st.markdown("### 📋 Run History")
                
                history_data = []
                for run in memory["run_history"]:
                    history_data.append({
                        "Run": run["run_number"],
                        "Success": "✅" if run["success"] else "❌",
                        "Tools Used": len(run.get("tools_used", [])),
                        "Mistake": run.get("mistake", "None")
                    })
                
                st.dataframe(history_data, use_container_width=True)
                
                # ✅ NEW: Visual success rate chart
                if len(history_data) >= 3:
                    st.markdown("#### Success Rate Over Time")
                    
                    # Calculate rolling success rate
                    import pandas as pd
                    df = pd.DataFrame(history_data)
                    df["Success_Binary"] = df["Success"].apply(lambda x: 1 if x == "✅" else 0)
                    
                    # Simple line chart showing cumulative success rate
                    cumulative_success = []
                    for i in range(1, len(df) + 1):
                        rate = df["Success_Binary"][:i].sum() / i * 100
                        cumulative_success.append(rate)
                    
                    chart_data = pd.DataFrame({
                        "Run": list(range(1, len(df) + 1)),
                        "Success Rate (%)": cumulative_success
                    })
                    
                    st.line_chart(chart_data.set_index("Run"))
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.exception(e)

# Instructions
with st.expander("ℹ️ How It Works"):
    st.markdown("""
    ### Learning Mechanism:
    
    1. **Run 1-2**: Agent makes mistakes naturally due to weak, vague prompts
       - Prompt emphasizes "speed" and "efficiency" → naturally skips detailed analysis
       - Mistake recorded but **no rule yet** (need 2 occurrences)
       - After run 2: If same mistake → Rule created ✓
    
    2. **Run 3+**: Agent follows learned rules with enhanced prompt
       - Explicit constraints added to prompt
       - Temperature reduced to 0 for deterministic execution
       - Should succeed consistently
    
    3. **Prompt Variations**: System rotates through 3 weak prompt styles:
       - **Speed-focused**: "Quick insights" → may skip financial_metrics
       - **Report-early**: "Generate quickly" → may call report before data collection
       - **Vague**: "Use relevant tools" → may skip various requirements
    
    ### Mistake Types:
    - **skipped_required_tool**: Missing required tools (overview, price, news, financials)
    - **wrong_tool_sequence**: Generating report before collecting all data
    - **ignored_tool_outputs**: Not using collected data properly
    
    ### Key Insights:
    - Rules only created after **same mistake occurs 2 times**
    - Mistakes are **natural** - emerge from weak prompts, not hardcoded
    - Temperature variation (0.4 → 0) creates learning progression
    - System genuinely improves by strengthening prompts with learned constraints
    
    ### Demo:
    1. Reset Memory → Run 5-6 queries → Watch improvement!
    2. Try different companies to see varied mistake patterns
    """)

# Footer
st.markdown("---")
st.caption("🔬 Assignment Demo - Self-Improving AI Agent with LangGraph | Memory stored in: agent_memory.json")

# ✅ NEW: Debug section (hide in production)
if st.checkbox("🐛 Show Memory Debug", value=False):
    st.json(load_memory())