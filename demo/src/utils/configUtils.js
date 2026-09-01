/**
 * Configuration Utilities for Data2MCP
 *
 * This module provides functions to convert frontend dataset configurations
 * to backend-compatible configuration objects.
 *
 * ## Supported Agent Types:
 * - **DataFrame Agents** (csv, json): Query structured data files using pandas
 * - **RAG Agents** (rag): Vector similarity search over text documents
 * - **SQL Agents** (sql): Query SQL databases (MySQL, PostgreSQL, SQLite)
 * - **Knowledge Graph Agents** (neo4j): Query Neo4j graph databases with Cypher
 *
 * ## Adding New Agent Types:
 *
 * 1. Add the type mapping to AGENT_TYPE_REGISTRY:
 *    ```javascript
 *    const AGENT_TYPE_REGISTRY = {
 *      csv: 'dataframe',
 *      your_new_type: 'your_agent_name',
 *    };
 *    ```
 *
 * 2. Create a builder function following the pattern:
 *    ```javascript
 *    function buildYourAgentConfig(dataset, llmConfig, embeddingConfig) {
 *      return {
 *        _target_: 'data2mcp_v2.config.YourAgentConfig',
 *        tool_name: dataset.name,
 *        tool_description: dataset.description,
 *        type: 'your_agent_type',
 *        llm_config: llmConfig,
 *        db_config: {
 *          _target_: 'data2mcp_v2.config.YourDBConfig',
 *          // ... your specific fields
 *        },
 *      };
 *    }
 *    ```
 *
 * 3. Register the builder in AGENT_BUILDERS:
 *    ```javascript
 *    const AGENT_BUILDERS = {
 *      rag: buildRAGAgentConfig,
 *      your_agent_name: buildYourAgentConfig,
 *    };
 *    ```
 *
 * 4. Update TYPE_COLORS in constants/index.js for UI display
 */

/**
 * Agent type registry - maps frontend data types to backend config builders
 * Document types (md, txt, pdf, html, etc.) all map to RAG agent
 */
const AGENT_TYPE_REGISTRY = {
  // Structured data files → DataFrame agent
  csv: 'dataframe',
  json: 'dataframe',

  // Document types → RAG agent (vector search)
  md: 'rag',
  txt: 'rag',
  pdf: 'rag',
  html: 'rag',
  doc: 'rag',
  docx: 'rag',

  // Databases
  sql: 'sql',
  neo4j: 'kg',
};

/**
 * Field schema definitions for each data type
 * Categorizes fields as 'essential' (always shown) or 'advanced' (shown on expand)
 */

// Shared schema for all document types (md, txt, pdf, html, etc.) → RAG agent
const DOCUMENT_SCHEMA = {
  essential: [
    { key: 'name', label: 'Name', type: 'text', placeholder: 'my_documents' },
    { key: 'description', label: 'Description', type: 'text', placeholder: 'Document collection description' },
    { key: 'path', label: 'File Path', type: 'text', placeholder: './data/documents.md' },
  ],
  advanced: [
    { key: 'search_type', label: 'Search Type', type: 'select', options: ['similarity', 'mmr'], default: 'similarity' },
    { key: 'top_k', label: 'Top K Results', type: 'number', default: 5, min: 1, max: 20 },
    { key: 'score_threshold', label: 'Score Threshold', type: 'number', default: 0.8, min: 0, max: 1, step: 0.05 },
    { key: 'fetch_k', label: 'Fetch K (MMR)', type: 'number', default: 20, min: 1, max: 100 },
    { key: 'lambda_mult', label: 'Lambda Multiplier (MMR)', type: 'number', default: 0.5, min: 0, max: 1, step: 0.1 },
    { key: 'save_path', label: 'Vector Store Path', type: 'text', default: './data/benchmark/DABStep/vector_store/' },
    { key: 'index_name', label: 'Index Name', type: 'text', placeholder: 'auto-generated from name' },
    { key: 'chunk_size', label: 'Chunk Size', type: 'number', default: 1000, min: 100, max: 5000, group: 'splitter_kwargs' },
    { key: 'chunk_overlap', label: 'Chunk Overlap', type: 'number', default: 0, min: 0, max: 500, group: 'splitter_kwargs' },
    { key: 'encoding', label: 'Text Encoding', type: 'text', default: 'utf-8', group: 'loader_kwargs' },
  ],
};

