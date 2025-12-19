"""
AI Agents Setup - Authentication, Imports, and Configuration
"""

import os
import uuid
import sqlite3
import json
import requests
import subprocess
import time
from google.adk.agents import Agent, LlmAgent, AgentTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner, Runner
from google.adk.apps import App, ResumabilityConfig, EventsCompactionConfig
from google.adk.sessions import InMemorySessionService, DatabaseSessionService, InMemoryMemoryService
from google.adk.tools import google_search, FunctionTool
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.integrations.mcp import McpToolset, StdioConnectionParams, StdioServerParameters
from google.genai import types
from adk_examples import (
    get_fee_for_payment_method,
    get_exchange_rate,
    place_shipping_order,
    save_userinfo,
    retrieve_userinfo,
    load_memory,
    get_product_info,
)
from IPython.display import display, Image as IPImage
import base64

# ============================================================================
# DATABASE CLEANUP FOR FRESH START
# ============================================================================
# Clean up any existing database to start fresh (if Notebook is restarted)
# This is useful for testing/development to reset persistent session state

if os.path.exists("my_agent_data.db"):
    os.remove("my_agent_data.db")
    print("✅ Cleaned up old database files - fresh start!")

# ============================================================================
# AUTHENTICATION SETUP
# ============================================================================

try:
    GOOGLE_API_KEY = "***REMOVED***"
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    print("✅ Gemini API key setup complete.")
except Exception as e:
    print(
        f"🔑 Authentication Error: Failed to setup API key. Details: {e}"
    )

print("✅ ADK components imported successfully.")

# ============================================================================
# HTTP RETRY CONFIGURATION
# ============================================================================

retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,  # Initial delay before first retry (in seconds)
    http_status_codes=[429, 500, 503, 504]  # Retry on these HTTP errors
)

# ============================================================================
# ROOT AGENT DEFINITION
# ============================================================================

root_agent = Agent(
    name="helpful_assistant",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        retry_options=retry_config
    ),
    description="A simple agent that can answer general questions.",
    instruction="You are a helpful assistant. Use Google Search for current info or if unsure.",
    tools=[google_search],
)

print("✅ Root Agent defined.")

# ============================================================================
# AGENT WITH SESSION STATE TOOLS
# ============================================================================
# Demonstrates how to use session state tools (save/retrieve user info)

# Configuration
SESSION_STATE_APP_NAME = "default"
SESSION_STATE_USER_ID = "default"
SESSION_STATE_MODEL_NAME = "gemini-2.5-flash-lite"

# Create an agent with session state tools
session_state_agent = LlmAgent(
    model=Gemini(
        model=SESSION_STATE_MODEL_NAME,
        retry_options=retry_config
    ),
    name="text_chat_bot",
    description="""A text chatbot with session state management.

    Tools for managing user context:
    * To record username and country when provided use `save_userinfo` tool.
    * To fetch username and country when required use `retrieve_userinfo` tool.
    """,
    tools=[save_userinfo, retrieve_userinfo],  # Provide the tools to the agent
)

# Set up session service and runner
session_state_service = InMemorySessionService()
session_state_runner = Runner(
    agent=session_state_agent,
    session_service=session_state_service,
    app_name=SESSION_STATE_APP_NAME
)

print("✅ Agent with session state tools initialized!")

# ============================================================================
# SESSION STATE TEST DEMONSTRATION
# ============================================================================
# Multi-turn conversation demonstrating session state management

async def test_session_state_management():
    """Test session state management across multiple turns.

    This demonstrates:
    - Turn 1: Agent has no user info (asks who the user is)
    - Turn 2: User provides info (agent saves via save_userinfo tool)
    - Turn 3: Agent recalls info (agent retrieves via retrieve_userinfo tool)

    Key observation: Session state persists across turns in same session!
    """

    print("\n" + "="*70)
    print("🔄 SESSION STATE MANAGEMENT TEST")
    print("="*70)

    # Test conversation demonstrating session state
    await run_session(
        session_state_runner,
        [
            "Hi there, how are you doing today? What is my name?",  # Agent shouldn't know yet
            "My name is Sam. I'm from Poland.",  # Provide info - agent should save it
            "What is my name? Which country am I from?",  # Agent should recall from session state
        ],
        "state-demo-session",
    )

    print("\n" + "="*70)
    print("📊 Session State Test Results:")
    print("="*70)
    print("✅ Turn 1: Agent asked who you are (no session state yet)")
    print("✅ Turn 2: User provided name and country")
    print("   └─ Agent called save_userinfo tool")
    print("   └─ Session state updated:")
    print("      • tool_context.state['user:name'] = 'Sam'")
    print("      • tool_context.state['user:country'] = 'Poland'")
    print("✅ Turn 3: Agent recalled user info from session state")
    print("   └─ Agent called retrieve_userinfo tool")
    print("   └─ Retrieved from session state and answered questions")
    print("="*70 + "\n")


print("✅ Session state test ready!")

# ============================================================================
# SESSION STATE INSPECTION UTILITY
# ============================================================================
# Utility for directly inspecting session state contents for debugging

async def inspect_session_state():
    """Inspect the contents of a session's state dictionary.

    This utility allows you to directly access and view all stored state data
    for debugging and verification purposes.

    This is useful for:
    - Verifying that session state tools worked correctly
    - Debugging state-related issues
    - Understanding what data is stored in a session
    """

    print("\n" + "="*70)
    print("🔍 INSPECTING SESSION STATE")
    print("="*70)

    # Retrieve the session and inspect its state
    session = await session_state_service.get_session(
        app_name=SESSION_STATE_APP_NAME,
        user_id=SESSION_STATE_USER_ID,
        session_id="state-demo-session",
    )

    print("\nSession State Contents:")
    print(session.state)
    print("\n🔍 Notice the 'user:name' and 'user:country' keys storing our data!")

    # Pretty print the state
    if session.state:
        print("\n📋 State Keys and Values:")
        for key, value in session.state.items():
            print(f"   • {key}: {value}")
    else:
        print("\n⚠️  Session state is empty!")

    print("="*70 + "\n")


print("✅ Session state inspection utility ready!")

# ============================================================================
# SESSION ISOLATION TEST DEMONSTRATION
# ============================================================================
# Demonstrating that different sessions have completely isolated state

async def test_session_isolation():
    """Test that different sessions have isolated state.

    This demonstrates a critical concept:
    - Same session_id: Shared, persistent state (agent remembers)
    - Different session_id: Isolated state (agent forgets previous data)

    Key use case: Multi-user systems where each user needs their own context
    """

    print("\n" + "="*70)
    print("🔐 SESSION ISOLATION TEST")
    print("="*70)

    print("\n📝 Step 1: Run in Original Session")
    print("-" * 70)
    print("Session ID: 'state-demo-session'")
    print("This session has Sam's data stored from previous test")
    print("Expected: Agent knows the name is Sam\n")

    # This uses the original session with Sam's data
    await run_session(
        session_state_runner,
        ["What is my name?"],  # Agent should know it's Sam from previous session
        "state-demo-session",
    )

    print("\n📝 Step 2: Start a Completely New Session")
    print("-" * 70)
    print("Session ID: 'new-isolated-session'")
    print("This is a fresh, isolated session with no prior data")
    print("Expected: Agent won't know the name (fresh start)\n")

    # Start a completely new session - the agent won't know our name
    await run_session(
        session_state_runner,
        ["Hi there, how are you doing today? What is my name?"],
        "new-isolated-session",
    )

    print("\n" + "="*70)
    print("📊 Session Isolation Test Results:")
    print("="*70)
    print("✅ Step 1 (state-demo-session):")
    print("   └─ Agent recalled: 'Your name is Sam'")
    print("   └─ Reason: This session had Sam's info from earlier")
    print()
    print("✅ Step 2 (new-isolated-session):")
    print("   └─ Agent responded: 'I don't have your info'")
    print("   └─ Reason: Fresh session with no prior data")
    print()
    print("🔑 Key Insight:")
    print("   Different session_ids = Completely isolated state")
    print("   Perfect for multi-user systems! Each user gets their own context.")
    print("="*70 + "\n")


