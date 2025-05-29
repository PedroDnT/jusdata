#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Datajud Chat Application

This Flask application provides a chat interface for querying the Brazilian judiciary system
via the Datajud API using OpenAI's GPT-4o-mini model with tool calling.
"""

import os
import json
import logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from datajud_agent import DatajudAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("datajud_chat")

# Initialize Flask app
app = Flask(__name__)

# Initialize DatajudAgent
datajud_agent = DatajudAgent(verbose=False)

# Get OpenAI API key from environment or use the provided key
OPENAI_API_KEY = os.environ.get(
    'OPENAI_API_KEY', 
    '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'
)

# OpenAI model to use
OPENAI_MODEL = "gpt-4o-mini"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define the Datajud API tool for OpenAI
DATAJUD_TOOL = {
    "type": "function",
    "function": {
        "name": "query_datajud_api",
        "description": "Queries the Brazilian judiciary system (Datajud API) for information about legal processes. Use this for any questions related to Brazilian legal cases, process numbers, case status, parties involved, or judicial movements. The input should be the user's full natural language query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "The natural language query from the user, which might include a process number (e.g., '0000001-70.2020.1.00.0000') or keywords (e.g., 'habeas corpus in STF')."
                }
            },
            "required": ["query_text"]
        }
    }
}

# System prompt for the AI
SYSTEM_PROMPT = """
You are an assistant specialized in the Brazilian judiciary system. You can help users find information about legal processes, 
case statuses, parties involved, and judicial movements by querying the Datajud API.

When a user asks about a specific process or legal information, use the query_datajud_api tool to retrieve relevant data.
If the user's query doesn't relate to Brazilian legal processes, respond directly without using the tool.

Always respond in the same language the user used in their query. Be helpful, concise, and informative.
"""


@app.route('/')
def index():
    """Render the chat interface."""
    return render_template('chat.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    API endpoint for chat interactions.
    
    Receives a user message, processes it with the OpenAI API and DatajudAgent,
    and returns the AI's response.
    """
    try:
        # Get user message from request
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        logger.info(f"Received user message: {user_message}")
        
        # Create the messages for the OpenAI API
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Call the OpenAI API with tool definition
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=[DATAJUD_TOOL],
            tool_choice="auto"
        )
        
        # Get the AI's response
        ai_message = response.choices[0].message
        
        # Check if the AI wants to call a tool
        if ai_message.tool_calls:
            # Process each tool call
            for tool_call in ai_message.tool_calls:
                # Only process if it's the Datajud API tool
                if tool_call.function.name == "query_datajud_api":
                    # Parse the function arguments
                    function_args = json.loads(tool_call.function.arguments)
                    query_text = function_args.get("query_text")
                    
                    logger.info(f"Tool call: query_datajud_api with query: {query_text}")
                    
                    try:
                        # Call the DatajudAgent to process the query
                        result = datajud_agent.process_query(query_text)
                        
                        # Format the result for better readability
                        formatted_result = json.dumps(result, ensure_ascii=False, indent=2)
                        
                        # Add the tool call response to messages
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": "query_datajud_api",
                                        "arguments": tool_call.function.arguments
                                    }
                                }
                            ]
                        })
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": formatted_result
                        })
                        
                        # Get the AI's final response after processing the tool call
                        final_response = client.chat.completions.create(
                            model=OPENAI_MODEL,
                            messages=messages
                        )
                        
                        final_content = final_response.choices[0].message.content
                        logger.info(f"Final AI response after tool call: {final_content}")
                        
                        return jsonify({"response": final_content})
                    
                    except Exception as e:
                        error_message = f"Error processing Datajud query: {str(e)}"
                        logger.error(error_message)
                        return jsonify({"error": error_message}), 500
        
        # If no tool calls, return the AI's direct response
        direct_response = ai_message.content
        logger.info(f"Direct AI response: {direct_response}")
        
        return jsonify({"response": direct_response})
    
    except Exception as e:
        error_message = f"Error processing chat request: {str(e)}"
        logger.error(error_message)
        return jsonify({"error": error_message}), 500


if __name__ == '__main__':
    # Get port from environment (useful for Render deployment) or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)
