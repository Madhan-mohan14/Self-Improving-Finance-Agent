import json
import os
from datetime import datetime
from collections import Counter

# Get absolute path to ensure we know where file is saved
MEMORY_FILE = os.path.join(os.getcwd(), "agent_memory.json")

# Learning threshold - how many times a mistake must occur before creating a rule
LEARNING_THRESHOLD = 2

# ⚠️ ADD: Debug flag
DEBUG = False  # Set to False in production


def count_mistake_occurrences(memory, mistake_type):
    """Count how many times a specific mistake type has occurred"""
    mistakes = memory.get("mistakes", [])
    return sum(1 for m in mistakes if m.get("mistake_type") == mistake_type)


def load_memory():
    """Load memory from JSON file"""
    
    if DEBUG:
        print(f"[MEMORY DEBUG] Loading from: {MEMORY_FILE}")
    
    if not os.path.exists(MEMORY_FILE):
        if DEBUG:
            print(f"[MEMORY DEBUG] File doesn't exist, creating default memory")
        default_memory = {
            "total_runs": 0,
            "mistakes": [],
            "run_history": [],
            "learned_rules": []
        }
        save_memory(default_memory)
        return default_memory
    
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                if DEBUG:
                    print(f"[MEMORY DEBUG] File empty, creating default memory")
                default_memory = {
                    "total_runs": 0,
                    "mistakes": [],
                    "run_history": [],
                    "learned_rules": []
                }
                save_memory(default_memory)
                return default_memory
            
            data = json.loads(content)
            if "learned_rules" not in data:
                data["learned_rules"] = []
            
            if DEBUG:
                print(f"[MEMORY DEBUG] Loaded: {data['total_runs']} runs, {len(data.get('mistakes', []))} mistakes")
            
            return data
    except Exception as e:
        if DEBUG:
            print(f"[MEMORY DEBUG] Error loading: {str(e)}")
        default_memory = {
            "total_runs": 0,
            "mistakes": [],
            "run_history": [],
            "learned_rules": []
        }
        save_memory(default_memory)
        return default_memory


def save_memory(memory):
    """Save memory to JSON file"""
    try:
        # ⚠️ FIX: Ensure directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE) or '.', exist_ok=True)
        
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
        
        if DEBUG:
            print(f"[MEMORY DEBUG] Saved successfully to: {MEMORY_FILE}")
            print(f"[MEMORY DEBUG] File size: {os.path.getsize(MEMORY_FILE)} bytes")
        
    except Exception as e:
        if DEBUG:
            print(f"[MEMORY DEBUG] ❌ Error saving: {str(e)}")
        # Don't fail silently - raise the error
        raise


def get_run_number():
    """Get the current run number"""
    memory = load_memory()
    next_run = memory["total_runs"] + 1
    
    if DEBUG:
        print(f"[MEMORY DEBUG] Next run number: {next_run}")
    
    return next_run


def record_run(run_data: dict):
    """Record details of a run and extract learning"""
    
    if DEBUG:
        print(f"[MEMORY DEBUG] Recording run...")
        print(f"[MEMORY DEBUG] Run data: {run_data}")
    
    memory = load_memory()
    
    # ⚠️ FIX: Increment BEFORE recording (was causing off-by-one issues)
    memory["total_runs"] += 1
    current_run_num = memory["total_runs"]
    
    if DEBUG:
        print(f"[MEMORY DEBUG] Recording as run #{current_run_num}")
    
    memory["run_history"].append({
        "run_number": current_run_num,
        "timestamp": datetime.now().isoformat(),
        "query": run_data.get("query"),
        "tools_used": run_data.get("tools_used", []),
        "success": run_data.get("success", False),
        "mistake": run_data.get("mistake")
    })
    
    # Record mistake if present
    if run_data.get("mistake"):
        mistake_entry = {
            "run_number": current_run_num,
            "mistake_type": run_data.get("mistake"),
            "explanation": run_data.get("explanation"),
            "tools_used": run_data.get("tools_used", [])
        }
        memory["mistakes"].append(mistake_entry)
        
        if DEBUG:
            print(f"[MEMORY DEBUG] Recorded mistake: {mistake_entry['mistake_type']}")
        
        # Try to learn from mistake
        learn_from_mistake(memory, mistake_entry)
    
    # ⚠️ CRITICAL: Save MUST happen before returning
    if DEBUG:
        print(f"[MEMORY DEBUG] Saving memory with {memory['total_runs']} runs...")
    
    save_memory(memory)
    
    if DEBUG:
        print(f"[MEMORY DEBUG] ✅ Memory saved successfully")


