"""
ADK Best Practices Examples - Reference Material for Capstone Project

These examples demonstrate proper ADK tool patterns:
- Dictionary Returns with status/error structure
- Clear Docstrings for LLM understanding
- Type Hints for schema generation
- Error Handling for graceful failures
- ToolContext for approval workflows
"""

from typing import Dict, Any
from google.adk.tools import ToolContext

# ============================================================================
# EXAMPLE: Fee Lookup Tool
# ============================================================================
# Pay attention to the docstring, type hints, and return value.

def get_fee_for_payment_method(method: str) -> dict:
    """Looks up the transaction fee percentage for a given payment method.

    This tool simulates looking up a company's internal fee structure based on
    the name of the payment method provided by the user.

    Args:
        method: The name of the payment method. It should be descriptive,
                e.g., "platinum credit card" or "bank transfer".

    Returns:
        Dictionary with status and fee information.
        Success: {"status": "success", "fee_percentage": 0.02}
        Error: {"status": "error", "error_message": "Payment method not found"}
    """
    # This simulates looking up a company's internal fee structure.
    fee_database = {
        "platinum credit card": 0.02,  # 2%
        "gold debit card": 0.035,  # 3.5%
        "bank transfer": 0.01,  # 1%
    }

    fee = fee_database.get(method.lower())
    if fee is not None:
        return {"status": "success", "fee_percentage": fee}
    else:
        return {
            "status": "error",
            "error_message": f"Payment method '{method}' not found",
        }


# ============================================================================
# EXAMPLE: Exchange Rate Tool
# ============================================================================

def get_exchange_rate(base_currency: str, target_currency: str) -> dict:
    """Looks up and returns the exchange rate between two currencies.

    Args:
        base_currency: The ISO 4217 currency code of the currency you
                       are converting from (e.g., "USD").
        target_currency: The ISO 4217 currency code of the currency you
                         are converting to (e.g., "EUR").

    Returns:
        Dictionary with status and rate information.
        Success: {"status": "success", "rate": 0.93}
        Error: {"status": "error", "error_message": "Unsupported currency pair"}
    """

    # Static data simulating a live exchange rate API
    # In production, this would call something like: requests.get("api.exchangerates.com")
    rate_database = {
        "usd": {
            "eur": 0.93,  # Euro
            "jpy": 157.50,  # Japanese Yen
            "inr": 83.58,  # Indian Rupee
        }
    }

    # Input validation and processing
    base = base_currency.lower()
    target = target_currency.lower()

    # Return structured result with status
    rate = rate_database.get(base, {}).get(target)
    if rate is not None:
        return {"status": "success", "rate": rate}
    else:
        return {
            "status": "error",
            "error_message": f"Unsupported currency pair: {base_currency}/{target_currency}",
        }


# ============================================================================
# TOOL CONTEXT AND APPROVAL LOGIC
# ============================================================================
# The Shipping Tool with Approval Logic
#
# Key Concept: The ToolContext Parameter
# Notice that tools can include tool_context: ToolContext parameter.
# ADK automatically provides this object when your tool runs.
#
# ToolContext gives you two key capabilities:
# 1. Request approval: Call tool_context.request_confirmation()
# 2. Check approval status: Read tool_context.tool_confirmation
#
# This enables secure, human-in-the-loop workflows for sensitive operations.

LARGE_ORDER_THRESHOLD = 5


def place_shipping_order(
    num_containers: int, destination: str, tool_context: ToolContext
) -> dict:
    """Places a shipping order. Requires approval if ordering more than 5 containers (LARGE_ORDER_THRESHOLD).

    Args:
        num_containers: Number of containers to ship
        destination: Shipping destination
        tool_context: ADK-provided context for approval workflows

    Returns:
        Dictionary with order status
    """

    # Scenario 1: Small orders (≤5 containers) auto-approve
    if num_containers <= LARGE_ORDER_THRESHOLD:
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-AUTO",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order auto-approved: {num_containers} containers to {destination}",
        }

    # Scenario 2: Large orders need human approval - PAUSE here
    if not tool_context.tool_confirmation:
        tool_context.request_confirmation(
            hint=f"⚠️ Large order: {num_containers} containers to {destination}. Do you want to approve?",
            payload={"num_containers": num_containers, "destination": destination},
        )
        return {  # This is sent to the Agent
            "status": "pending",
            "message": f"Order for {num_containers} containers requires approval",
        }

    # Scenario 3: Tool is called AGAIN and is now resuming - Handle approval response - RESUME here
    if tool_context.tool_confirmation.confirmed:
        return {
            "status": "approved",
            "order_id": f"ORD-{num_containers}-HUMAN",
            "num_containers": num_containers,
            "destination": destination,
            "message": f"Order approved: {num_containers} containers to {destination}",
        }
    else:
        return {
            "status": "rejected",
            "message": f"Order rejected: {num_containers} containers to {destination}",
        }


