<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Creating and Registering Tools in FastMCP

FastMCP provides a powerful and intuitive way to create tools - server-side functions that clients can execute remotely. Think of tools as specialized instruments in a workshop that clients can request to use for specific tasks.

## Basic Tool Creation

The simplest way to create a tool is using the `@server.tool()` decorator:[^1]

```python
from fastmcp import FastMCP

mcp = FastMCP("Demo Server")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```


## Tool Registration with Custom Parameters

You can customize tool registration by specifying a name and description:[^1]

```python
@mcp.tool(name="calculator_add", description="Adds two numbers together")
def add_numbers(num1: int, num2: int) -> int:
    """
    This function is registered as the 'calculator_add' tool.
    Type hints are crucial for FastMCP to understand expected inputs.
    """
    print(f"Tool 'calculator_add' called with {num1} and {num2}")
    result = num1 + num2
    print(f"Returning result: {result}")
    return result
```


## Type Hints Are Essential

**Type hints are crucial** for tool registration. FastMCP uses them to:[^1]

- Validate input from clients automatically
- Generate documentation about expected arguments
- Define return types for proper response handling

```python
@mcp.tool()
def process_data(name: str, age: int, active: bool) -> dict:
    """Process user data and return formatted information"""
    return {
        "message": f"Hello {name}",
        "status": "active" if active else "inactive",
        "category": "adult" if age >= 18 else "minor"
    }
```


## How Tool Registration Works

When you use the `@mcp.tool()` decorator, FastMCP performs these steps:[^1]

1. **Function Inspection**: Analyzes your function's parameters and return type using Python's introspection
2. **Schema Generation**: Creates a schema describing expected input arguments
3. **Tool Object Creation**: Wraps your function in a `Tool` object with metadata
4. **Registration**: Stores the tool in the internal `ToolManager` dictionary

## Tool Discovery and Execution

Once registered, clients can interact with your tools through the MCP protocol:[^1]

1. **Discovery**: Clients call `listTools` to see available tools with their descriptions and expected arguments
2. **Invocation**: Clients call `callTool` with the tool name and required arguments
3. **Validation**: FastMCP validates arguments against the tool's schema
4. **Execution**: Your function runs with the provided arguments
5. **Response**: Results are sent back to the client

## Advanced Tool Examples

### Database Query Tool

```python
@mcp.tool(description="Query user information from database")
def get_user(user_id: int) -> dict:
    """Retrieve user data by ID"""
    # Database query logic here
    return {"id": user_id, "name": "John Doe", "email": "john@example.com"}
```


### File Processing Tool

```python
@mcp.tool(description="Process and analyze text files")
def analyze_text(filename: str, word_count: bool = True) -> dict:
    """Analyze text file and return statistics"""
    # File processing logic
    return {
        "filename": filename,
        "word_count": 150 if word_count else None,
        "processed": True
    }
```


## Tool Manager Behind the Scenes

While you interact with the `@mcp.tool()` decorator, the `ToolManager` handles the heavy lifting:[^1]

- Maintains a dictionary mapping tool names to `Tool` objects
- Provides tool lists for `listTools` requests
- Validates arguments against tool schemas
- Executes functions and handles errors
- Returns results to clients


## Integration with ToolRegistry

For more advanced use cases, FastMCP tools can be integrated with external systems like ToolRegistry:[^2]

```python
from toolregistry import ToolRegistry

# Register FastMCP tools
registry = ToolRegistry()
fastmcp_server = FastMCP(name="MyServer")

# Add tools to FastMCP
@fastmcp_server.tool()
def multiply(x: int, y: int) -> int:
    return x * y

# Register with ToolRegistry for broader integration
registry.register_from_mcp(fastmcp_server)
```


## Best Practices

1. **Use Descriptive Names**: Choose clear, descriptive names for your tools
2. **Add Comprehensive Descriptions**: Help clients understand what each tool does
3. **Implement Proper Type Hints**: Essential for validation and documentation
4. **Handle Errors Gracefully**: Include error handling in your tool functions
5. **Keep Tools Focused**: Each tool should have a single, well-defined purpose

FastMCP's tool system makes it simple to expose server functionality to clients while maintaining proper validation and documentation automatically.[^3][^1]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^4][^5][^6][^7][^8][^9]</span>

<div style="text-align: center">⁂</div>

[^1]: https://the-pocket.github.io/PocketFlow-Tutorial-Codebase-Knowledge/MCP Python SDK/04_fastmcp_tools___tool____toolmanager__.html

[^2]: https://toolregistry.readthedocs.io/en/stable/usage/integrations/mcp.html

[^3]: https://github.com/jlowin/fastmcp

[^4]: https://journals.sagepub.com/doi/10.3233/SJI-240032

[^5]: https://ieeexplore.ieee.org/document/10427782/

[^6]: https://www.semanticscholar.org/paper/e31ceae7e0a5450b9a37b63830dec7e03cf9f399

[^7]: https://bmcmusculoskeletdisord.biomedcentral.com/articles/10.1186/s12891-022-05062-w

[^8]: https://qir.bmj.com/lookup/doi/10.1136/bmjoq-2021-001804

[^9]: https://morepress.unizd.hr/journals/index.php/pubmet/article/view/4276

[^10]: http://link.springer.com/10.1007/s10072-018-3610-0

[^11]: https://link.springer.com/10.1007/s00113-024-01487-1

[^12]: https://www.researchprotocols.org/2024/1/e58389

[^13]: https://www.tandfonline.com/doi/full/10.1080/17538947.2023.2198778

[^14]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10989850/

[^15]: http://arxiv.org/pdf/2410.15479.pdf

[^16]: https://www.mdpi.com/1424-8220/22/17/6333/pdf?version=1661756623

[^17]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10126156/

[^18]: http://arxiv.org/pdf/1204.5402.pdf

[^19]: https://dl.acm.org/doi/pdf/10.1145/3576915.3616664

[^20]: http://arxiv.org/pdf/2403.18374.pdf

[^21]: https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/imt2.107

[^22]: http://arxiv.org/pdf/2403.18149.pdf

[^23]: http://arxiv.org/pdf/2305.10612.pdf

[^24]: https://gofastmcp.com/getting-started/quickstart

[^25]: https://evo-byte.com/building-llm-tools-with-fastmcp/

[^26]: https://mcpservers.org/servers/hannguyendd/fastapi-with-mcp

[^27]: https://deepwiki.com/jlowin/fastmcp/2.2-resource-templates

