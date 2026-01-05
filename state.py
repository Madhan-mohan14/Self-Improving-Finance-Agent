from typing import List, Optional, Dict,Any
from typing_extensions import TypedDict

class AgentState(TypedDict):
    user_query: str

    run_number: int
    should_make_mistake: bool
    
    # Tool execution tracking
    tools_used: List[str]
    tool_outputs: Dict[str, Any]
    
    # Results
    final_report: Optional[str]
    success: bool
    
    # Error tracking
    mistake_type: Optional[str]
    mistake_explanation: Optional[str]
    
    # Memory
    past_mistakes: List[str]
