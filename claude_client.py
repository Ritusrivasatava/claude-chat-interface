import os
from typing import Optional, List, Dict
from dotenv import load_dotenv
import requests
import json


class ClaudeClient:
    """
    A client for interacting directly with the Anthropic Claude API.
    Reads the API key from environment variables (.env file).
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the Claude Client for the Anthropic API.
        
        Args:
            model_name: Optional model name. Defaults to claude-sonnet-latest
        
        Raises:
            ValueError: If required environment variables are not set
        """
        # Load environment variables from .env file (don't override existing env vars)
        # This allows Docker environment variables to take precedence
        load_dotenv(override=False)
        
        # Get API key from environment
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )
        
        # Direct Anthropic API base URL
        self.base_url = "https://api.anthropic.com/v1"
        
        # Set model name
        self.model_name = model_name or os.getenv(
            "MODEL_NAME", "claude-sonnet-latest"
        )
        
        # Initialize conversation history
        self.conversation_history: List[Dict[str, str]] = []
        
        # Set up request headers
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

    def send_message(self, user_message: str, model_name: Optional[str] = None, attachments: Optional[List[Dict]] = None) -> str:
        """
        Send a message and get a response from the Claude API.
        
        Args:
            user_message: The user's message
            model_name: Optional model name. If not provided, uses default model
            attachments: Optional list of attachments. Each dict has:
                         type ('image' or 'text_file'), name, data (base64 or text),
                         media_type (for images)
            
        Returns:
            The assistant's response
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Use provided model or default
            model = model_name or self.model_name
            
            # Build user content (plain text or multimodal content blocks)
            if attachments:
                content_blocks = []
                for attachment in attachments:
                    if attachment["type"] == "image":
                        content_blocks.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": attachment["media_type"],
                                "data": attachment["data"]
                            }
                        })
                    elif attachment["type"] == "text_file":
                        content_blocks.append({
                            "type": "text",
                            "text": f"[Attached file: {attachment['name']}]\n\n{attachment['data']}"
                        })
                if user_message:
                    content_blocks.append({"type": "text", "text": user_message})
                user_content = content_blocks
            else:
                user_content = user_message
            
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": user_content
            })
            
            # Prepare request
            url = f"{self.base_url}/messages"
            
            payload = {
                "model": model,
                "max_tokens": 1024,
                "messages": self.conversation_history
            }
            
            # Make API request
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Check for errors
            if response.status_code != 200:
                error_msg = f"Status {response.status_code}: {response.text}"
                raise Exception(error_msg)
            
            # Parse response
            response_data = response.json()
            
            # Extract message - handle both response formats
            if "content" in response_data:
                assistant_message = response_data["content"][0]["text"]
            else:
                raise Exception(f"Unexpected response format: {response_data}")
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error communicating with the Anthropic API: {str(e)}")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get the current conversation history.
        
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        return self.conversation_history.copy()

    def get_available_models(self) -> List[str]:
        """
        Fetch available models from the Anthropic /models endpoint.
        Falls back to a hardcoded list if the endpoint is unavailable.
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                # Anthropic API returns {"data": [{"id": "...", ...}, ...]}
                models = [m["id"] for m in data.get("data", []) if "id" in m]
                if models:
                    return sorted(models)
        except Exception:
            pass
        # Fallback
        return [
            "claude-haiku-latest",
            "claude-sonnet-latest",
            "claude-opus-latest",
        ]

    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the current model and API connection.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.model_name,
            "api_url": self.base_url,
            "messages_count": len(self.conversation_history)
        }