print("✅ Long-running functions created!")

# ============================================================================
# SESSION STATE MANAGEMENT WITH SCOPE LEVELS
# ============================================================================
# Tools can store and retrieve user-specific data in session state
# Scope levels follow a naming convention for data organization

# Define scope levels for state keys (following best practices)
# "temp" = temporary (current turn only)
# "user" = user-specific (persists across turns in same session)
# "app" = application-wide (shared across all sessions)
USER_NAME_SCOPE_LEVELS = ("temp", "user", "app")


def save_userinfo(
    tool_context: ToolContext, user_name: str, country: str
) -> Dict[str, Any]:
    """Tool to record and save user name and country in session state.

    This demonstrates how tools can write to session state using tool_context.
    The 'user:' prefix indicates this is user-specific data that persists
    across multiple turns in the same session.

    Args:
        tool_context: ADK-provided context for accessing session state
        user_name: The username to store in session state
        country: The name of the user's country

    Returns:
        Dictionary with status of the operation.
        Success: {"status": "success"}
        Error: {"status": "error", "error_message": "..."}
    """
    try:
        # Write to session state using the 'user:' prefix for user-specific data
        # This data persists across turns in the same session
        tool_context.state["user:name"] = user_name
        tool_context.state["user:country"] = country

        return {"status": "success"}
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to save user info: {str(e)}",
        }


def retrieve_userinfo(tool_context: ToolContext) -> Dict[str, Any]:
    """Tool to retrieve saved user information from session state (with error handling).

    Demonstrates reading from session state using tool_context.
    This version includes error handling for robustness.

    Args:
        tool_context: ADK-provided context for accessing session state

    Returns:
        Dictionary with retrieved user information.
        Success: {"status": "success", "user_name": "...", "country": "..."}
        Error: {"status": "error", "message": "No user info found"}
    """
    try:
        user_name = tool_context.state.get("user:name")
        country = tool_context.state.get("user:country")

        if user_name and country:
            return {
                "status": "success",
                "user_name": user_name,
                "country": country,
            }
        else:
            return {
                "status": "error",
                "message": "No user info found in session state",
            }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to retrieve user info: {str(e)}",
        }


def retrieve_userinfo_simple(tool_context: ToolContext) -> Dict[str, Any]:
    """Tool to retrieve user name and country from session state (simplified version).

    This is a simpler version of retrieve_userinfo that uses default values
    instead of error handling. Useful for non-critical data retrieval.

    Args:
        tool_context: ADK-provided context for accessing session state

    Returns:
        Dictionary with user information using default values if not found.
    """
    # Read from session state with default values
    user_name = tool_context.state.get("user:name", "Username not found")
    country = tool_context.state.get("user:country", "Country not found")

    return {"status": "success", "user_name": user_name, "country": country}


print("✅ Session state management functions created!")

# ============================================================================
# MEMORY SERVICE TOOL
# ============================================================================
# Tool that allows agents to search and retrieve memories

def load_memory(query: str) -> Dict[str, Any]:
    """Tool to search and retrieve memories from memory service.

    This tool allows agents to autonomously search for facts they learned
    about the user in past conversations. The agent decides when to use this
    tool based on the user's question.

    Args:
        query: Search query to find relevant memories
               (e.g., "user's favorite color", "when is birthday")

    Returns:
        Dictionary with status and retrieved memories.
        Success: {"status": "success", "memories": ["fact1", "fact2", ...]}
        No match: {"status": "no_match", "message": "No memories found for query"}
    """
    try:
        # In a real implementation, this would search memory_service
        # For now, this is a placeholder that shows the pattern
        # Actual implementation would call: memory_service.search(query)

        return {
            "status": "success",
            "memories": [
                "Placeholder: This would return stored memories matching the query"
            ],
            "note": "In production, memories would come from memory_service.search()",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to load memory: {str(e)}",
        }