export const FIELD_SCHEMAS = {
  csv: {
    essential: [
      { key: 'name', label: 'Name', type: 'text', placeholder: 'my_dataset' },
      { key: 'description', label: 'Description', type: 'text', placeholder: 'Dataset description' },
      { key: 'path', label: 'File Path', type: 'text', placeholder: './data/file.csv' },
    ],
    advanced: [
      { key: 'agent_type', label: 'Agent Type', type: 'select', options: ['tool-calling', 'openai-functions'], default: 'tool-calling' },
      { key: 'allow_dangerous_code', label: 'Allow Dangerous Code', type: 'boolean', default: true },
      { key: 'verbose', label: 'Verbose Logging', type: 'boolean', default: false },
      { key: 'max_iterations', label: 'Max Iterations', type: 'number', default: 15, min: 1, max: 50 },
      { key: 'include_df_in_prompt', label: 'Include DataFrame in Prompt', type: 'boolean', default: true },
      { key: 'number_of_head_rows', label: 'Number of Head Rows', type: 'number', default: 3, min: 1, max: 20 },
      { key: 'engine', label: 'Engine', type: 'select', options: ['pandas', 'modin'], default: 'pandas' },
    ],
  },
  json: {
    essential: [
      { key: 'name', label: 'Name', type: 'text', placeholder: 'my_dataset' },
      { key: 'description', label: 'Description', type: 'text', placeholder: 'Dataset description' },
      { key: 'path', label: 'File Path', type: 'text', placeholder: './data/file.json' },
    ],
    advanced: [
      { key: 'agent_type', label: 'Agent Type', type: 'select', options: ['tool-calling', 'openai-functions'], default: 'tool-calling' },
      { key: 'allow_dangerous_code', label: 'Allow Dangerous Code', type: 'boolean', default: true },
      { key: 'verbose', label: 'Verbose Logging', type: 'boolean', default: false },
      { key: 'max_iterations', label: 'Max Iterations', type: 'number', default: 15, min: 1, max: 50 },
      { key: 'include_df_in_prompt', label: 'Include DataFrame in Prompt', type: 'boolean', default: true },
      { key: 'number_of_head_rows', label: 'Number of Head Rows', type: 'number', default: 3, min: 1, max: 20 },
      { key: 'engine', label: 'Engine', type: 'select', options: ['pandas', 'modin'], default: 'pandas' },
    ],
  },

  // Document types - all use the same RAG agent schema
  md: DOCUMENT_SCHEMA,
  txt: DOCUMENT_SCHEMA,
  pdf: DOCUMENT_SCHEMA,
  html: DOCUMENT_SCHEMA,
  doc: DOCUMENT_SCHEMA,
  docx: DOCUMENT_SCHEMA,

  sql: {
    essential: [
      { key: 'name', label: 'Name', type: 'text', placeholder: 'my_database' },
      { key: 'description', label: 'Description', type: 'text', placeholder: 'Database description' },
      { key: 'db_type', label: 'Database Type', type: 'select', options: ['sqlite', 'mysql', 'postgresql'], default: 'sqlite' },
    ],
    advanced: [
      { key: 'agent_type', label: 'Agent Type', type: 'select', options: ['tool-calling', 'openai-functions'], default: 'tool-calling' },
      // SQLite-specific
      { key: 'path', label: 'Database File Path', type: 'text', placeholder: './data/database.db', condition: { key: 'db_type', value: 'sqlite' } },
      // MySQL/PostgreSQL-specific
      { key: 'host', label: 'Host', type: 'text', default: 'localhost', condition: { key: 'db_type', value: ['mysql', 'postgresql'] } },
      { key: 'port', label: 'Port', type: 'number', default: 3306, condition: { key: 'db_type', value: ['mysql', 'postgresql'] } },
      { key: 'user', label: 'Username', type: 'text', placeholder: 'db_user', condition: { key: 'db_type', value: ['mysql', 'postgresql'] } },
      { key: 'password', label: 'Password', type: 'password', placeholder: '••••••', condition: { key: 'db_type', value: ['mysql', 'postgresql'] } },
      { key: 'db_name', label: 'Database Name', type: 'text', placeholder: 'my_database', condition: { key: 'db_type', value: ['mysql', 'postgresql'] } },
    ],
  },
  neo4j: {
    essential: [
      { key: 'name', label: 'Name', type: 'text', placeholder: 'my_knowledge_graph' },
      { key: 'description', label: 'Description', type: 'text', placeholder: 'Knowledge graph description' },
      { key: 'host', label: 'Host', type: 'text', default: 'localhost', placeholder: 'bolt://localhost' },
    ],
    advanced: [
      { key: 'port', label: 'Port', type: 'number', default: 7687 },
      { key: 'user', label: 'Username', type: 'text', default: 'neo4j' },
      { key: 'password', label: 'Password', type: 'password', placeholder: '••••••' },
      { key: 'allow_dangerous_requests', label: 'Allow Dangerous Requests', type: 'boolean', default: false },
      { key: 'validate_cypher', label: 'Validate Cypher Queries', type: 'boolean', default: false },
    ],
  },
};