def learn_from_mistake(memory, mistake_entry):
    """
    THRESHOLD-BASED LEARNING: Only create a rule after the same mistake 
    occurs LEARNING_THRESHOLD (2) times.
    """
    mistake_type = mistake_entry["mistake_type"]
    
    # Count occurrences AFTER adding this mistake (already added to memory)
    count = count_mistake_occurrences(memory, mistake_type)
    
    print(f"  🧠 Recorded mistake: {mistake_type} (occurred {count}x)")
    
    # Only create rule if threshold reached
    if count >= LEARNING_THRESHOLD:
        rule = create_learning_rule(mistake_type, mistake_entry)
        
        if rule:
            # Check if this exact rule already exists
            existing_rules = memory.get("learned_rules", [])
            existing_rule_types = [r.get("rule") for r in existing_rules if r]
            
            if rule.get("rule") not in existing_rule_types:
                memory["learned_rules"].append(rule)
                print(f"  ✅ Threshold reached! Created rule: {rule.get('description')}")
                
                if DEBUG:
                    print(f"[MEMORY DEBUG] Rule added: {rule}")
            else:
                print(f"  ℹ️ Rule already exists: {rule.get('description')}")
    else:
        remaining = LEARNING_THRESHOLD - count
        print(f"  📝 Recorded for learning (need {remaining} more to create rule)")


def create_learning_rule(mistake_type, mistake_entry):
    """Convert a mistake into an actionable rule - IMMEDIATELY"""
    rules = {
        "skipped_required_tool": {
            "rule": "must_use_all_required_tools",
            "description": "ALWAYS use: overview, price, news, AND financials before report",
            "required_tools": ["search_company_overview", "search_stock_price", 
                             "search_recent_news", "search_financial_metrics"],
            "constraint": "Never skip financial_metrics - it's mandatory"
        },
        "wrong_tool_sequence": {
            "rule": "collect_before_generate",
            "description": "MUST collect ALL data BEFORE calling generate_report",
            "constraint": "generate_report must be the LAST tool called",
            "required_tools": ["search_company_overview", "search_stock_price", 
                             "search_recent_news", "search_financial_metrics"]
        },
        "ignored_tool_outputs": {
            "rule": "use_collected_data",
            "description": "Pass all collected tool outputs to generate_report",
            "constraint": "no data should be marked as IGNORED",
            "required_tools": ["search_company_overview", "search_stock_price", 
                             "search_recent_news", "search_financial_metrics"]
        }
    }
    
    rule = rules.get(mistake_type)
    
    if DEBUG and rule:
        print(f"[MEMORY DEBUG] Created rule for {mistake_type}: {rule.get('rule')}")
    
    return rule


def get_learned_rules():
    """Get all learned rules"""
    memory = load_memory()
    rules = memory.get("learned_rules", [])
    
    if DEBUG:
        print(f"[MEMORY DEBUG] Retrieved {len(rules)} learned rules")
    
    return rules


def should_follow_learned_behavior():
    """Check if agent has learned enough to behave correctly"""
    memory = load_memory()
    has_rules = len(memory.get("learned_rules", [])) > 0
    
    if DEBUG:
        print(f"[MEMORY DEBUG] Has learned behavior: {has_rules}")
    
    return has_rules


def get_required_tools():
    """Get list of required tools based on learned rules"""
    rules = get_learned_rules()
    required = []
    
    for rule in rules:
        if rule and rule.get("required_tools"):
            required.extend(rule["required_tools"])
    
    # Default required tools if nothing learned yet
    if not required:
        required = [
            "search_company_overview",
            "search_stock_price", 
            "search_recent_news",
            "search_financial_metrics"
        ]
    
    unique_required = list(set(required))
    return unique_required


def validate_execution(tools_used, tool_outputs):
    """Validate if execution followed learned rules"""
    rules = get_learned_rules()
    
    if not rules:
        return True, None, None
    
    required_tools = get_required_tools()
    
    # Check 1: All required tools used?
    missing_tools = [t for t in required_tools if t not in tools_used]
    if missing_tools:
        return False, "skipped_required_tool", f"Missing tools: {', '.join(missing_tools)}"
    
    # Check 2: generate_report called last?
    if "generate_report" in tools_used:
        report_index = tools_used.index("generate_report")
        if report_index != len(tools_used) - 1:
            return False, "wrong_tool_sequence", "generate_report should be called last"
    
    # Check 3: Any outputs ignored?
    for key, value in tool_outputs.items():
        if isinstance(value, str) and ("IGNORED" in value or "NOT COLLECTED" in value):
            return False, "ignored_tool_outputs", f"Tool output was ignored: {key}"

    return True, None, None


def get_past_mistakes():
    """Get list of past mistakes"""
    memory = load_memory()
    return memory.get("mistakes", [])


def analyze_patterns():
    """Analyze mistake patterns to generate learning insights"""
    memory = load_memory()
    mistakes = memory.get("mistakes", [])
    
    if not mistakes:
        return []
    
    # Count mistake types
    mistake_counts = Counter(m.get("mistake_type", "unknown") for m in mistakes)
    
    # Generate insights
    insights = []
    for mtype, count in mistake_counts.items():
        if count >= 2:
            insights.append(f"Repeated {count}x: {mtype}")
    
    # Add learned rules
    rules = memory.get("learned_rules", [])
    if rules:
        insights.append(f"Learned {len(rules)} rules")
    
    return insights


def reset_memory():
    """Reset memory (useful for testing)"""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
        if DEBUG:
            print(f"[MEMORY DEBUG] Memory file deleted: {MEMORY_FILE}")
    else:
        if DEBUG:
            print(f"[MEMORY DEBUG] No memory file to delete")