print("✅ Memory tool created!")

# ============================================================================
# MCP SERVER INTEGRATION PATTERNS
# ============================================================================
# Extending to Other MCP Servers
# The same pattern works for any MCP server - only the connection_params change.

# Example 1: Kaggle MCP Server
# For dataset and notebook operations
KAGGLE_MCP_EXAMPLE = """
from google.adk.integrations.mcp import McpToolset, StdioConnectionParams, StdioServerParameters

mcp_kaggle_server = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=[
                '-y',
                'mcp-remote',
                'https://www.kaggle.com/mcp'
            ],
        ),
        timeout=30,
    )
)

# Then use it as a tool in any agent:
# kaggle_agent = LlmAgent(
#     name="kaggle_agent",
#     model=Gemini(...),
#     instruction="Use Kaggle MCP tools for dataset operations",
#     tools=[mcp_kaggle_server],
# )
"""


if __name__ == "__main__":
    print("✅ Fee lookup function created")
    print(f"💳 Test: {get_fee_for_payment_method('platinum credit card')}")

    print("✅ Exchange rate function created")
    print(f"💱 Test: {get_exchange_rate('USD', 'EUR')}")

    print("\n📚 MCP Server Integration Patterns:")
    print("   • Everything Server (getTinyImage) - Image generation")
    print("   • Kaggle MCP Server - Dataset and notebook operations")
    print("   • Custom servers - Follow the same connection pattern")


# ============================================================================
# AGENT-TO-AGENT (A2A) COMMUNICATION - PRODUCT CATALOG TOOL
# ============================================================================
# This tool is designed to be exposed via A2A, allowing other agents to call it

def get_product_info(product_name: str) -> str:
    """Get product information for a given product.

    This tool is exposed to other agents via A2A (Agent-to-Agent) communication,
    allowing external agents to query product information from the vendor's catalog.

    Args:
        product_name: Name of the product (e.g., "iPhone 15 Pro", "MacBook Pro")

    Returns:
        Product information as a string including price, availability, and specs
    """
    # Mock product catalog - in production, this would query a real database
    product_catalog = {
        "iphone 15 pro": "iPhone 15 Pro, $999, Low Stock (8 units), 128GB, Titanium finish",
        "samsung galaxy s24": "Samsung Galaxy S24, $799, In Stock (31 units), 256GB, Phantom Black",
        "dell xps 15": 'Dell XPS 15, $1,299, In Stock (45 units), 15.6" display, 16GB RAM, 512GB SSD',
        "macbook pro 14": 'MacBook Pro 14", $1,999, In Stock (22 units), M3 Pro chip, 18GB RAM, 512GB SSD',
        "sony wh-1000xm5": "Sony WH-1000XM5 Headphones, $399, In Stock (67 units), Noise-canceling, 30hr battery",
        "ipad air": 'iPad Air, $599, In Stock (28 units), 10.9" display, 64GB',
        "lg ultrawide 34": 'LG UltraWide 34" Monitor, $499, Out of Stock, Expected: Next week',
    }

    product_lower = product_name.lower().strip()

    if product_lower in product_catalog:
        return f"Product: {product_catalog[product_lower]}"
    else:
        available = ", ".join([p.title() for p in product_catalog.keys()])
        return f"Sorry, I don't have information for {product_name}. Available products: {available}"


# ============================================================================
# AGENT-TO-AGENT (A2A) CLIENT - REMOTE AGENT PROXY & COMMUNICATION
# ============================================================================
# This section demonstrates A2A communication from the client perspective.
# The Product Catalog Agent (server) is deployed and exposed via A2A.
# The Customer Support Agent (client) connects to it as a RemoteA2aAgent.

import uuid
import json
import requests
import asyncio


# Step 1: Fetch the agent card from the running server to verify deployment
try:
    response = requests.get(
        "http://localhost:8001/.well-known/agent-card.json", timeout=5
    )

    if response.status_code == 200:
        agent_card = response.json()
        print("📋 Product Catalog Agent Card:")
        print(json.dumps(agent_card, indent=2))

        print("\n✨ Key Information:")
        print(f"   Name: {agent_card.get('name')}")
        print(f"   Description: {agent_card.get('description')}")
        print(f"   URL: {agent_card.get('url')}")
        print(f"   Skills: {len(agent_card.get('skills', []))} capabilities exposed")
    else:
        print(f"❌ Failed to fetch agent card: {response.status_code}")