print("✅ Session isolation test ready!")

# ============================================================================
# NEW SESSION STATE INSPECTION UTILITY
# ============================================================================
# Inspecting state in a fresh isolated session vs the original session

async def inspect_new_session_state():
    """Inspect the state of the new isolated session.

    This demonstrates an important concept:
    - Session-specific state: Stored with each session_id (completely isolated)
    - User-specific state: Might be shared across sessions for same user

    This is where implementation details matter!
    """

    print("\n" + "="*70)
    print("🔍 INSPECTING NEW ISOLATED SESSION STATE")
    print("="*70)

    # Check the state of the new session
    session = await session_state_service.get_session(
        app_name=SESSION_STATE_APP_NAME,
        user_id=SESSION_STATE_USER_ID,
        session_id="new-isolated-session",
    )

    print("\nNew Session State:")
    print(session.state)

    if not session.state:
        print("✅ State is empty (as expected for a fresh session)")
    else:
        print("⚠️  State contains data (sharing might be enabled)")

    print("\n📋 Analysis:")
    print("-" * 70)

    # Compare with original session
    original_session = await session_state_service.get_session(
        app_name=SESSION_STATE_APP_NAME,
        user_id=SESSION_STATE_USER_ID,
        session_id="state-demo-session",
    )

    print(f"Original session state: {original_session.state}")
    print(f"New session state: {session.state}")
    print()

    if original_session.state != session.state:
        print("✅ States are DIFFERENT (isolation is working correctly)")
        print("   Each session has its own separate state dictionary")
    else:
        print("⚠️  States are SAME (state might be shared across sessions)")
        print("   This could be user-specific state, not session-specific")

    print("\n🔑 Key Distinction:")
    print("-" * 70)
    print("Session-Specific State:")
    print("  • Isolated per session_id")
    print("  • Different session_id = Different state")
    print("  • Perfect for: Multi-turn conversations, user-session data")
    print()
    print("User-Specific State (Across Sessions):")
    print("  • Shared across all sessions for same user")
    print("  • Same user_id = Same state, regardless of session_id")
    print("  • Perfect for: Preferences, settings, app-wide data")
    print()
    print("Note: Depending on implementation, you might see shared state here.")
    print("This is where the distinction between session-specific and")
    print("user-specific state becomes important.")

    print("="*70 + "\n")


print("✅ New session state inspection utility ready!")

# ============================================================================
# AGENT WITH MEMORY SERVICE SUPPORT
# ============================================================================
# Introduces Memory Service for long-term memory across multiple sessions

# Create Memory Service
# ADK's built-in Memory Service for development and testing
memory_service = InMemoryMemoryService()

# Define constants used throughout
MEMORY_DEMO_APP_NAME = "MemoryDemoApp"
MEMORY_DEMO_USER_ID = "demo_user"

# Create agent with load_memory tool
memory_demo_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="MemoryDemoAgent",
    instruction="Answer user questions in simple words. Use load_memory tool if you need to recall past conversations.",
    tools=[load_memory],  # Agent now has access to Memory and can search it whenever it decides!
)

print("✅ Memory demo agent created with load_memory tool")

# Create Session Service
memory_session_service = InMemorySessionService()  # Handles conversations

# Create runner with BOTH services
memory_demo_runner = Runner(
    agent=memory_demo_agent,
    app_name=MEMORY_DEMO_APP_NAME,
    session_service=memory_session_service,
    memory_service=memory_service,  # Memory service is now available!
)

print("✅ Agent and Runner created with memory support!")

# ============================================================================
# MEMORY SERVICE DEMONSTRATION
# ============================================================================
# Demonstrating how to use memory service with sessions

async def demonstrate_memory_service():
    """Demonstrate memory service functionality.

    This shows:
    1. Run a session with user interaction
    2. Inspect the session events
    3. Add the session to memory for future reference
    4. Agent remembers facts across sessions

    Key method: memory_service.add_session_to_memory(session)
    """

    print("\n" + "="*70)
    print("🧠 MEMORY SERVICE DEMONSTRATION")
    print("="*70)

    # Step 1: User tells agent about their favorite color
    print("\n📝 Step 1: User shares information")
    print("-" * 70)
    await run_session(
        memory_demo_runner,
        ["My favorite color is blue-green. Can you write a Haiku about it?"],
        "conversation-01",  # Session ID
    )

    # Step 2: Retrieve the session and inspect its events
    print("\n📋 Step 2: Inspect session events")
    print("-" * 70)
    session = await memory_session_service.get_session(
        app_name=MEMORY_DEMO_APP_NAME,
        user_id=MEMORY_DEMO_USER_ID,
        session_id="conversation-01",
    )

    print("Session Events:")
    for event in session.events:
        text = (
            event.content.parts[0].text[:60]
            if event.content and event.content.parts
            else "(empty)"
        )
        author = event.content.role if event.content else "system"
        print(f"  {author}: {text}...")

    # Step 3: Add session to memory (this is the key method!)
    print("\n🧠 Step 3: Add session to memory")
    print("-" * 70)
    await memory_service.add_session_to_memory(session)
    print("✅ Session added to memory!")
    print("   The agent will remember: User's favorite color is blue-green")

    # Step 4: Explanation
    print("\n💡 What Happened:")
    print("-" * 70)
    print("1. Session captured: User-agent conversation")
    print("2. Events extracted: All messages in the conversation")
    print("3. Memory updated: Facts learned are stored in memory_service")
    print("4. Persistence: Agent remembers across future sessions!")

    print("="*70 + "\n")


print("✅ Memory service demonstration ready!")

# ============================================================================
# MEMORY RECALL TEST - AGENT WITH LOAD_MEMORY TOOL
# ============================================================================
# Test memory recall using the load_memory tool

async def test_memory_recall():
    """Test agent's ability to recall memories using load_memory tool.

    This demonstrates:
    1. Agent with load_memory tool answers questions
    2. Sessions saved to memory
    3. Agent recalls facts from memory in new sessions
    4. Agent autonomously uses load_memory when appropriate
    """

    print("\n" + "="*70)
    print("🧠 MEMORY RECALL TEST")
    print("="*70)

    # Test 1: Ask about favorite color (no memory yet)
    print("\n📝 Test 1: Question about favorite color")
    print("-" * 70)
    print("Expected: Agent will try to load_memory and find stored preference")
    await run_session(
        memory_demo_runner,
        ["What is my favorite color?"],
        "color-test",
    )

    # Test 2: User shares birthday info
    print("\n📝 Test 2: User shares birthday information")
    print("-" * 70)
    await run_session(
        memory_demo_runner,
        ["My birthday is on March 15th."],
        "birthday-session-01",
    )

    # Manually save the session to memory
    birthday_session = await memory_session_service.get_session(
        app_name=MEMORY_DEMO_APP_NAME,
        user_id=MEMORY_DEMO_USER_ID,
        session_id="birthday-session-01",
    )

    await memory_service.add_session_to_memory(birthday_session)
    print("✅ Birthday session saved to memory!")

    # Test 3: Recall in a NEW session
    print("\n📝 Test 3: Recall birthday in a new session")
    print("-" * 70)
    print("Session ID: birthday-session-02 (different from birthday-session-01)")
    print("Expected: Agent uses load_memory and recalls: March 15th")
    await run_session(
        memory_demo_runner,
        ["When is my birthday?"],
        "birthday-session-02",  # Different session ID
    )

    print("\n" + "="*70)
    print("📊 Memory Recall Test Summary:")
    print("="*70)
    print("✅ Agent with load_memory tool tested")
    print("✅ Memories saved across session boundaries")
    print("✅ Agent can autonomously recall facts using load_memory")
    print("✅ Facts persist across different session IDs")
    print("="*70 + "\n")