/**
 * Get field schema for a specific agent type
 */
export function getFieldSchema(type) {
  return FIELD_SCHEMAS[type] || FIELD_SCHEMAS.csv;
}

/**
 * Check if a field should be displayed based on conditions
 */
export function shouldDisplayField(field, dataset) {
  if (!field.condition) return true;

  const conditionKey = field.condition.key;
  const conditionValue = field.condition.value;
  const datasetValue = dataset[conditionKey];

  if (Array.isArray(conditionValue)) {
    return conditionValue.includes(datasetValue);
  }

  return datasetValue === conditionValue;
}

/**
 * Build LLM configuration
 */
function buildLLMConfig(llmConfig) {
  return {
    _target_: 'data2mcp_v2.config.LLMConfig',
    model: llmConfig.model,
    temperature: llmConfig.temperature,
    max_tokens: llmConfig.max_tokens,
    timeout_seconds: 600,
    max_retries: 3,
    base_url: llmConfig.base_url,
    api_key: llmConfig.api_key,
  };
}

/**
 * Build embedding configuration for RAG agents
 * Model name is always explicit from embeddingConfig
 * Base URL and API key fall back to LLM config if empty
 */
function buildEmbeddingConfig(llmConfig, embeddingConfig = null) {
  const defaultModel = 'text-embedding-v4';

  return {
    _target_: 'data2mcp_v2.config.EmbeddingConfig',
    model: embeddingConfig?.model || defaultModel,
    base_url: embeddingConfig?.base_url || llmConfig.base_url,
    api_key: embeddingConfig?.api_key || llmConfig.api_key,
    dimensions: embeddingConfig?.dimensions || null,
    encoding_format: embeddingConfig?.encoding_format || 'base64',
    chunk_size: embeddingConfig?.chunk_size || 1000,
  };
}

/**
 * Build RAG Agent Configuration
 */
function buildRAGAgentConfig(dataset, llmConfig, embeddingConfig) {
  return {
    _target_: 'data2mcp_v2.config.RAGAgentConfig',
    tool_name: dataset.name,
    tool_description: dataset.description,
    type: 'rag_agent',
    search_type: dataset.search_type || 'similarity',
    top_k: dataset.top_k || 5,
    score_threshold: dataset.score_threshold || 0.8,
    fetch_k: dataset.fetch_k || 20,
    lambda_mult: dataset.lambda_mult || 0.5,
    llm_config: llmConfig,
    db_config: {
      _target_: 'data2mcp_v2.config.VectorConfig',
      type: 'faiss',
      data_path: dataset.path,
      save_path: dataset.save_path || './data/benchmark/DABStep/vector_store/',
      index_name: dataset.index_name || `${dataset.name}_${embeddingConfig?.model || 'Unknown'}_index`,
      allow_dangerous_deserialization: true,
      loader_kwargs: dataset.loader_kwargs || {
        encoding: 'utf-8',
      },
      splitter_kwargs: dataset.splitter_kwargs || {
        chunk_size: 1000,
        chunk_overlap: 0,
      },
      embedding_config: embeddingConfig,
    },
  };
}