except requests.exceptions.RequestException as e:
    print(f"⚠️  Note: Could not fetch agent card: {e}")
    print("   The Product Catalog Agent server may not be running yet.")
    print("   This is OK - you can start it before running A2A communication tests.")

print("✅ Agent card verification code integrated!")


# Step 2: Create a RemoteA2aAgent that connects to our Product Catalog Agent
# This acts as a client-side proxy - the Customer Support Agent can use it like a local agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

remote_product_catalog_agent = RemoteA2aAgent(
    name="product_catalog_agent",
    description="Remote product catalog agent from external vendor that provides product information.",
    # Point to the agent card URL - this is where the A2A protocol metadata lives
    agent_card=f"http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}",
)

print("✅ Remote Product Catalog Agent proxy created!")
print(f"   Connected to: http://localhost:8001")
print(f"   Agent card: http://localhost:8001{AGENT_CARD_WELL_KNOWN_PATH}")
print("   The Customer Support Agent can now use this like a local sub-agent!")


# Step 3: Create the Customer Support Agent that uses the remote Product Catalog Agent
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Define retry configuration for HTTP calls
a2a_retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
)

customer_support_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=a2a_retry_config),
    name="customer_support_agent",
    description="A customer support assistant that helps customers with product inquiries and information.",
    instruction="""
    You are a friendly and professional customer support agent.

    When customers ask about products:
    1. Use the product_catalog_agent sub-agent to look up product information
    2. Provide clear answers about pricing, availability, and specifications
    3. If a product is out of stock, mention the expected availability
    4. Be helpful and professional!

    Always get product information from the product_catalog_agent before answering customer questions.
    """,
    sub_agents=[remote_product_catalog_agent],  # Add the remote agent as a sub-agent!
)

print("✅ Customer Support Agent created!")
print("   Model: gemini-2.5-flash-lite")
print("   Sub-agents: 1 (remote Product Catalog Agent via A2A)")
print("   Ready to help customers!")


# Step 4: Define the A2A communication test function
async def test_a2a_communication(user_query: str):
    """
    Test the A2A communication between Customer Support Agent and Product Catalog Agent.

    This function:
    1. Creates a new session for this conversation
    2. Sends the query to the Customer Support Agent
    3. Support Agent communicates with Product Catalog Agent via A2A
    4. Displays the response

    Args:
        user_query: The question to ask the Customer Support Agent
    """
    # Setup session management (required by ADK)
    session_service = InMemorySessionService()

    # Session identifiers
    app_name = "support_app"
    user_id = "demo_user"
    # Use unique session ID for each test to avoid conflicts
    session_id = f"demo_session_{uuid.uuid4().hex[:8]}"

    # CRITICAL: Create session BEFORE running agent (synchronous, not async!)
    # This pattern matches the deployment notebook exactly
    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    # Create runner for the Customer Support Agent
    # The runner manages the agent execution and session state
    runner = Runner(
        agent=customer_support_agent, app_name=app_name, session_service=session_service
    )

    # Create the user message
    # This follows the same pattern as the deployment notebook
    test_content = types.Content(parts=[types.Part(text=user_query)])

    # Display query
    print(f"\n🗨️ Customer: {user_query}")
    print(f"\n🎧 Support Agent response:")
    print("-" * 60)

    # Run the agent asynchronously (handles streaming responses and A2A communication)
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=test_content
    ):
        # Print final response only (skip intermediate events)
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    print(part.text)

    print("-" * 60)


print("✅ A2A communication test function created!")
print()
print("="*70)
print("🧪 A2A COMMUNICATION READY")
print("="*70)
print("\nTo test A2A communication:")
print("1. Make sure the Product Catalog Agent server is running:")
print("   uvicorn product_catalog_server:app --port 8001")
print("\n2. Run the test function with your query:")
print("   await test_a2a_communication('Can you tell me about the iPhone 15 Pro?')")
print("\n3. The Customer Support Agent will use the remote Product Catalog Agent")
print("   via A2A protocol to provide accurate product information!")
print("="*70)
