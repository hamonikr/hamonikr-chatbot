"""
MCP (Model Context Protocol) Client Implementation
Handles communication with MCP servers for extended AI capabilities
"""

import json
import asyncio
import subprocess
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MCPMessageType(Enum):
    """MCP message types"""
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    LIST_TOOLS = "tools/list"
    TOOL_CALL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    ERROR = "error"

@dataclass
class MCPServer:
    """MCP Server configuration"""
    name: str
    uri: str
    command: Optional[str] = None
    enabled: bool = True
    process: Optional[subprocess.Popen] = None
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None

class MCPClient:
    """
    MCP Client for managing connections to MCP servers
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.loop = None
        self._running = False
        
    def add_server(self, name: str, uri: str, command: Optional[str] = None, enabled: bool = True):
        """Add an MCP server configuration"""
        self.servers[name] = MCPServer(
            name=name,
            uri=uri,
            command=command,
            enabled=enabled
        )
        
    def remove_server(self, name: str):
        """Remove an MCP server"""
        if name in self.servers:
            asyncio.run(self.disconnect_server(name))
            del self.servers[name]
            
    async def connect_server(self, name: str):
        """Connect to an MCP server"""
        if name not in self.servers:
            raise ValueError(f"Server {name} not found")
            
        server = self.servers[name]
        if not server.enabled:
            return
            
        try:
            if server.command:
                # Start server process if command is provided
                server.process = await asyncio.create_subprocess_shell(
                    server.command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                logger.info(f"Started MCP server process: {name}")
            
            # Connect to server URI
            if server.uri.startswith("stdio://"):
                # Use stdio for communication
                if server.process:
                    server.reader = server.process.stdout
                    server.writer = server.process.stdin
            elif server.uri.startswith("tcp://"):
                # TCP connection
                host_port = server.uri[6:].split(":")
                host = host_port[0]
                port = int(host_port[1]) if len(host_port) > 1 else 3000
                server.reader, server.writer = await asyncio.open_connection(host, port)
            elif server.uri.startswith("unix://"):
                # Unix socket connection
                socket_path = server.uri[7:]
                server.reader, server.writer = await asyncio.open_unix_connection(socket_path)
            else:
                raise ValueError(f"Unsupported URI scheme: {server.uri}")
                
            # Send initialization message
            await self.send_message(name, {
                "jsonrpc": "2.0",
                "method": MCPMessageType.INITIALIZE.value,
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {}
                },
                "id": 1
            })
            
            # Wait for initialization response
            response = await self.receive_message(name)
            if response and response.get("result"):
                logger.info(f"MCP server {name} initialized successfully")
                return True
            else:
                logger.error(f"Failed to initialize MCP server {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MCP server {name}: {e}")
            return False
            
    async def disconnect_server(self, name: str):
        """Disconnect from an MCP server"""
        if name not in self.servers:
            return
            
        server = self.servers[name]
        
        try:
            if server.writer:
                server.writer.close()
                await server.writer.wait_closed()
                
            if server.process:
                server.process.terminate()
                await server.process.wait()
                
            server.reader = None
            server.writer = None
            server.process = None
            
            logger.info(f"Disconnected from MCP server {name}")
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server {name}: {e}")
            
    async def send_message(self, server_name: str, message: Dict[str, Any]):
        """Send a message to an MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
            
        server = self.servers[server_name]
        if not server.writer:
            raise ConnectionError(f"Server {server_name} not connected")
            
        try:
            json_message = json.dumps(message) + "\n"
            server.writer.write(json_message.encode())
            await server.writer.drain()
            logger.debug(f"Sent message to {server_name}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending message to {server_name}: {e}")
            raise
            
    async def receive_message(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Receive a message from an MCP server"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
            
        server = self.servers[server_name]
        if not server.reader:
            raise ConnectionError(f"Server {server_name} not connected")
            
        try:
            line = await server.reader.readline()
            if not line:
                return None
                
            message = json.loads(line.decode().strip())
            logger.debug(f"Received message from {server_name}: {message}")
            return message
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding message from {server_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error receiving message from {server_name}: {e}")
            return None
            
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List available tools from an MCP server"""
        await self.send_message(server_name, {
            "jsonrpc": "2.0",
            "method": MCPMessageType.LIST_TOOLS.value,
            "id": 2
        })
        
        response = await self.receive_message(server_name)
        if response and response.get("result"):
            return response["result"].get("tools", [])
        return []
        
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on an MCP server"""
        await self.send_message(server_name, {
            "jsonrpc": "2.0",
            "method": MCPMessageType.TOOL_CALL.value,
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 3
        })
        
        response = await self.receive_message(server_name)
        if response and response.get("result"):
            return response["result"]
        elif response and response.get("error"):
            raise Exception(f"Tool call error: {response['error']}")
        return None
        
    async def list_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """List available resources from an MCP server"""
        await self.send_message(server_name, {
            "jsonrpc": "2.0",
            "method": MCPMessageType.LIST_RESOURCES.value,
            "id": 4
        })
        
        response = await self.receive_message(server_name)
        if response and response.get("result"):
            return response["result"].get("resources", [])
        return []
        
    async def read_resource(self, server_name: str, uri: str) -> Any:
        """Read a resource from an MCP server"""
        await self.send_message(server_name, {
            "jsonrpc": "2.0",
            "method": MCPMessageType.READ_RESOURCE.value,
            "params": {
                "uri": uri
            },
            "id": 5
        })
        
        response = await self.receive_message(server_name)
        if response and response.get("result"):
            return response["result"]
        return None
        
    async def list_prompts(self, server_name: str) -> List[Dict[str, Any]]:
        """List available prompts from an MCP server"""
        await self.send_message(server_name, {
            "jsonrpc": "2.0",
            "method": MCPMessageType.LIST_PROMPTS.value,
            "id": 6
        })
        
        response = await self.receive_message(server_name)
        if response and response.get("result"):
            return response["result"].get("prompts", [])
        return []
        
    async def get_prompt(self, server_name: str, name: str, arguments: Optional[Dict[str, Any]] = None) -> str:
        """Get a prompt from an MCP server"""
        await self.send_message(server_name, {
            "jsonrpc": "2.0",
            "method": MCPMessageType.GET_PROMPT.value,
            "params": {
                "name": name,
                "arguments": arguments or {}
            },
            "id": 7
        })
        
        response = await self.receive_message(server_name)
        if response and response.get("result"):
            messages = response["result"].get("messages", [])
            return "\n".join([msg.get("content", "") for msg in messages])
        return ""
        
    async def connect_all(self):
        """Connect to all enabled MCP servers"""
        tasks = []
        for name, server in self.servers.items():
            if server.enabled:
                tasks.append(self.connect_server(name))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def disconnect_all(self):
        """Disconnect from all MCP servers"""
        tasks = []
        for name in self.servers:
            tasks.append(self.disconnect_server(name))
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    def run_async(self, coro):
        """Helper method to run async coroutines"""
        if not self.loop:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        return self.loop.run_until_complete(coro)
        
    def start(self):
        """Start the MCP client and connect to all servers"""
        self._running = True
        self.run_async(self.connect_all())
        
    def stop(self):
        """Stop the MCP client and disconnect from all servers"""
        self._running = False
        self.run_async(self.disconnect_all())
        if self.loop:
            self.loop.close()
            self.loop = None


# Global MCP client instance
mcp_client = MCPClient()