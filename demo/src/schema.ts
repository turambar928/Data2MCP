export type FieldSchema =
    | {
        kind: "string" | "number" | "boolean";
        title: string;
        default?: any;
        enum?: string[];
        secret?: boolean; // api_key这类
        description?: string;
    }
    | {
        kind: "object";
        title: string;
        targetRequired?: boolean; // 是否要求 _target_
        targetEnum?: string[]; // 允许的 _target_ 值
        defaultTarget?: string;
        fields: Record<string, FieldSchema>;
        description?: string;
    }
    | {
        kind: "array";
        title: string;
        item: FieldSchema;
        default?: any[];
        description?: string;
    };

// ==== LLM & Embedding Configs ====

export const LLMConfigSchema: FieldSchema = {
    kind: "object",
    title: "LLMConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.LLMConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.LLMConfig" },
        model: { kind: "string", title: "Model", default: "gpt-4-turbo" },
        temperature: { kind: "number", title: "Temperature", default: 0 },
        max_tokens: { kind: "number", title: "Max Tokens" },
        timeout_seconds: { kind: "number", title: "Timeout (sec)", default: 60 },
        max_retries: { kind: "number", title: "Max Retries", default: 3 },
        base_url: { kind: "string", title: "Base URL", description: "Optional custom API base URL" },
        api_key: { kind: "string", title: "API Key", secret: true, description: "API Key" },
    },
};

export const EmbeddingConfigSchema: FieldSchema = {
    kind: "object",
    title: "EmbeddingConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.EmbeddingConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.EmbeddingConfig" },
        model: { kind: "string", title: "Model", default: "text-embedding-3-large" },
        base_url: { kind: "string", title: "Base URL" },
        api_key: { kind: "string", title: "API Key", secret: true },
    },
};

// ==== Database Configs ====

export const SQLDBConfigSchema: FieldSchema = {
    kind: "object",
    title: "SQLDBConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.SQLDBConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.SQLDBConfig" },
        type: { kind: "string", title: "Type", enum: ["mysql", "postgresql", "sqlite"], default: "sqlite" },
        host: { kind: "string", title: "Host", description: "For MySQL/PostgreSQL" },
        port: { kind: "number", title: "Port", description: "For MySQL/PostgreSQL" },
        user: { kind: "string", title: "User", description: "For MySQL/PostgreSQL" },
        password: { kind: "string", title: "Password", secret: true, description: "For MySQL/PostgreSQL" },
        db_name: { kind: "string", title: "Database Name", description: "For MySQL/PostgreSQL" },
        file_path: { kind: "string", title: "File Path", description: "For SQLite" },
    },
};

export const KGConfigSchema: FieldSchema = {
    kind: "object",
    title: "KGConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.KGConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.KGConfig" },
        type: { kind: "string", title: "Type", default: "neo4j" },
        host: { kind: "string", title: "Host" },
        port: { kind: "number", title: "Port", default: 7687 },
        user: { kind: "string", title: "User", default: "neo4j" },
        password: { kind: "string", title: "Password", secret: true },
    },
};

export const VectorConfigSchema: FieldSchema = {
    kind: "object",
    title: "VectorConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.VectorConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.VectorConfig" },
        type: { kind: "string", title: "Type", default: "faiss" },
        data_path: { kind: "string", title: "Data Path", description: "Path to documents" },
        save_path: { kind: "string", title: "Save Path", description: "Path to save vector index" },
        index_name: { kind: "string", title: "Index Name", default: "index" },
        allow_dangerous_deserialization: { kind: "boolean", title: "Allow Dangerous Deserialization", default: false },
        embedding_config: EmbeddingConfigSchema,
        loader_kwargs: { kind: "string", title: "Loader Kwargs (JSON)", description: "JSON string for loader config" },
        splitter_kwargs: { kind: "string", title: "Splitter Kwargs (JSON)", description: "JSON string for splitter config" },
    },
};

export const DataFrameConfigSchema: FieldSchema = {
    kind: "object",
    title: "DataFrameConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.DataFrameConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.DataFrameConfig" },
        type: { kind: "string", title: "Type", enum: ["csv", "json"], default: "csv" },
        save_path: { kind: "string", title: "Save Path" },
    },
};

// ==== Agent Configs ====

export const SQLAgentConfigSchema: FieldSchema = {
    kind: "object",
    title: "SQLAgentConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.SQLAgentConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.SQLAgentConfig" },
        type: { kind: "string", title: "Type", default: "sql_agent" },
        tool_name: { kind: "string", title: "Tool Name" },
        tool_description: { kind: "string", title: "Tool Description" },
        agent_type: { kind: "string", title: "Agent Type", enum: ["tool-calling", "zero-shot-react-description"], default: "tool-calling" },
        llm_config: LLMConfigSchema,
        db_config: SQLDBConfigSchema,
    },
};

export const KGAgentConfigSchema: FieldSchema = {
    kind: "object",
    title: "KGAgentConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.KGAgentConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.KGAgentConfig" },
        type: { kind: "string", title: "Type", default: "kg_agent" },
        tool_name: { kind: "string", title: "Tool Name" },
        tool_description: { kind: "string", title: "Tool Description" },
        allow_dangerous_requests: { kind: "boolean", title: "Allow Dangerous Requests", default: false },
        validate_cypher: { kind: "boolean", title: "Validate Cypher", default: false },
        llm_config: LLMConfigSchema,
        db_config: KGConfigSchema,
    },
};

