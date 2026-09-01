import logging
import json

import pandas as pd
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ArgTransform
from langchain.agents import create_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import create_retriever_tool
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from data2mcp_v2.config import (
    DataFrameConfig,
    KGConfig,
    LLMConfig,
    SQLDBConfig,
)
from data2mcp_v2.config.db import DBType
from data2mcp_v2.config.db_agent import (
    AgentConfig,
    AgentType,
    DataFrameAgentConfig,
    KGAgentConfig,
    RAGAgentConfig,
    SQLAgentConfig,
)
from data2mcp_v2.utils.indexing import indexing_data
from data2mcp_v2.utils.tools import function2tool
from data2mcp_v2.server.data_tools.analysis_agent import analysis_agent
from data2mcp_v2.server.data_tools.chart_agent import chart_agent

logger = logging.getLogger(__name__)


async def create_db_query_tool(query: str, handler=None) -> str:
    try:
        # KG Agent
        if isinstance(handler, GraphCypherQAChain):
            result = await handler.ainvoke({"query": query})
            logger.debug(result)
            return result.get("result", "Can't Get Results from Agent.")
        elif isinstance(handler, AgentExecutor):
            # SQL Agent, DataFrame Agent And RAG Agent
            result = await handler.ainvoke({"input": query})
            logger.debug(result)
            return result.get("output", "Can't Get Results from Agent.")
        elif isinstance(handler, CompiledStateGraph):
            result = await handler.ainvoke({"messages": [{"role": "user", "content": query}]})
            logger.debug(result)
            return result["messages"][-1].content
        else:
            return f"Unsupported agent handler {type(handler)}."
    except Exception as e:
        return f"数据库查询过程中发生错误: {e}"


def init_sql_agent(sql_aget_config: SQLAgentConfig):
    # init sql db
    sql_config: SQLDBConfig = sql_aget_config.db_config
    user = sql_config.user
    password = sql_config.password
    host = sql_config.host
    port = sql_config.port
    db_type = sql_config.type
    db_name = sql_config.db_name
    if db_type == DBType.POSTGRESQL:
        db_uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == DBType.MYSQL:
        db_uri = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db_name}"
    elif db_type == DBType.SQLITE:
        db_uri = f"sqlite:///{sql_config.file_path}"
    else:
        raise ValueError(f"Unsupported SQL DB type: {db_type}")
    db = SQLDatabase.from_uri(db_uri)
    # init agent
    llm_config: LLMConfig = sql_aget_config.llm_config
    llm = ChatOpenAI(
        temperature=llm_config.temperature,
        model_name=llm_config.model,
        max_tokens=llm_config.max_tokens,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        timeout=llm_config.timeout_seconds,
        max_retries=llm_config.max_retries,
    )
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent_executor: AgentExecutor = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        agent_type=sql_aget_config.agent_type,
        handle_parsing_errors=True,
    )
    return agent_executor


def init_kg_agent(kg_agent_config: KGAgentConfig):
    # init kg
    kg_config: KGConfig = kg_agent_config.db_config
    db_type = kg_config.type
    if db_type == DBType.NEO4J:
        graph = Neo4jGraph(
            url=f"bolt://{kg_config.host}:{kg_config.port}",
            username=kg_config.user,
            password=kg_config.password,
        )
    else:
        raise ValueError(f"Unsupported KG DB type: {db_type}")
    # init agent
    llm_config: LLMConfig = kg_agent_config.llm_config
    llm = ChatOpenAI(
        temperature=llm_config.temperature,
        model_name=llm_config.model,
        max_tokens=llm_config.max_tokens,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        timeout=llm_config.timeout_seconds,
        max_retries=llm_config.max_retries,
    )
    agent_executor = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        allow_dangerous_requests=kg_agent_config.allow_dangerous_requests,
        validate_cypher=kg_agent_config.validate_cypher,
        return_intermediate_steps=True,
    )
    return agent_executor