/**
 * Build DataFrame Agent Configuration
 */
function buildDataFrameAgentConfig(dataset, llmConfig) {
  return {
    _target_: 'data2mcp_v2.config.DataFrameAgentConfig',
    tool_name: dataset.name,
    tool_description: dataset.description,
    type: 'dataframe_agent',
    agent_type: dataset.agent_type || 'tool-calling',
    allow_dangerous_code: dataset.allow_dangerous_code ?? true,
    verbose: dataset.verbose ?? false,
    max_iterations: dataset.max_iterations || 15,
    include_df_in_prompt: dataset.include_df_in_prompt ?? true,
    number_of_head_rows: dataset.number_of_head_rows || 3,
    engine: dataset.engine || 'pandas',
    llm_config: llmConfig,
    db_config: {
      _target_: 'data2mcp_v2.config.DataFrameConfig',
      type: dataset.type,
      save_path: dataset.path,
    },
  };
}

/**
 * Build SQL Agent Configuration
 */
function buildSQLAgentConfig(dataset, llmConfig) {
  return {
    _target_: 'data2mcp_v2.config.SQLAgentConfig',
    tool_name: dataset.name,
    tool_description: dataset.description,
    type: 'sql_agent',
    agent_type: dataset.agent_type || 'tool-calling',
    llm_config: llmConfig,
    db_config: {
      _target_: 'data2mcp_v2.config.SQLDBConfig',
      type: dataset.db_type || 'sqlite', // mysql, postgresql, sqlite
      ...(dataset.db_type === 'sqlite'
        ? { file_path: dataset.path }
        : {
          host: dataset.host,
          port: dataset.port,
          user: dataset.user,
          password: dataset.password,
          db_name: dataset.db_name,
        }
      ),
    },
  };
}

/**
 * Build Knowledge Graph Agent Configuration
 */
function buildKGAgentConfig(dataset, llmConfig) {
  return {
    _target_: 'data2mcp_v2.config.KGAgentConfig',
    tool_name: dataset.name,
    tool_description: dataset.description,
    type: 'kg_agent',
    allow_dangerous_requests: dataset.allow_dangerous_requests ?? false,
    validate_cypher: dataset.validate_cypher ?? false,
    llm_config: llmConfig,
    db_config: {
      _target_: 'data2mcp_v2.config.KGConfig',
      type: 'neo4j',
      host: dataset.host,
      port: dataset.port || 7687,
      user: dataset.user,
      password: dataset.password,
    },
  };
}

/**
 * Agent config builders registry
 */
const AGENT_BUILDERS = {
  rag: buildRAGAgentConfig,
  dataframe: buildDataFrameAgentConfig,
  sql: buildSQLAgentConfig,
  kg: buildKGAgentConfig,
};

/**
 * Build agent configuration based on dataset type
 */
function buildAgentConfig(dataset, llmConfig, embeddingConfig) {
  const agentType = AGENT_TYPE_REGISTRY[dataset.type];

  if (!agentType) {
    console.warn(`Unknown agent type: ${dataset.type}, defaulting to dataframe`);
    return buildDataFrameAgentConfig(dataset, llmConfig);
  }

  const builder = AGENT_BUILDERS[agentType];
  if (!builder) {
    throw new Error(`No builder found for agent type: ${agentType}`);
  }

  return builder(dataset, llmConfig, embeddingConfig);
}

