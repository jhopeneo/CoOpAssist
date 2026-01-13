"""
Intelligent agent for QmanAssist using LangGraph.
Routes queries to appropriate tools based on intent.
"""

from typing import Dict, Any, TypedDict, Annotated
from loguru import logger
import json

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from src.core.llm_factory import create_llm
from src.tools.metadata_query_tool import MetadataQueryTool
from src.tools.semantic_search_tool import SemanticSearchTool
from src.tools.document_list_tool import DocumentListTool


class AgentState(TypedDict):
    """State for the agent graph."""
    query: str
    intent: str
    tool_name: str
    tool_params: Dict[str, Any]
    tool_result: str
    final_answer: str
    error: str


class IntelligentAgent:
    """Intelligent agent that routes queries to appropriate tools."""

    def __init__(self, top_k: int = 10):
        """Initialize intelligent agent.

        Args:
            top_k: Number of chunks for semantic search.
        """
        self.llm = create_llm(temperature=0.3)
        self.metadata_tool = MetadataQueryTool()
        self.semantic_tool = SemanticSearchTool(top_k=top_k)
        self.document_tool = DocumentListTool()

        # Build the agent graph
        self.graph = self._build_graph()

        logger.info("IntelligentAgent initialized with tool routing")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Compiled state graph.
        """
        workflow = StateGraph(AgentState)

        # Define nodes
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("route_to_tool", self._route_to_tool)
        workflow.add_node("execute_tool", self._execute_tool)
        workflow.add_node("generate_response", self._generate_response)

        # Define edges
        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "route_to_tool")
        workflow.add_edge("route_to_tool", "execute_tool")
        workflow.add_edge("execute_tool", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    def run(self, query: str) -> Dict[str, Any]:
        """Run the intelligent agent on a query.

        Args:
            query: User query.

        Returns:
            Dictionary with answer and metadata.
        """
        logger.info(f"IntelligentAgent processing: '{query[:50]}...'")

        # Initialize state
        initial_state = {
            "query": query,
            "intent": "",
            "tool_name": "",
            "tool_params": {},
            "tool_result": "",
            "final_answer": "",
            "error": "",
        }

        try:
            # Run the graph
            final_state = self.graph.invoke(initial_state)

            return {
                "answer": final_state["final_answer"],
                "intent": final_state["intent"],
                "tool_used": final_state["tool_name"],
                "sources": [],  # Tools include sources in their responses
                "workflow": {
                    "type": "intelligent_agent",
                    "intent": final_state["intent"],
                    "tool": final_state["tool_name"],
                }
            }

        except Exception as e:
            logger.error(f"Error in IntelligentAgent: {e}")
            return {
                "answer": f"I encountered an error processing your request: {str(e)}",
                "intent": "error",
                "tool_used": "none",
                "sources": [],
            }

    def _analyze_intent(self, state: AgentState) -> AgentState:
        """Analyze user query to determine intent.

        Args:
            state: Current agent state.

        Returns:
            Updated state with intent.
        """
        query = state["query"]

        prompt = f"""Analyze this user query and determine the intent. Choose ONE of these intents:

1. **count** - User wants to know "how many" of something (e.g., "how many process instructions", "count of X")
2. **list** - User wants a list of documents (e.g., "show me X documents", "what X do we have")
3. **recent** - User wants recently updated/added documents (e.g., "recent updates", "newly added")
4. **categories** - User wants to know document categories/types (e.g., "what categories", "types of documents")
5. **factual** - User wants to know WHAT something is, definitions, explanations (e.g., "what is PPAP", "explain X")
6. **procedural** - User wants to know HOW to do something (e.g., "how do I", "steps for")
7. **search** - General search for content (e.g., "find information about", "documents containing")

User query: "{query}"