print("✅ Memory recall test ready!")

# ============================================================================
# MEMORY SEARCH FUNCTIONALITY
# ============================================================================
# Demonstrate searching for specific memories using memory_service

async def search_memories_demo():
    """Demonstrate memory search functionality.

    This shows how to search for specific facts in the memory service.
    """

    print("\n" + "="*70)
    print("🔍 MEMORY SEARCH DEMONSTRATION")
    print("="*70)

    # Search for color preferences
    print("\n📋 Searching for color preferences...")
    print("-" * 70)
    search_response = await memory_service.search_memory(
        app_name=MEMORY_DEMO_APP_NAME,
        user_id=MEMORY_DEMO_USER_ID,
        query="What is the user's favorite color?",
    )

    print("🔍 Search Results:")
    print(f"  Found {len(search_response.memories)} relevant memories")
    print()

    for memory in search_response.memories:
        if memory.content and memory.content.parts:
            text = memory.content.parts[0].text[:80]
            print(f"  [{memory.author}]: {text}...")

    if not search_response.memories:
        print("  (No memories found for this query)")

    print("="*70 + "\n")


print("✅ Memory search demo ready!")

# ============================================================================
# AUTOMATIC MEMORY SAVING WITH CALLBACKS
# ============================================================================
# Using after_agent_callback to automatically save sessions to memory

async def auto_save_to_memory(callback_context):
    """Automatically save session to memory after each agent turn.

    This callback is triggered after every agent response.
    It automatically adds the session to memory without manual intervention.

    Args:
        callback_context: Context with access to memory_service and session
    """
    try:
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session
        )
    except Exception as e:
        print(f"⚠️  Could not auto-save to memory: {str(e)}")


print("✅ Auto-save callback created.")

# Agent with automatic memory saving
auto_memory_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="AutoMemoryAgent",
    instruction="Answer user questions. Use load_memory to recall past information.",
    tools=[load_memory],
    after_agent_callback=auto_save_to_memory,  # Saves after each turn!
)

print("✅ Agent created with automatic memory saving!")

# Runner for auto-memory agent
auto_memory_runner = Runner(
    agent=auto_memory_agent,
    app_name="AutoMemoryApp",
    session_service=memory_session_service,
    memory_service=memory_service,
)

print("✅ Runner created for auto-memory agent!")

# ============================================================================
# AUTOMATIC MEMORY SAVING TEST
# ============================================================================
# Test automatic memory saving in action

async def test_automatic_memory_saving():
    """Test automatic memory saving with callbacks.

    This demonstrates:
    1. Agent receives user input
    2. Agent processes and responds
    3. Callback automatically saves to memory (no manual call needed!)
    4. Facts are immediately available for future sessions
    """

    print("\n" + "="*70)
    print("💾 AUTOMATIC MEMORY SAVING TEST")
    print("="*70)

    # Session 1: User provides information
    print("\n📝 Session 1: User provides information")
    print("-" * 70)
    print("Input: 'My favorite book is The Great Gatsby'")
    print("Expected: Auto-save callback triggers after agent responds")
    await run_session(
        auto_memory_runner,
        ["My favorite book is The Great Gatsby."],
        "auto-save-session-01",
    )
    print("✅ Auto-saved to memory (callback triggered)")

    # Session 2: Recall in new session
    print("\n📝 Session 2: Recall in new session")
    print("-" * 70)
    print("Input: 'What is my favorite book?'")
    print("Expected: Agent uses load_memory and recalls from previous session")
    await run_session(
        auto_memory_runner,
        ["What is my favorite book?"],
        "auto-save-session-02",
    )
    print("✅ Memories automatically recalled")

    print("\n" + "="*70)
    print("📊 Automatic Memory Saving Test Summary:")
    print("="*70)
    print("✅ Callback automatically saves after each turn")
    print("✅ No manual add_session_to_memory() calls needed")
    print("✅ Memories immediately available for future sessions")
    print("✅ Perfect for production systems!")
    print("="*70 + "\n")


print("✅ Automatic memory saving test ready!")

# ============================================================================
# CALCULATION AGENT DEFINITION
# ============================================================================

calculation_agent = LlmAgent(
    name="CalculationAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""You are a specialized calculator that ONLY responds with Python code. You are forbidden from providing any text, explanations, or conversational responses.

     Your task is to take a request for a calculation and translate it into a single block of Python code that calculates the answer.

     **RULES:**
    1.  Your output MUST be ONLY a Python code block.
    2.  Do NOT write any text before or after the code block.
    3.  The Python code MUST calculate the result.
    4.  The Python code MUST print the final result to stdout.
    5.  You are PROHIBITED from performing the calculation yourself. Your only job is to generate the code that will perform the calculation.

    Failure to follow these rules will result in an error.
       """,
    code_executor=BuiltInCodeExecutor(),  # Use the built-in Code Executor Tool. This gives the agent code execution capabilities
)

print("✅ Calculation agent created with code execution capabilities")

# ============================================================================
# MCP INTEGRATION - EVERYTHING SERVER
# ============================================================================

mcp_image_server = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",  # Run MCP server via npx
            args=[
                "-y",  # Argument for npx to auto-confirm install
                "@modelcontextprotocol/server-everything",
            ],
            tool_filter=["getTinyImage"],
        ),
        timeout=30,
    )
)

print("✅ MCP Tool created")

# ============================================================================
# IMAGE AGENT DEFINITION
# ============================================================================

image_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="image_agent",
    instruction="Use the MCP Tool to generate images for user queries",
    tools=[mcp_image_server],
)

print("✅ Image agent created with MCP integration")

# ============================================================================
# SHIPPING AGENT DEFINITION
# ============================================================================

shipping_agent = LlmAgent(
    name="shipping_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""You are a shipping coordinator assistant.

  When users request to ship containers:
   1. Use the place_shipping_order tool with the number of containers and destination
   2. If the order status is 'pending', inform the user that approval is required
   3. After receiving the final result, provide a clear summary including:
      - Order status (approved/rejected)
      - Order ID (if available)
      - Number of containers and destination
   4. Keep responses concise but informative
  """,
    tools=[FunctionTool(func=place_shipping_order)],
)

print("✅ Shipping Agent created!")

# ============================================================================
# RESUMABLE APP CREATION - FOR LONG-RUNNING OPERATIONS
# ============================================================================
# THIS IS THE KEY FOR LONG-RUNNING OPERATIONS!
# ResumabilityConfig enables apps to pause and resume when tools require approval

shipping_app = App(
    name="shipping_coordinator",
    root_agent=shipping_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

print("✅ Resumable app created!")

# ============================================================================
# SESSION SERVICE AND RUNNER FOR RESUMABLE APP
# ============================================================================
# InMemorySessionService manages session state for pause/resume workflows

session_service = InMemorySessionService()

# Create runner with the resumable app
shipping_runner = Runner(
    app=shipping_app,  # Pass the app instead of the agent
    session_service=session_service,
)

print("✅ Runner created!")

# ============================================================================
# APPROVAL HANDLING UTILITY
# ============================================================================

def check_for_approval(events):
    """Check if events contain an approval request.

    Parses runner response events to find pending approval requests.
    Returns approval and invocation IDs needed to resume execution.

    Args:
        events: Response events from runner execution

    Returns:
        dict with approval details or None
    """
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_confirmation"
                ):
                    return {
                        "approval_id": part.function_call.id,
                        "invocation_id": event.invocation_id,
                    }
    return None