def init_rag_agent(rag_agent_config: RAGAgentConfig):
    # init llm
    llm_config: LLMConfig = rag_agent_config.llm_config
    llm = ChatOpenAI(
        temperature=llm_config.temperature,
        model_name=llm_config.model,
        max_tokens=llm_config.max_tokens,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        timeout=llm_config.timeout_seconds,
        max_retries=llm_config.max_retries,
    )
    # init vector store
    vector_store = indexing_data(rag_agent_config.db_config)
    vector_store_retrieve = vector_store.as_retriever(
        search_type=rag_agent_config.search_type,
        search_kwargs={
            "k": rag_agent_config.top_k,
            "score_threshold": rag_agent_config.score_threshold,
            "fetch_k": rag_agent_config.fetch_k,
            "lambda_mult": rag_agent_config.lambda_mult,
        },
    )
    tool = create_retriever_tool(
        vector_store_retrieve,
        rag_agent_config.tool_name,
        rag_agent_config.tool_description,
    )
    agent_executor = create_agent(llm, [tool])
    return agent_executor


def init_dataframe_agent(dataframe_agent_config: DataFrameAgentConfig):
    dataframe_config: DataFrameConfig = dataframe_agent_config.db_config
    datarame_type = dataframe_config.type
    if datarame_type == DBType.CSV:
        data = pd.read_csv(dataframe_config.save_path)
    elif datarame_type == DBType.JSON:
        data = pd.read_json(dataframe_config.save_path)
    else:
        raise ValueError(f"Unsupported DataFrame DB type: {datarame_type}")
    llm_config: LLMConfig = dataframe_agent_config.llm_config
    llm = ChatOpenAI(
        temperature=llm_config.temperature,
        model_name=llm_config.model,
        max_tokens=llm_config.max_tokens,
        base_url=llm_config.base_url,
        api_key=llm_config.api_key,
        timeout=llm_config.timeout_seconds,
        max_retries=llm_config.max_retries,
    )
    agent_executor = create_pandas_dataframe_agent(
        llm,
        data,
        agent_type=dataframe_agent_config.agent_type,
        allow_dangerous_code=dataframe_agent_config.allow_dangerous_code,
        return_intermediate_steps=True,
        verbose=dataframe_agent_config.verbose,
        max_iterations=dataframe_agent_config.max_iterations,
        include_df_in_prompt=dataframe_agent_config.include_df_in_prompt,
        number_of_head_rows=dataframe_agent_config.number_of_head_rows,
        engine=dataframe_agent_config.engine,
    )
    return agent_executor