/**
 * Convert frontend configuration to backend-compatible format
 * Matches the exact structure expected by data2mcp_v2 backend
 *
 * @param {Array} datasets - List of dataset configurations
 * @param {Object} llmConfig - LLM configuration (model, temperature, api_key, etc.)
 * @param {Object} embeddingConfig - Embedding configuration (model, base_url, api_key)
 *        - model: Embedding model name (always used)
 *        - base_url: Override URL (empty = inherit from llmConfig)
 *        - api_key: Override key (empty = inherit from llmConfig)
 * @param {string} selectedStrategy - Selected strategy key
 * @param {Object} strategies - Available strategies
 * @param {string} customStrategyText - Custom strategy text (if strategy is 'custom')
 * @returns {Object} Backend-compatible configuration object
 */
function formatDataSummary(summary) {
  if (!summary || !Array.isArray(summary.sources) || summary.sources.length === 0) {
    return 'No data summary available.';
  }

  const lines = summary.sources.map((source, idx) => {
    const name = source.name || `source_${idx + 1}`;
    const agentType = source.agent_type || 'unknown';
    const dataType = source.data_type || source.db_type || 'unknown';
    const size = source.size_human || source.total_size_human || 'unknown';
    const rows = source.row_count !== undefined && source.row_count !== null
      ? `rows=${source.row_count}`
      : null;
    const columns = Array.isArray(source.columns) && source.columns.length > 0
      ? `columns=${source.columns.slice(0, 10).join(', ')}`
      : null;
    const extra = [rows, columns].filter(Boolean).join('; ');
    return `- ${name} (${agentType}): type=${dataType}; size=${size}${extra ? `; ${extra}` : ''}`;
  });

  return [
    'Data Summary:',
    ...lines
  ].join('\n');
}

export function convertToBackendConfig(
  datasets,
  llmConfig,
  embeddingConfig,
  selectedStrategy,
  strategies,
  customStrategyText,
  dataSummary = null,
  userQuestion = ''
) {
  // Get retrieval strategy text
  const strategyObj = strategies[selectedStrategy];
  let retrievalStrategyText = '';
  if (strategyObj) {
    if (selectedStrategy === 'custom') {
      retrievalStrategyText = customStrategyText || 'Please define your custom retrieval strategy.';
    } else if (selectedStrategy === 'auto') {
      const availableStrategies = Object.entries(strategies)
        .filter(([key]) => key !== 'custom' && key !== 'auto')
        .map(([key, strategy]) => {
          const title = strategy?.name || key;
          const fullText = strategy?.fullText || '';
          return `- ${title}: ${fullText}`;
        })
        .join('\n');

      const summaryText = formatDataSummary(dataSummary);
      const questionText = userQuestion ? `User Question: ${userQuestion}` : 'User Question: (not provided)';

      retrievalStrategyText = [
        'Auto Strategy Selection:',
        'Based on the user request and the available data sources, select exactly ONE strategy from the list below.',
        'Then follow that strategy strictly for retrieval and synthesis.',
        'Do not mix strategies or switch mid-way unless the chosen strategy explicitly requires it.',
        '',
        questionText,
        summaryText,
        '',
        'Available strategies:',
        availableStrategies,
      ].join('\n');
    } else {
      retrievalStrategyText = strategyObj.fullText;
    }
  }

  // Build shared configurations
  const defaultLLMConfig = buildLLMConfig(llmConfig);
  const defaultEmbeddingConfig = buildEmbeddingConfig(llmConfig, embeddingConfig);

  return {
    _target_: 'data2mcp_v2.config.Data2McpConfig',
    route_type: 'agentic',
    tool_call_timeout: 300,
    tool_call_max_length: 10000,
    max_turns: 15,
    retrieval_strategy: retrievalStrategyText,
    llm: defaultLLMConfig,
    agents: {
      _target_: 'data2mcp_v2.config.AgentConfig',
      default_llm_config: defaultLLMConfig,
      agent_configs: datasets
        .filter(d => d.enabled)
        .map(d => buildAgentConfig(d, defaultLLMConfig, defaultEmbeddingConfig)),
    },
  };
}