export const RAGAgentConfigSchema: FieldSchema = {
    kind: "object",
    title: "RAGAgentConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.RAGAgentConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.RAGAgentConfig" },
        type: { kind: "string", title: "Type", default: "rag_agent" },
        tool_name: { kind: "string", title: "Tool Name" },
        tool_description: { kind: "string", title: "Tool Description" },
        search_type: { kind: "string", title: "Search Type", enum: ["similarity", "mmr", "similarity_score_threshold"], default: "similarity" },
        top_k: { kind: "number", title: "Top K", default: 5 },
        score_threshold: { kind: "number", title: "Score Threshold", default: 0.8, description: "For similarity_score_threshold" },
        fetch_k: { kind: "number", title: "Fetch K", default: 20, description: "For MMR algorithm" },
        lambda_mult: { kind: "number", title: "Lambda Mult", default: 0.5, description: "Diversity for MMR" },
        llm_config: LLMConfigSchema,
        db_config: VectorConfigSchema,
    },
};

export const DataFrameAgentConfigSchema: FieldSchema = {
    kind: "object",
    title: "DataFrameAgentConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.DataFrameAgentConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.DataFrameAgentConfig" },
        type: { kind: "string", title: "Type", default: "dataframe_agent" },
        tool_name: { kind: "string", title: "Tool Name" },
        tool_description: { kind: "string", title: "Tool Description" },
        agent_type: { kind: "string", title: "Agent Type", enum: ["tool-calling", "zero-shot-react-description"], default: "tool-calling" },
        allow_dangerous_code: { kind: "boolean", title: "Allow Dangerous Code", default: false },
        verbose: { kind: "boolean", title: "Verbose", default: false },
        max_iterations: { kind: "number", title: "Max Iterations", default: 15 },
        include_df_in_prompt: { kind: "boolean", title: "Include DF in Prompt", default: true },
        number_of_head_rows: { kind: "number", title: "Number of Head Rows", default: 5 },
        engine: { kind: "string", title: "Engine", enum: ["pandas", "modin"], default: "pandas" },
        llm_config: LLMConfigSchema,
        db_config: DataFrameConfigSchema,
    },
};

export const AgentConfigSchema: FieldSchema = {
    kind: "object",
    title: "AgentConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.AgentConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.AgentConfig" },
        default_llm_config: LLMConfigSchema,
        agent_configs: {
            kind: "array",
            title: "Agent Configs",
            item: {
                kind: "object",
                title: "Agent Item",
                targetRequired: true,
                targetEnum: [
                    "data2mcp_v2.config.SQLAgentConfig",
                    "data2mcp_v2.config.KGAgentConfig",
                    "data2mcp_v2.config.RAGAgentConfig",
                    "data2mcp_v2.config.DataFrameAgentConfig",
                ],
                defaultTarget: "data2mcp_v2.config.SQLAgentConfig",
                fields: {} as any,
            },
        },
    },
};

// 顶层 schema
export const RootSchema: FieldSchema = {
    kind: "object",
    title: "Data2McpConfig",
    targetRequired: true,
    defaultTarget: "data2mcp_v2.config.Data2McpConfig",
    fields: {
        _target_: { kind: "string", title: "_target_", default: "data2mcp_v2.config.Data2McpConfig" },
        agents: AgentConfigSchema,
        route_type: {
            kind: "string",
            title: "Route Type",
            enum: ["selection", "fusion", "hybrid", "agentic"],
            default: "agentic",
        },
        llm: LLMConfigSchema,
        tool_call_timeout: { kind: "number", title: "Tool Call Timeout", default: 300 },
        tool_call_max_length: { kind: "number", title: "Tool Call Max Length", default: 10000 },
        max_turns: { kind: "number", title: "Max Turns", default: 15 },
    },
};

// _target_ -> schema 映射
export const TargetSchemaMap: Record<string, FieldSchema> = {
    "data2mcp_v2.config.Data2McpConfig": RootSchema,
    "data2mcp_v2.config.LLMConfig": LLMConfigSchema,
    "data2mcp_v2.config.EmbeddingConfig": EmbeddingConfigSchema,
    "data2mcp_v2.config.SQLDBConfig": SQLDBConfigSchema,
    "data2mcp_v2.config.KGConfig": KGConfigSchema,
    "data2mcp_v2.config.VectorConfig": VectorConfigSchema,
    "data2mcp_v2.config.DataFrameConfig": DataFrameConfigSchema,
    "data2mcp_v2.config.AgentConfig": AgentConfigSchema,
    "data2mcp_v2.config.SQLAgentConfig": SQLAgentConfigSchema,
    "data2mcp_v2.config.KGAgentConfig": KGAgentConfigSchema,
    "data2mcp_v2.config.RAGAgentConfig": RAGAgentConfigSchema,
    "data2mcp_v2.config.DataFrameAgentConfig": DataFrameAgentConfigSchema,
};