def init_db_agents(config: AgentConfig) -> list[Tool]:
    """
    init agents for db
    """
    logger.info("Initializing DB Agents...")

    db_tools: list[Tool] = []
    transform_args = {}
    for agent_config in config.agent_configs:
        agent_type = agent_config.type
        logger.info(f"Configured DB: {agent_config.tool_name} ({agent_type})")
        if agent_type == AgentType.SQL_AGENT:
            assert isinstance(agent_config, SQLAgentConfig), (
                f"{agent_type} must be use SQLAgentConfig"
            )
            agent_executor = init_sql_agent(agent_config)
        elif agent_type == AgentType.KG_AGENT:
            assert isinstance(agent_config, KGAgentConfig), (
                f"{agent_type} must be use KGAgentConfig"
            )
            agent_executor = init_kg_agent(agent_config)
        elif agent_type == AgentType.RAG_Agent:
            assert isinstance(agent_config, RAGAgentConfig), (
                f"{agent_type} must be use DenseAgentConfig"
            )
            agent_executor = init_rag_agent(agent_config)
        elif agent_type == AgentType.DataFrame_Agent:
            assert isinstance(agent_config, DataFrameAgentConfig), (
                f"{agent_type} must be use DataFrameAgentConfig"
            )
            agent_executor = init_dataframe_agent(agent_config)
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
        tool_handler = create_db_query_tool
        transform_args["handler"] = ArgTransform(default=agent_executor, hide=True)
        tool = function2tool(
            tool_handler,
            agent_config.tool_name,
            agent_config.tool_description,
            transform_args,
        )
        db_tools.append(tool)
        logger.info(f"{agent_type} Agent for {agent_config.tool_name} initialized.")

    # Add data analysis tool
    async def analyze_data_tool(query: str, data: str) -> str:
        """
        Analyze data and calculate growth rates, market shares, and statistics.

        Use this tool to get precise numerical calculations instead of manual computation.

        Args:
            query: Natural language description of what analysis to perform
                   Example: "Calculate growth rates and market shares"
            data: JSON string containing the data to analyze
                  Example: '{"Month":["Jan","Feb"],"Revenue":[100000,120000]}'

        Returns:
            Formatted analysis results with specific numbers, including:
            - Growth rates (total, average, max, min)
            - Market shares (percentages for each category)
            - Statistical metrics (mean, median, std, quartiles)
        """
        try:
            # Parse data if it's a JSON string
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass

            # Perform analysis
            result = analysis_agent.analyze_data(data, analysis_type="auto")
            formatted = analysis_agent.format_analysis_result(result)
            return formatted
        except Exception as e:
            logger.error(f"Error in analyze_data_tool: {e}")
            return f"Analysis error: {str(e)}"

    analysis_tool = function2tool(
        analyze_data_tool,
        "data_analysis_tool",
        "Calculate growth rates, market shares, and statistical metrics from data. Use this to get specific numerical values and percentages.",
        {}
    )
    db_tools.append(analysis_tool)
    logger.info("Data Analysis Tool initialized.")

    # Add chart generation tool
    async def generate_chart_tool(
        data: str,
        chart_type: str = "line",
        title: str = "Chart",
        x_label: str = "X",
        y_label: str = "Y"
    ) -> str:
        """
        🔴 MANDATORY: Generate charts (line, bar, scatter, heatmap) from data.

        ⚠️ YOU MUST call this tool 2-3 times for EVERY data analysis task.
        ⚠️ DO NOT write markdown references like ![Chart](file.png) without calling this tool first.

        Args:
            data: JSON string containing the data to visualize.
                  Example: '{"Month":["Jan","Feb","Mar"],"Revenue":[100000,120000,135000]}'
            chart_type: Type of chart to generate:
                  - "line": For trends over time
                  - "bar": For comparisons between categories
                  - "scatter": For correlations between two variables
                  - "heatmap": For correlation matrices
            title: Chart title (e.g., "Revenue Growth Trend")
            x_label: X-axis label (e.g., "Month")
            y_label: Y-axis label (e.g., "Revenue ($)")

        Returns:
            Markdown image reference that you MUST include in your final answer
            Example: "Chart generated successfully: ![Revenue Trend](line_Revenue_Trend.png)"
        """
        try:
            # Parse data if it's a JSON string
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    pass

            # Generate chart
            result = chart_agent.generate_chart(
                data=data,
                chart_type=chart_type,
                title=title,
                x_label=x_label,
                y_label=y_label
            )

            if "error" in result:
                return f"Chart generation error: {result['error']}"

            return f"Chart generated successfully: {result['markdown']}\nFile saved at: {result['filepath']}"
        except Exception as e:
            logger.error(f"Error in generate_chart_tool: {e}")
            return f"Chart generation error: {str(e)}"

    chart_tool = function2tool(
        generate_chart_tool,
        "chart_generation_tool",
        "🔴 MANDATORY: Generate visualizations (line/bar/scatter/heatmap) from data. YOU MUST call this tool 2-3 times for EVERY data analysis task. DO NOT fabricate chart filenames - always call this tool to generate real charts.",
        {}
    )
    db_tools.append(chart_tool)
    logger.info("Chart Generation Tool initialized.")

    return db_tools
