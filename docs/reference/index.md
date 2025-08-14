# API Reference

Complete technical reference for the memOS.as API and services.

## FastAPI Endpoints

The memOS.as service provides the following REST API endpoints:

### Health & Status
- `GET /health` - System health check
- `GET /status` - Detailed service status

### Memory Operations
- `POST /memory/store` - Store new memory entries
- `POST /memory/query` - Search memories semantically

### Tool Management
- `POST /tools/register` - Register new tools
- `GET /tools` - List available tools
- `GET /tools/search` - Search tools by context

### Graph Operations (Future)
- `POST /graph/query` - Query knowledge graph
- `GET /graph/explore` - Explore graph relationships

### Historical Logs (Future)
- `POST /log/event` - Log system events
- `GET /history` - Retrieve historical data

## Data Models

### Core Models
- `StoreRequest` - Memory storage request
- `QueryRequest` - Memory query request  
- `ToolRegistrationRequest` - Tool registration request

### Database Models
- `Memory` - Memory storage table
- `RegisteredTool` - Tool registry table
- `DailyLog` - Historical event logs (future)

For detailed API documentation with examples, see [Services](services.md).