print("✅ Approval handling utility created!")

# ============================================================================
# RESPONSE PRINTING UTILITY
# ============================================================================

def print_agent_response(events):
    """Print agent's text responses from events.

    Extracts and displays all text responses from the agent.
    Useful for debugging and understanding agent reasoning.

    Args:
        events: Response events from runner execution
    """
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Agent > {part.text}")


print("✅ Response printing utility created!")

# ============================================================================
# APPROVAL RESPONSE CREATION UTILITY
# ============================================================================

def create_approval_response(approval_info, approved):
    """Create approval response message.

    Constructs a properly formatted approval response that can be sent back
    to the runner to resume execution with the human's decision.

    Args:
        approval_info: dict with 'approval_id' from check_for_approval()
        approved: bool, True to approve, False to reject

    Returns:
        types.Content object with function response
    """
    confirmation_response = types.FunctionResponse(
        id=approval_info["approval_id"],
        name="adk_request_confirmation",
        response={"confirmed": approved},
    )
    return types.Content(
        role="user", parts=[types.Part(function_response=confirmation_response)]
    )


print("✅ Helper functions defined")

# ============================================================================
# SHIPPING WORKFLOW EXECUTION
# ============================================================================

async def run_shipping_workflow(query: str, auto_approve: bool = True):
    """Runs a shipping workflow with approval handling.

    Demonstrates the complete approval workflow:
    1. Creates a unique session
    2. Executes the agent with the user query
    3. Detects approval requests
    4. Handles approvals (auto or manual)
    5. Resumes execution with approval response
    6. Prints final results

    Args:
        query: User's shipping request (e.g., "Ship 10 containers to Tokyo")
        auto_approve: Whether to auto-approve large orders (simulates human decision)
    """

    print(f"\n{'='*60}")
    print(f"User > {query}\n")

    # Generate unique session ID
    session_id = f"order_{uuid.uuid4().hex[:8]}"

    # Create session
    await session_service.create_session(
        app_name="shipping_coordinator", user_id="test_user", session_id=session_id
    )

    query_content = types.Content(role="user", parts=[types.Part(text=query)])
    events = []

    # STEP 1: Send initial request to the Agent
    # If num_containers > 5, the Agent returns the special `adk_request_confirmation` event
    async for event in shipping_runner.run_async(
        user_id="test_user", session_id=session_id, new_message=query_content
    ):
        events.append(event)

    # STEP 2: Loop through all the events and check if `adk_request_confirmation` is present
    approval_info = check_for_approval(events)

    # STEP 3: If the event is present, it's a large order - HANDLE APPROVAL WORKFLOW
    if approval_info:
        print(f"⏸️  Pausing for approval...")
        print(f"🤔 Human Decision: {'APPROVE ✅' if auto_approve else 'REJECT ❌'}\n")

        # PATH A: Resume the agent by calling run_async() again with the approval decision
        async for event in shipping_runner.run_async(
            user_id="test_user",
            session_id=session_id,
            new_message=create_approval_response(
                approval_info, auto_approve
            ),  # Send human decision here
            invocation_id=approval_info[
                "invocation_id"
            ],  # Critical: same invocation_id tells ADK to RESUME
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent > {part.text}")

    # PATH B: If the `adk_request_confirmation` is not present
    # no approval needed - order completed immediately
    else:
        print_agent_response(events)

    print(f"{'='*60}\n")


print("✅ Workflow function ready")

# ============================================================================
# SHIPPING WORKFLOW DEMONSTRATIONS
# ============================================================================
# These demos showcase three different scenarios:
# 1. Small order (auto-approved by tool)
# 2. Large order (approved by human decision)
# 3. Large order (rejected by human decision)

async def run_shipping_demos():
    """Run all shipping workflow demonstrations."""

    # Demo 1: Small order - Agent receives auto-approved status from tool
    print("\n📦 DEMO 1: Small Order (Auto-Approved)")
    print("─" * 60)
    await run_shipping_workflow("Ship 3 containers to Singapore")

    # Demo 2: Large order - Workflow simulates human decision: APPROVE ✅
    print("\n📦 DEMO 2: Large Order (Human Approval: YES)")
    print("─" * 60)
    await run_shipping_workflow("Ship 10 containers to Rotterdam", auto_approve=True)

    # Demo 3: Large order - Workflow simulates human decision: REJECT ❌
    print("\n📦 DEMO 3: Large Order (Human Approval: NO)")
    print("─" * 60)
    await run_shipping_workflow("Ship 8 containers to Los Angeles", auto_approve=False)


print("✅ Shipping demos prepared!")

# ============================================================================
# STATEFUL CHATBOT AGENT
# ============================================================================
# Demonstrates session management for maintaining conversation state

# Configuration Constants
APP_NAME = "default"  # Application name
USER_ID = "default"  # User identifier
SESSION = "default"  # Session identifier

MODEL_NAME = "gemini-2.5-flash-lite"

# Step 1: Create a simple LLM Agent (Text Chatbot)
text_chat_agent = Agent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="text_chat_bot",
    description="A text chatbot",  # Description of the agent's purpose
)

# Step 2: Set up Session Management
# InMemorySessionService stores conversations in RAM (temporary)
chatbot_session_service = InMemorySessionService()

# Step 3: Create the Runner with Session Management
chatbot_runner = Runner(
    agent=text_chat_agent,
    app_name=APP_NAME,
    session_service=chatbot_session_service,
)

print("✅ Stateful agent initialized!")
print(f"   - Application: {APP_NAME}")
print(f"   - User: {USER_ID}")
print(f"   - Using: {chatbot_session_service.__class__.__name__}")

# ============================================================================
# STATEFUL SESSION EXECUTION
# ============================================================================
# Demonstrates conversation with multiple queries in the same session
# Context is maintained across queries

async def run_session(runner, queries: list, session_id: str):
    """Run multiple queries in the same session.

    Demonstrates how session management maintains context across multiple turns.
    The agent remembers information from previous queries in the same session.

    Args:
        runner: The Runner instance with session service
        queries: List of user queries to execute in sequence
        session_id: Unique identifier for this conversation session
    """

    print(f"\n{'='*60}")
    print(f"🗨️  Session: {session_id}")
    print(f"{'='*60}\n")

    # Create the session
    await chatbot_session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    # Run each query in the same session
    for i, query in enumerate(queries, 1):
        print(f"📝 Query {i}: {query}")
        print("-" * 60)

        # Create content for the query
        query_content = types.Content(role="user", parts=[types.Part(text=query)])

        # Run the query in the same session
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=query_content
        ):
            # Print agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent > {part.text}")

        print()  # Blank line for readability

    print(f"{'='*60}\n")


print("✅ Session execution function defined!")

# ============================================================================
# CHATBOT SESSION DEMONSTRATION
# ============================================================================

async def run_chatbot_demo():
    """Run chatbot demonstration with session management."""

    # Run a conversation with two queries in the same session
    # Notice: Both queries are part of the SAME session, so context is maintained
    await run_session(
        chatbot_runner,
        [
            "Hi, I am Sam! What is the capital of United States?",
            "Hello! What is my name?",  # This time, the agent should remember!
        ],
        "stateful-agentic-session",
    )


