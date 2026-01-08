# SundayGraph Frontend

Next.js frontend for SundayGraph Knowledge Graph System.

## Features

- **Schema Building**: Build ontology schemas from domain descriptions using AI
- **Data Ingestion**: Upload files or paste text to populate the knowledge graph
- **Query Interface**: Search and explore the knowledge graph
- **Statistics Dashboard**: View graph statistics and metadata

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)

## Docker

The frontend is included in the main docker-compose.yml file.

```bash
docker-compose up frontend
```