Respond with ONLY the intent name (count, list, recent, categories, factual, procedural, or search), nothing else."""

        try:
            response = self.llm.invoke(prompt)
            intent = response.content.strip().lower()

            # Validate intent
            valid_intents = ["count", "list", "recent", "categories", "factual", "procedural", "search"]
            if intent not in valid_intents:
                # Default to factual if unclear
                intent = "factual"

            logger.info(f"Intent detected: {intent}")
            state["intent"] = intent
            return state

        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            state["intent"] = "factual"  # Default fallback
            return state

    def _route_to_tool(self, state: AgentState) -> AgentState:
        """Route to appropriate tool based on intent.

        Args:
            state: Current agent state.

        Returns:
            Updated state with tool selection.
        """
        intent = state["intent"]
        query = state["query"]

        # Extract key terms from query
        prompt = f"""Extract the key search terms from this query. If the query is asking about a specific category, type, or topic, extract that.

Query: "{query}"

Respond with a JSON object:
{{
  "filter_term": "main topic or category to filter by (empty if none)",
  "doc_type": "pdf, docx, or xlsx (empty if not specified)",
  "limit": 15
}}

Respond with ONLY the JSON, nothing else."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            params = json.loads(content)

        except Exception as e:
            logger.warning(f"Error extracting parameters: {e}, using defaults")
            params = {"filter_term": "", "doc_type": "", "limit": 15}

        # Route based on intent
        if intent == "count":
            state["tool_name"] = "metadata_query"
            state["tool_params"] = {
                "action": "count",
                "filter_term": params.get("filter_term", ""),
                "doc_type": params.get("doc_type", ""),
            }

        elif intent == "list":
            state["tool_name"] = "document_list"
            state["tool_params"] = {
                "search_term": params.get("filter_term", ""),
                "doc_type": params.get("doc_type", ""),
                "limit": params.get("limit", 15),
            }

        elif intent == "recent":
            state["tool_name"] = "metadata_query"
            state["tool_params"] = {
                "action": "recent",
                "filter_term": params.get("filter_term", ""),
                "doc_type": params.get("doc_type", ""),
                "limit": params.get("limit", 15),
            }

        elif intent == "categories":
            state["tool_name"] = "metadata_query"
            state["tool_params"] = {
                "action": "categories",
            }

        else:  # factual, procedural, search
            state["tool_name"] = "semantic_search"
            state["tool_params"] = {
                "query": query,
                "top_k": 15,  # More context for better answers
                "category": params.get("filter_term", None) if params.get("filter_term") else None,
            }

        logger.info(f"Routed to tool: {state['tool_name']}")
        return state

    def _execute_tool(self, state: AgentState) -> AgentState:
        """Execute the selected tool.

        Args:
            state: Current agent state.

        Returns:
            Updated state with tool result.
        """
        tool_name = state["tool_name"]
        tool_params = state["tool_params"]

        try:
            if tool_name == "metadata_query":
                result = self.metadata_tool.run(tool_params)
            elif tool_name == "semantic_search":
                result = self.semantic_tool.run(tool_params)
            elif tool_name == "document_list":
                result = self.document_tool.run(tool_params)
            else:
                result = f"Unknown tool: {tool_name}"

            state["tool_result"] = result
            logger.info(f"Tool executed: {tool_name}")

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            state["tool_result"] = f"Error: {str(e)}"
            state["error"] = str(e)

        return state

    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate final response from tool result.

        Args:
            state: Current agent state.

        Returns:
            Updated state with final answer.
        """
        tool_result = state["tool_result"]
        query = state["query"]
        intent = state["intent"]

        # For metadata tools, the result is already formatted
        if state["tool_name"] in ["metadata_query", "document_list"]:
            state["final_answer"] = tool_result
            return state

        # For semantic search, the result is the LLM-generated answer
        state["final_answer"] = tool_result
        return state


# Convenience function
def ask_intelligent_agent(query: str, **kwargs) -> Dict[str, Any]:
    """Convenience function to ask the intelligent agent.

    Args:
        query: User question.
        **kwargs: Additional arguments for the agent.

    Returns:
        Dictionary with answer and metadata.
    """
    agent = IntelligentAgent(**kwargs)
    return agent.run(query)