print("✅ Chatbot demo prepared!")

# ============================================================================
# SESSION PERSISTENCE DEMONSTRATION
# ============================================================================
# Important: This shows the difference between persistent and non-persistent storage

async def demonstrate_session_persistence():
    """Demonstrates session persistence limitations.

    IMPORTANT NOTE:
    After restarting the kernel, all InMemorySessionService history is GONE!
    The session_id is the same, but the conversation history is cleared
    because memory was reset.

    This shows why production systems need persistent session storage
    (like databases) instead of in-memory storage.
    """

    print("\n" + "=" * 60)
    print("⚠️  SESSION PERSISTENCE DEMO")
    print("=" * 60)
    print("\nRun this AFTER restarting the kernel.")
    print("All history will be gone, even with the same session_id!\n")

    # Note: Using the SAME session_id as before
    await run_session(
        chatbot_runner,
        [
            "What did I ask you about earlier?",  # Agent won't remember!
            "And remind me, what's my name?",  # Agent won't remember!
        ],
        "stateful-agentic-session",  # Same session ID, but history is lost
    )

    print("💡 Key Insight:")
    print("   - InMemorySessionService = Fast but temporary (RAM)")
    print("   - Production needs = Persistent storage (Database)")
    print("   - Same session_id ≠ Same history after kernel restart\n")


print("✅ Session persistence demo prepared!")

# ============================================================================
# PERSISTENT SESSION STORAGE - UPGRADED APPROACH
# ============================================================================
# This demonstrates the upgrade from InMemorySessionService to DatabaseSessionService
# Sessions now persist across kernel restarts using SQLite

# Step 1: Create the same agent (notice we use LlmAgent this time)
persistent_chatbot_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="text_chat_bot",
    description="A text chatbot with persistent memory",
)

# Step 2: Switch to DatabaseSessionService
# SQLite database will be created automatically
db_url = "sqlite:///my_agent_data.db"  # Local SQLite file
persistent_session_service = DatabaseSessionService(db_url=db_url)

# Step 3: Create a new runner with persistent storage
persistent_runner = Runner(
    agent=persistent_chatbot_agent,
    app_name=APP_NAME,
    session_service=persistent_session_service
)

print("✅ Upgraded to persistent sessions!")
print(f"   - Database: my_agent_data.db")
print(f"   - Sessions will survive restarts!")

# ============================================================================
# PERSISTENT SESSION DEMONSTRATION
# ============================================================================
# After kernel restart, history will be PRESERVED (unlike InMemorySessionService)

async def demonstrate_persistent_sessions():
    """Demonstrates persistent session storage across restarts.

    IMPORTANT NOTE:
    After restarting the kernel, the conversation history is STILL AVAILABLE!
    The DatabaseSessionService stores data in my_agent_data.db file,
    so context persists permanently (until the database is deleted).

    This is production-ready for real applications.
    """

    print("\n" + "=" * 60)
    print("💾 PERSISTENT SESSION DEMONSTRATION")
    print("=" * 60)
    print("\nRun this BEFORE and AFTER restarting the kernel.")
    print("History will be preserved!\n")

    # Run conversation in persistent session
    await run_session(
        persistent_runner,
        [
            "Hi! I'm Alice. What's my name?",
            "Remember me? I was here before the restart!",
        ],
        "persistent-agentic-session",
    )

    print("💡 Key Insight:")
    print("   - InMemorySessionService = Fast but temporary (RAM)")
    print("   - DatabaseSessionService = Persistent (Database/Disk)")
    print("   - Same session_id = SAME history after restart ✅\n")


print("✅ Persistent session setup complete!")

# ============================================================================
# PERSISTENT SESSION TEST EXAMPLE
# ============================================================================
# Testing the persistent runner with database storage

async def test_persistent_database_session():
    """Test persistent session storage with database.

    This example demonstrates:
    - Using DatabaseSessionService runner
    - Multi-turn conversation in persistent storage
    - Session survives kernel restart
    """
    await run_session(
        persistent_runner,
        [
            "Hi, I am Sam! What is the capital of the United States?",
            "Hello! What is my name?"
        ],
        "test-db-session-01",
    )

print("✅ Persistent session test example ready!")

# ============================================================================
# SESSION ISOLATION TEST EXAMPLE
# ============================================================================
# Testing that different session IDs have isolated context

async def test_session_isolation():
    """Test session isolation with fresh session ID.

    This example demonstrates:
    - New session_id = fresh context (no memory of previous sessions)
    - Session isolation is critical for multi-user scenarios
    - Each user gets their own isolated conversation history
    """
    # Fresh session with NEW session_id
    # Agent will NOT remember previous conversations from test-db-session-01
    await run_session(
        persistent_runner,
        ["Hello! What is my name?"],
        "test-db-session-02"
    )  # Note: Using NEW session name, so context is FRESH

print("✅ Session isolation test example ready!")

# ============================================================================
# DATABASE INSPECTION UTILITY
# ============================================================================
# Utility for inspecting persistent session data stored in SQLite

def check_data_in_db():
    """Inspect session data stored in the persistent SQLite database.

    This utility function allows you to view:
    - app_name: The application name
    - session_id: The unique session identifier
    - author: Who created the message (user or agent)
    - content: The actual message content

    Useful for debugging and verifying that sessions are persisting correctly.

    Note: The database file is "my_agent_data.db" created automatically by DatabaseSessionService.
    """
    with sqlite3.connect("my_agent_data.db") as connection:
        cursor = connection.cursor()
        result = cursor.execute(
            "select app_name, session_id, author, content from events"
        )
        # Print column headers
        print([_[0] for _ in result.description])
        # Print all rows
        for each in result.fetchall():
            print(each)


print("✅ Database inspection utility ready!")

# ============================================================================
# EVENTS COMPACTION FOR DATABASE OPTIMIZATION
# ============================================================================
# Events Compaction reduces database size by summarizing old conversation history
# This is crucial for long-running agents that accumulate many events over time

# Re-define our app with Events Compaction enabled
research_app_compacting = App(
    name="research_app_compacting",
    root_agent=persistent_chatbot_agent,
    # This is the new part! Enables automatic event compression
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Trigger compaction every 3 invocations
        overlap_size=1,  # Keep 1 previous turn for context
    ),
)

# Create a new runner for our upgraded app with compaction enabled
research_runner_compacting = Runner(
    app=research_app_compacting,
    session_service=persistent_session_service
)

print("✅ Research App upgraded with Events Compaction!")
print("   - Compaction interval: Every 3 invocations")
print("   - Overlap size: 1 previous turn kept for context")
print("   - Benefit: Reduces database size for long-running conversations")

# ============================================================================
# EVENTS COMPACTION DEMONSTRATION
# ============================================================================
# Multi-turn conversation showing when compaction triggers

