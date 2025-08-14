#!/usr/bin/env python3
"""
Tool seeding script for memOS.as

This script pre-populates the registered_tools table with initial tools
that are commonly available in the DevEnviro ecosystem.
"""

import sys
import os
from app.services.postgres_client import get_postgres_client

def seed_initial_tools():
    """Seed the database with initial tools"""
    
    postgres_client = get_postgres_client()
    
    # Initial tool definitions
    initial_tools = [
        {
            "name": "file_read",
            "description": "Read and analyze file contents from the filesystem",
            "usage": "Use this tool to read configuration files, source code, logs, or any text-based files",
            "tags": ["filesystem", "read", "analysis", "text"]
        },
        {
            "name": "file_write",
            "description": "Create or modify files on the filesystem",
            "usage": "Use this tool to create new files, update configurations, or save generated content",
            "tags": ["filesystem", "write", "create", "modify"]
        },
        {
            "name": "bash_execute",
            "description": "Execute shell commands and scripts",
            "usage": "Use this tool to run system commands, build scripts, tests, or automation tasks",
            "tags": ["shell", "command", "execute", "automation"]
        },
        {
            "name": "git_operations",
            "description": "Perform Git version control operations",
            "usage": "Use this tool for Git commands like commit, push, pull, branch management, and status checking",
            "tags": ["git", "version-control", "commit", "branch"]
        },
        {
            "name": "docker_management",
            "description": "Manage Docker containers and images",
            "usage": "Use this tool to build, run, stop Docker containers, and manage Docker images",
            "tags": ["docker", "containers", "build", "deploy"]
        },
        {
            "name": "api_testing",
            "description": "Test and validate API endpoints",
            "usage": "Use this tool to send HTTP requests, validate responses, and test API functionality",
            "tags": ["api", "testing", "http", "validation"]
        },
        {
            "name": "code_analysis",
            "description": "Analyze code quality, structure, and patterns",
            "usage": "Use this tool to review code, check for issues, analyze dependencies, and suggest improvements",
            "tags": ["code", "analysis", "quality", "review"]
        },
        {
            "name": "database_query",
            "description": "Execute database queries and manage data",
            "usage": "Use this tool to query databases, manage schemas, and handle data operations",
            "tags": ["database", "sql", "query", "data"]
        },
        {
            "name": "log_analysis",
            "description": "Parse and analyze log files and system outputs",
            "usage": "Use this tool to analyze application logs, system logs, and extract insights from log data",
            "tags": ["logs", "analysis", "monitoring", "debugging"]
        },
        {
            "name": "web_scraping",
            "description": "Extract data from web pages and APIs",
            "usage": "Use this tool to scrape web content, extract structured data, and gather information from online sources",
            "tags": ["web", "scraping", "data-extraction", "automation"]
        }
    ]
    
    # Register each tool
    registered_count = 0
    for tool in initial_tools:
        try:
            tool_id = postgres_client.register_tool(
                name=tool["name"],
                description=tool["description"],
                usage=tool["usage"],
                tags=tool["tags"]
            )
            
            if tool_id:
                print(f"✅ Registered tool: {tool['name']} (ID: {tool_id})")
                registered_count += 1
            else:
                print(f"⚠️  Tool already exists: {tool['name']}")
                
        except Exception as e:
            print(f"❌ Failed to register tool {tool['name']}: {e}")
    
    print(f"\n🎉 Seeding complete! Registered {registered_count} new tools.")
    return registered_count

def list_registered_tools():
    """List all currently registered tools"""
    postgres_client = get_postgres_client()
    
    try:
        tools = postgres_client.get_all_tools()
        
        if not tools:
            print("No tools are currently registered.")
            return
        
        print(f"\n📋 Currently registered tools ({len(tools)}):")
        print("-" * 80)
        
        for tool in tools:
            print(f"ID: {tool['id']} | Name: {tool['name']}")
            print(f"Description: {tool['description']}")
            print(f"Tags: {', '.join(tool['tags']) if tool['tags'] else 'None'}")
            print(f"Created: {tool['created_at']}")
            print("-" * 80)
            
    except Exception as e:
        print(f"❌ Failed to list tools: {e}")

if __name__ == "__main__":
    print("🔧 memOS.as Tool Seeding Script")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_registered_tools()
    else:
        print("Seeding initial tools...")
        seed_initial_tools()
        print("\nUse --list to view all registered tools")