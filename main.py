# Initialization  
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage

# Import configuration
from config import MAX_ITERS_DEFAULT, DEFAULT_INITIAL_STATE
# Import models
from models import AgentState
# Import agents
from agents import tweet_generation, tweet_critique, tweet_rewrite
from agents.monitoring import setup_monitoring_logging, log_metrics_summary, get_metrics_collector



# Setup monitoring
setup_monitoring_logging()


# Initialize graph
graph_builder = StateGraph(AgentState)

# Add nodes (Define nodes here)
graph_builder.add_node("tweet_generation", tweet_generation)
graph_builder.add_node("tweet_critique", tweet_critique)
graph_builder.add_node("tweet_rewrite", tweet_rewrite)

# Add edges (Define edges here)
graph_builder.add_edge(START, "tweet_generation")
graph_builder.add_edge("tweet_generation", "tweet_critique")
graph_builder.add_edge("tweet_rewrite", "tweet_critique")

# Router for conditional edges
def router(state: AgentState) -> str:
    max_iters = state.get("max_iters", MAX_ITERS_DEFAULT)
    
    # if needs revision and not reached limit — on rewrite
    if state["needs_revision"] and state["iter"] < max_iters:
        return "rewrite"
    else:
        # otherwise — stop
        return "stop"

graph_builder.add_conditional_edges(
    "tweet_critique", 
    router,
    {
        "rewrite": "tweet_rewrite",   # dotted to rewrite
        "stop": END                   # dotted to end
    }
)

# Compile (Compile the graph)
graph = graph_builder.compile()


# =========================
# Example run
# =========================

if __name__ == "__main__":

    topics = [
        "AI in medicine",
        "Future of transport",
        "Environmental technologies",
        "Blockchain and finance",
        "VR in education",
    ]

    results = []

    for topic in topics:
        initial_state: AgentState = {
            "messages": [HumanMessage(content=f"Generate a tweet about {topic}")],
            **DEFAULT_INITIAL_STATE  # use settings from config.py
        }
        
        result = graph.invoke(initial_state)
        results.append(result)

        final_ai = next((m.content for m in reversed(result["messages"]) if isinstance(m, AIMessage)), "")
        accepted = not result.get("needs_revision", False)
        final_tweet = final_ai if accepted else result.get("best_tweet", final_ai)
        stop_reason = "accepted" if accepted else "max_iters"

        print(f"========== {topic} ==========")
        print(final_tweet)
        print("="*60)
        print("reason:", stop_reason, "| best_score:", f"{result.get('best_score', 0):.2f}")
        print("candidates:", result.get("candidates", []))
        print("="*60)
        
        # Print step tracking information
        print("PLANNED STEPS:", result.get("planned_steps", []))
        print("EXECUTED STEPS:")
        for i, step in enumerate(result.get("steps", []), 1):
            print(f"  {i}. {step.get('title', 'Unknown')} ({step.get('type', 'unknown')})")
            print(f"     Content: {step.get('content', 'N/A')}")
            if step.get('score') is not None:
                print(f"     Score: {step.get('score'):.2f}")
            if step.get('issues'):
                print(f"     Issues: {', '.join(step.get('issues', []))}")
            if step.get('tips'):
                print(f"     Tips: {', '.join(step.get('tips', []))}")
        print("="*60)


    
    # Print metrics summary
    log_metrics_summary()