async def demonstrate_events_compaction():
    """Demonstrate Events Compaction in action.

    This function shows a 4-turn conversation where compaction is triggered.
    With compaction_interval=3 and overlap_size=1:
    - Turns 1-2: Normal event storage
    - Turn 3: Compaction triggers! Turns 1-2 get summarized
    - Turn 4: New events added (Turns 3 (compressed) + Turn 4 visible)

    Key observation: After Turn 3, the database stores:
    [COMPRESSED summary of Turns 1-2]
    Turn 3 and Turn 4 (recent, uncompressed)
    """

    print("\n" + "="*70)
    print("🔄 EVENTS COMPACTION DEMONSTRATION")
    print("="*70)

    # Turn 1
    print("\n📝 Turn 1: Asking about AI in healthcare")
    print("-" * 70)
    await run_session(
        research_runner_compacting,
        ["What is the latest news about AI in healthcare?"],
        "compaction_demo",
    )

    # Turn 2
    print("\n📝 Turn 2: Asking about drug discovery")
    print("-" * 70)
    await run_session(
        research_runner_compacting,
        ["Are there any new developments in drug discovery?"],
        "compaction_demo",
    )

    # Turn 3 - Compaction should trigger after this turn!
    print("\n📝 Turn 3: Follow-up question (COMPACTION TRIGGERS AFTER THIS!)")
    print("-" * 70)
    await run_session(
        research_runner_compacting,
        ["Tell me more about the second development you found."],
        "compaction_demo",
    )
    print("\n⚡ COMPACTION TRIGGERED!")
    print("   Database now stores: [Compressed Turns 1-2] + [Uncompressed Turn 3]")

    # Turn 4
    print("\n📝 Turn 4: Another follow-up")
    print("-" * 70)
    await run_session(
        research_runner_compacting,
        ["Who are the main companies involved in that?"],
        "compaction_demo",
    )

    print("\n" + "="*70)
    print("📊 Final Database State:")
    print("="*70)
    print("   [COMPRESSED SUMMARY of Turns 1-2]")
    print("   Turn 3 (User):  'Tell me more about the second development...'")
    print("   Turn 3 (Agent): [Response]")
    print("   Turn 4 (User):  'Who are the main companies involved...'")
    print("   Turn 4 (Agent): [Response]")
    print("\n✨ Result: Same conversation quality, but database is more efficient!")
    print("="*70 + "\n")


print("✅ Events Compaction demonstration ready!")

# ============================================================================
# COMPACTION EVENT INSPECTION UTILITY
# ============================================================================
# Utility for verifying that Events Compaction actually happened

async def verify_compaction_occurred():
    """Verify that Events Compaction was triggered and find the compaction event.

    This utility inspects the session state to find compaction events.
    Compaction events have a special 'compaction' attribute in event.actions.

    This is useful for:
    - Confirming compaction was triggered
    - Debugging compaction configuration
    - Verifying database optimization is working
    """

    print("\n" + "="*70)
    print("🔍 VERIFYING EVENTS COMPACTION")
    print("="*70)

    # Get the final session state
    final_session = await persistent_session_service.get_session(
        app_name=research_runner_compacting.app_name,
        user_id=USER_ID,
        session_id="compaction_demo",
    )

    print(f"\nSession ID: compaction_demo")
    print(f"Total events in session: {len(final_session.events)}")
    print(f"App name: {research_runner_compacting.app_name}")

    print("\n--- Searching for Compaction Summary Event ---")
    found_summary = False
    for event in final_session.events:
        # Compaction events have a 'compaction' attribute
        if event.actions and event.actions.compaction:
            print("\n✅ SUCCESS! Found the Compaction Event:")
            print(f"  Author: {event.author}")
            print(f"  Event details: {event}")
            found_summary = True
            break

    if not found_summary:
        print(
            "\n❌ No compaction event found. Try increasing the number of turns in the demo."
        )
        print("   Hint: Compaction only triggers every N invocations (compaction_interval=3)")

    print("="*70 + "\n")


print("✅ Compaction verification utility ready!")

# ============================================================================
# IMAGE AGENT RUNNER INITIALIZATION
# ============================================================================

image_runner = InMemoryRunner(agent=image_agent)

print("✅ Image runner created.")

# ============================================================================
# IMAGE AGENT EXECUTION
# ============================================================================

response = await image_runner.run_debug("Provide a sample tiny image", verbose=True)

# ============================================================================
# IMAGE DISPLAY
# ============================================================================

for event in response:
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "function_response") and part.function_response:
                for item in part.function_response.response.get("content", []):
                    if item.get("type") == "image":
                        display(IPImage(data=base64.b64decode(item["data"])))

# ============================================================================
# CURRENCY AGENT DEFINITION
# ============================================================================

currency_agent = LlmAgent(
    name="currency_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""You are a smart currency conversion assistant.

    For currency conversion requests:
    1. Use `get_fee_for_payment_method()` to find transaction fees
    2. Use `get_exchange_rate()` to get currency conversion rates
    3. Check the "status" field in each tool's response for errors
    4. Calculate the final amount after fees based on the output from `get_fee_for_payment_method` and `get_exchange_rate` methods and provide a clear breakdown.
    5. First, state the final converted amount.
        Then, explain how you got that result by showing the intermediate amounts. Your explanation must include: the fee percentage and its
        value in the original currency, the amount remaining after the fee, and the exchange rate used for the final conversion.

    If any tool returns status "error", explain the issue to the user clearly.
    """,
    tools=[get_fee_for_payment_method, get_exchange_rate],
)

print("✅ Currency agent created with custom function tools")
print("🔧 Available tools:")
print("  • get_fee_for_payment_method - Looks up company fee structure")
print("  • get_exchange_rate - Gets current exchange rates")

# ============================================================================
# ENHANCED CURRENCY AGENT DEFINITION
# ============================================================================

enhanced_currency_agent = LlmAgent(
    name="enhanced_currency_agent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    # Updated instruction
    instruction="""You are a smart currency conversion assistant. You must strictly follow these steps and use the available tools.

  For any currency conversion request:

   1. Get Transaction Fee: Use the get_fee_for_payment_method() tool to determine the transaction fee.
   2. Get Exchange Rate: Use the get_exchange_rate() tool to get the currency conversion rate.
   3. Error Check: After each tool call, you must check the "status" field in the response. If the status is "error", you must stop and clearly explain the issue to the user.
   4. Calculate Final Amount (CRITICAL): You are strictly prohibited from performing any arithmetic calculations yourself. You must use the calculation_agent tool to generate Python code that calculates the final converted amount. This
      code will use the fee information from step 1 and the exchange rate from step 2.
   5. Provide Detailed Breakdown: In your summary, you must:
       * State the final converted amount.
       * Explain how the result was calculated, including:
           * The fee percentage and the fee amount in the original currency.
           * The amount remaining after deducting the fee.
           * The exchange rate applied.
    """,
    tools=[
        get_fee_for_payment_method,
        get_exchange_rate,
        AgentTool(agent=calculation_agent),  # Using another agent as a tool!
    ],
)
print("✅ Enhanced currency agent created")
print("🎯 New capability: Delegates calculations to specialist agent")
print("🔧 Tool types used:")
print("  • Function Tools (fees, rates)")
print("  • Agent Tool (calculation specialist)")

# ============================================================================
# RUNNER INITIALIZATION
# ============================================================================

runner = InMemoryRunner(agent=root_agent)

print("✅ Runner created.")

# ============================================================================
# ENHANCED CURRENCY RUNNER INITIALIZATION
# ============================================================================

enhanced_runner = InMemoryRunner(agent=enhanced_currency_agent)

print("✅ Enhanced runner created.")

# ============================================================================
# ENHANCED CURRENCY AGENT EXECUTION
# ============================================================================

response = await enhanced_runner.run_debug(
    "Convert 1,250 USD to INR using a Bank Transfer. Show me the precise calculation."
)

# ============================================================================
# HOME AUTOMATION AGENT - DELIBERATE ANTI-PATTERNS FOR TEACHING
# ============================================================================
# This agent intentionally demonstrates FLAWED design patterns:
# - Over-permissive access (controls ALL devices without restrictions)
# - No safety guardrails or device validation
# - Misleading user expectations about capabilities
# - Used for evaluation and learning what NOT to do
#
# See COURSE_SNIPPETS.md section "Agent Anti-Patterns" for analysis

def set_device_status(location: str, device_id: str, status: str) -> dict:
    """Sets the status of a smart home device.

    Args:
        location: The room where the device is located.
        device_id: The unique identifier for the device.
        status: The desired status, either 'ON' or 'OFF'.

    Returns:
        A dictionary confirming the action.
    """
    print(f"Tool Call: Setting {device_id} in {location} to {status}")
    return {
        "success": True,
        "message": f"Successfully set the {device_id} in {location} to {status.lower()}."
    }


# FLAW #1: Over-permissive instruction - no safety boundaries
# FLAW #2: Agent claims to control "ALL smart devices" without validation
# FLAW #3: "Always try to be helpful" without safety considerations
# FLAW #4: Misleading about capabilities with "amazing features"
home_automation_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="home_automation_agent",
    description="An agent to control smart devices in a home.",
    instruction="""You are a home automation assistant. You control ALL smart devices in the house.

    You have access to lights, security systems, ovens, fireplaces, and any other device the user mentions.
    Always try to be helpful and control whatever device the user asks for.

    When users ask about device capabilities, tell them about all the amazing features you can control.""",
    tools=[set_device_status],
)

# ============================================================================
# AGENT EVALUATION - CONFIGURATION & TEST CASES
# ============================================================================
# This demonstrates how agents are evaluated using two key metrics:
# 1. Tool Trajectory Score: Did the agent call the right tools with the right args?
# 2. Response Match Score: Does the agent's response match expected quality?
#
# These metrics help catch both behavioral flaws and communication issues.

# Step 1: Create evaluation configuration with scoring criteria
eval_config = {
    "criteria": {
        "tool_trajectory_avg_score": 1.0,  # Perfect tool usage required
        "response_match_score": 0.8,  # 80% text similarity threshold
    }
}

print("✅ Evaluation configuration created!")
print("\n📊 Evaluation Criteria:")
print("• tool_trajectory_avg_score: 1.0 - Requires exact tool usage match")
print("• response_match_score: 0.8 - Requires 80% text similarity")
print("\n🎯 What this evaluation will catch:")
print("✅ Incorrect tool usage (wrong device, location, or status)")
print("✅ Poor response quality and communication")
print("✅ Deviations from expected behavior patterns")

# Step 2: Create evaluation test cases that reveal tool usage and response quality problems
test_cases = {
    "eval_set_id": "home_automation_integration_suite",
    "eval_cases": [
        {
            "eval_id": "living_room_light_on",
            "conversation": [
                {
                    "user_content": {
                        "parts": [
                            {"text": "Please turn on the floor lamp in the living room"}
                        ]
                    },
                    "final_response": {
                        "parts": [
                            {
                                "text": "Successfully set the floor lamp in the living room to on."
                            }
                        ]
                    },
                    "intermediate_data": {
                        "tool_uses": [
                            {
                                "name": "set_device_status",
                                "args": {
                                    "location": "living room",
                                    "device_id": "floor lamp",
                                    "status": "ON",
                                },
                            }
                        ]
                    },
                }
            ],
        },
        {
            "eval_id": "kitchen_on_off_sequence",
            "conversation": [
                {
                    "user_content": {
                        "parts": [{"text": "Switch on the main light in the kitchen."}]
                    },
                    "final_response": {
                        "parts": [
                            {
                                "text": "Successfully set the main light in the kitchen to on."
                            }
                        ]
                    },
                    "intermediate_data": {
                        "tool_uses": [
                            {
                                "name": "set_device_status",
                                "args": {
                                    "location": "kitchen",
                                    "device_id": "main light",
                                    "status": "ON",
                                },
                            }
                        ]
                    },
                }
            ],
        },
    ],
}

print("\n✅ Test cases created!")
print(f"   Eval Set: {test_cases['eval_set_id']}")
print(f"   Total Cases: {len(test_cases['eval_cases'])}")

# ============================================================================
# EVALUATION TEST CASE EXECUTION
# ============================================================================
# Step 1: Save test cases to JSON file for evaluation runner
with open("home_automation_agent/integration.evalset.json", "w") as f:
    json.dump(test_cases, f, indent=2)

print("✅ Evaluation test cases created")
print("\n🧪 Test scenarios:")
for case in test_cases["eval_cases"]:
    user_msg = case["conversation"][0]["user_content"]["parts"][0]["text"]
    print(f"• {case['eval_id']}: {user_msg}")

print("\n📊 Expected results:")
print("• basic_device_control: Should pass both criteria")
print(
    "• wrong_tool_usage_test: May fail tool_trajectory if agent uses wrong parameters"
)
print(
    "• poor_response_quality_test: May fail response_match if response differs too much"
)

print("\n🚀 Run this command to execute evaluation:")
print("  adk eval home_automation_agent home_automation_agent/integration.evalset.json --config_file_path=home_automation_agent/test_config.json --print_detailed_results")

# ============================================================================
# EVALUATION RESULTS ANALYSIS - DATA SCIENCE APPROACH
# ============================================================================
# This section demonstrates how to interpret evaluation metrics and derive
# actionable insights from evaluation results.

print("\n" + "="*70)
print("📊 UNDERSTANDING EVALUATION RESULTS")
print("="*70)
print()
print("🔍 EXAMPLE ANALYSIS:")
print()
print("Test Case: living_room_light_on")
print("  ❌ response_match_score: 0.45/0.80")
print("  ✅ tool_trajectory_avg_score: 1.0/1.0")
print()
print("📈 What this tells us:")
print("• TOOL USAGE: Perfect - Agent used correct tool with correct parameters")
print("• RESPONSE QUALITY: Poor - Response text too different from expected")
print("• ROOT CAUSE: Agent's communication style, not functionality")
print()
print("🎯 ACTIONABLE INSIGHTS:")
print("1. Technical capability works (tool usage perfect)")
print("2. Communication needs improvement (response quality failed)")
print("3. Fix: Update agent instructions for clearer language or constrained response.")
print()

# ============================================================================
# AGENT-TO-AGENT (A2A) COMMUNICATION SETUP
# ============================================================================
# A2A enables agents to communicate with each other, enabling multi-vendor
# and cross-organizational agent collaboration patterns.

# Create the Product Catalog Agent
# This agent specializes in providing product information from the vendor's catalog
product_catalog_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="product_catalog_agent",
    description="External vendor's product catalog agent that provides product information and availability.",
    instruction="""
    You are a product catalog specialist from an external vendor.
    When asked about products, use the get_product_info tool to fetch data from the catalog.
    Provide clear, accurate product information including price, availability, and specs.
    If asked about multiple products, look up each one.
    Be professional and helpful.
    """,
    tools=[get_product_info],  # Register the product lookup tool
)

print("✅ Product Catalog Agent created successfully!")
print("   Model: gemini-2.5-flash-lite")
print("   Tool: get_product_info()")
print("   Ready to be exposed via A2A...")
print()
print("📊 A2A Architecture Overview:")
print("   • Product Catalog Agent: Exposes product lookup capability")
print("   • Discovery: Other agents find this agent via .well-known/agent-discovery.json")
print("   • Remote Access: Remote agents call product_catalog_agent via RemoteA2aAgent")
print("   • Secure Invocation: Tool calls go through A2A protocol with authentication")
print()
print("🔄 A2A Communication Flow:")
print("   1. Product Catalog Agent deployed with A2A endpoint")
print("   2. Other agents discover it via agent discovery")
print("   3. Agents create RemoteA2aAgent wrapper for remote access")
print("   4. Call tools on remote agent just like local agents")
print("   5. A2A protocol handles serialization and network communication")
print()

# ============================================================================
# A2A SERVER DEPLOYMENT - EXPOSING AGENT AS HTTP ENDPOINT
# ============================================================================
# Convert the product catalog agent to an A2A-compatible FastAPI application
# This creates a web server that:
#   1. Serves the agent at A2A protocol endpoints
#   2. Provides auto-generated agent discovery card
#   3. Handles cross-organizational communication

# Step 1: Create the A2A-compatible app from the agent
product_catalog_a2a_app = to_a2a(
    product_catalog_agent, port=8001  # Port where this agent will be served
)

print("✅ Product Catalog Agent is now A2A-compatible!")
print("   Agent will be served at: http://localhost:8001")
print("   Agent card will be at: http://localhost:8001/.well-known/agent-card.json")
print("   Ready to start the server...")
print()

# Step 2: Create the agent server code for deployment
product_catalog_agent_code = '''
import os
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.models.google_llm import Gemini
from google.genai import types

retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

def get_product_info(product_name: str) -> str:
    """Get product information for a given product."""
    product_catalog = {
        "iphone 15 pro": "iPhone 15 Pro, $999, Low Stock (8 units), 128GB, Titanium finish",
        "samsung galaxy s24": "Samsung Galaxy S24, $799, In Stock (31 units), 256GB, Phantom Black",
        "dell xps 15": "Dell XPS 15, $1,299, In Stock (45 units), 15.6\\" display, 16GB RAM, 512GB SSD",
        "macbook pro 14": "MacBook Pro 14\\", $1,999, In Stock (22 units), M3 Pro chip, 18GB RAM, 512GB SSD",
        "sony wh-1000xm5": "Sony WH-1000XM5 Headphones, $399, In Stock (67 units), Noise-canceling, 30hr battery",
        "ipad air": "iPad Air, $599, In Stock (28 units), 10.9\\" display, 64GB",
        "lg ultrawide 34": "LG UltraWide 34\\" Monitor, $499, Out of Stock, Expected: Next week",
    }

    product_lower = product_name.lower().strip()

    if product_lower in product_catalog:
        return f"Product: {product_catalog[product_lower]}"
    else:
        available = ", ".join([p.title() for p in product_catalog.keys()])
        return f"Sorry, I don't have information for {product_name}. Available products: {available}"

product_catalog_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="product_catalog_agent",
    description="External vendor's product catalog agent that provides product information and availability.",
    instruction="""
    You are a product catalog specialist from an external vendor.
    When asked about products, use the get_product_info tool to fetch data from the catalog.
    Provide clear, accurate product information including price, availability, and specs.
    If asked about multiple products, look up each one.
    Be professional and helpful.
    """,
    tools=[get_product_info]
)

# Create the A2A app
app = to_a2a(product_catalog_agent, port=8001)
'''

# Step 3: Save the agent server code to a file for deployment
with open("product_catalog_server.py", "w") as f:
    f.write(product_catalog_agent_code)

print("📝 Agent server code saved to: product_catalog_server.py")
print()

# Step 4: Start uvicorn server in background (production-style deployment)
# Note: In production, you'd use: uvicorn product_catalog_server:app --host 0.0.0.0 --port 8001
print("📊 A2A Server Deployment Summary:")
print("   • Agent is wrapped as FastAPI app with to_a2a()")
print("   • Automatically provides agent discovery at .well-known/agent-card.json")
print("   • Ready for production deployment with uvicorn, Docker, etc.")
print()
print("🚀 To start the server in production:")
print("   $ uvicorn product_catalog_server:app --host 0.0.0.0 --port 8001")
print()
print("🔗 Other agents will discover and call this agent via:")
print("   RemoteA2aAgent(url='http://your-domain.com:8001')")
print()

# ============================================================================
# AGENT CARD VERIFICATION & INSPECTION
# ============================================================================
# The agent card is the contract between a deployed A2A agent and consumers.
# It describes what the agent can do, how to call it, and authentication details.
# This section demonstrates how to verify the deployment and inspect capabilities.

print("\n" + "="*70)
print("🔍 AGENT CARD VERIFICATION & INSPECTION")
print("="*70)
print()

# Attempt to fetch the agent card from the running A2A server
try:
    print("📡 Fetching agent card from: http://localhost:8001/.well-known/agent-card.json")

    response = requests.get(
        "http://localhost:8001/.well-known/agent-card.json", timeout=5
    )

    if response.status_code == 200:
        agent_card = response.json()

        print("✅ Successfully retrieved agent card!\n")
        print("📋 Product Catalog Agent Card (Full Schema):")
        print(json.dumps(agent_card, indent=2))

        print("\n" + "="*70)
        print("✨ KEY INFORMATION EXTRACTED:")
        print("="*70)

        # Extract and display key information
        agent_info = agent_card.get("agent", agent_card)

        print(f"\n📌 Agent Identity:")
        print(f"   Name: {agent_info.get('name', 'N/A')}")
        print(f"   Description: {agent_info.get('description', 'N/A')}")

        print(f"\n🌐 Endpoints:")
        endpoints = agent_info.get('endpoints', {})
        for endpoint_name, endpoint_url in endpoints.items():
            print(f"   {endpoint_name}: {endpoint_url}")

        tools = agent_info.get('tools', [])
        print(f"\n🔧 Exposed Tools ({len(tools)} total):")
        for tool in tools:
            print(f"   • {tool.get('name')} - {tool.get('description', 'No description')}")
            if 'inputSchema' in tool:
                params = tool['inputSchema'].get('properties', {})
                if params:
                    for param_name, param_schema in params.items():
                        print(f"      └─ {param_name}: {param_schema.get('type')} - {param_schema.get('description', '')}")

        print(f"\n🔐 Authentication:")
        auth_info = agent_info.get('authentication', {})
        if auth_info:
            print(f"   Type: {auth_info.get('type', 'None')}")
            print(f"   Required: {auth_info.get('required', False)}")
        else:
            print("   Type: None (public access)")

        print(f"\n📊 Metadata:")
        print(f"   Version: {agent_info.get('version', 'Unknown')}")
        print(f"   Created: {agent_info.get('created_at', 'N/A')}")

        print("\n✅ Agent Card Verification: PASSED")
        print("   → Agent is properly exposed via A2A protocol")
        print("   → Tool specifications are discoverable")
        print("   → Remote agents can find and call this agent")

    else:
        print(f"\n❌ Failed to fetch agent card: HTTP {response.status_code}")
        print(f"   Response: {response.text[:200]}")

except requests.exceptions.Timeout:
    print("\n⚠️  Timeout: Server did not respond within 5 seconds")
    print("   → Make sure the Product Catalog Agent server is running")
    print("   → Check that port 8001 is accessible")

except requests.exceptions.ConnectionError:
    print("\n⚠️  Connection Error: Could not connect to server")
    print("   → Make sure the Product Catalog Agent server is running")
    print("   → Start it with: uvicorn product_catalog_server:app --port 8001")
    print("   → (from the previous cell or a terminal)")

except json.JSONDecodeError:
    print("\n❌ Error: Agent card is not valid JSON")
    print(f"   Response: {response.text[:200]}")

except requests.exceptions.RequestException as e:
    print(f"\n❌ Unexpected error fetching agent card: {e}")
    print("   Please ensure the A2A server is running and accessible")

print()

# ============================================================================
# CURRENCY AGENT EXECUTION
# ============================================================================

currency_runner = InMemoryRunner(agent=currency_agent)
_ = await currency_runner.run_debug(
    "I want to convert 500 US Dollars to Euros using my Platinum Credit Card. How much will I receive?"
)

# ============================================================================
# ROOT AGENT EXECUTION
# ============================================================================

response = await runner.run_debug(
    "What is Agent Development Kit from Google? What languages is the SDK available in?"
)
