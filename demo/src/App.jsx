import { useState, useEffect, useMemo, useRef } from 'react';
import { load as loadYaml } from 'js-yaml';
import DatasetConfigPanel from './components/DatasetConfigPanel';
import ChatHeader from './components/ChatHeader';
import ChatMessages from './components/ChatMessages';
import DataSummaryModal from './components/DataSummaryModal';
import { DEFAULT_DATASETS, STRATEGIES } from './constants';
import { bundleToolCalls, splitMessages } from './utils/messageUtils';
import { convertToBackendConfig } from './utils/configUtils';
import { saveConfig, loadConfig, clearConfig } from './utils/configPersistence';

// Default configurations (for reset functionality)
const DEFAULT_LLM_CONFIG = {
  model: 'gpt-4o-mini',
  max_tokens: 8192,
  temperature: 0,
  base_url: 'https://api.openai.com/v1',
  api_key: '',
};

const DEFAULT_EMBEDDING_CONFIG = {
  model: 'text-embedding-v4',
  base_url: '',
  api_key: '',
  dimensions: null,
  encoding_format: 'float',
  chunk_size: 10,
};

const DEFAULT_API_CONFIG = {
  api_base_url: import.meta.env.BACKEND_BASE_URL || '',
};

export default function AgentDebugger() {
  // 数据集配置状态
  const [datasets, setDatasets] = useState(DEFAULT_DATASETS);
  const [llmConfig, setLLMConfig] = useState(DEFAULT_LLM_CONFIG);
  const [embeddingConfig, setEmbeddingConfig] = useState(DEFAULT_EMBEDDING_CONFIG);
  const [apiConfig, setApiConfig] = useState(DEFAULT_API_CONFIG);

  const [showConfig, setShowConfig] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Agent Configured. Ready to connect data sources.' }
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // Strategy 状态（Retrieval Strategy - Intelligence Analysis Methods）
  const [selectedStrategy, setSelectedStrategy] = useState('auto');
  const [customStrategyText, setCustomStrategyText] = useState('');
  const [showStrategyMenu, setShowStrategyMenu] = useState(false);
  // 动态策略：内置 STRATEGIES + 后端提取策略合并
  const [strategies, setStrategies] = useState(STRATEGIES);
  const [showDataSummary, setShowDataSummary] = useState(false);
  const [dataSummary, setDataSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState('');

  // 是否折叠 system 轨迹（默认折叠）
  const [showTrace, setShowTrace] = useState(false);
  const [finalText, setFinalText] = useState('');
  const [strategyUsed, setStrategyUsed] = useState('');
  const [outputComplianceScore, setOutputComplianceScore] = useState(null);

  // 自动滚动到底部
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Textarea 引用和自动调整高度
  const textareaRef = useRef(null);
  useEffect(() => {
    if (textareaRef.current && !input) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input]);

  // Load saved configuration on mount
  useEffect(() => {
    let cancelled = false;

    const loadYamlDefaults = async () => {
      try {
        const response = await fetch('/config.yaml', { cache: 'no-store' });
        if (!response.ok) return null;
        const text = await response.text();
        const yamlConfig = loadYaml(text);
        if (!yamlConfig || typeof yamlConfig !== 'object') return null;
        const llmConfigFromYaml =
          yamlConfig.llm ||
          yamlConfig.agents?.default_llm_config ||
          yamlConfig.agents?.agent_configs?.[0]?.llm_config ||
          null;
        if (!llmConfigFromYaml || typeof llmConfigFromYaml !== 'object') return null;
        return {
          model: llmConfigFromYaml.model,
          temperature: llmConfigFromYaml.temperature,
          max_tokens: llmConfigFromYaml.max_tokens,
          base_url: llmConfigFromYaml.base_url,
          api_key: llmConfigFromYaml.api_key,
        };
      } catch (error) {
        console.warn('Failed to load config.yaml defaults:', error);
        return null;
      }
    };

    const init = async () => {
      const savedConfig = loadConfig();
      if (savedConfig) {
        if (savedConfig.datasets) setDatasets(savedConfig.datasets);
        if (savedConfig.llmConfig) setLLMConfig(savedConfig.llmConfig);
        if (savedConfig.embeddingConfig) setEmbeddingConfig(savedConfig.embeddingConfig);
        if (savedConfig.apiConfig) setApiConfig(savedConfig.apiConfig);
        if (savedConfig.darkMode !== undefined) setDarkMode(savedConfig.darkMode);
        if (savedConfig.selectedStrategy) setSelectedStrategy(savedConfig.selectedStrategy);
        if (savedConfig.customStrategyText) setCustomStrategyText(savedConfig.customStrategyText);
        console.log('Loaded saved configuration');
      }

      const yamlLlmDefaults = await loadYamlDefaults();
      if (!cancelled && yamlLlmDefaults) {
        setLLMConfig(prev => ({
          ...prev,
          ...Object.fromEntries(
            Object.entries(yamlLlmDefaults).filter(([, value]) => value !== undefined && value !== null)
          ),
        }));
      }

      // 从后端拉取提取的策略，合并到内置策略中
      try {
        const res = await fetch(buildApiUrl('/api/strategies'));
        if (res.ok) {
          const data = await res.json();
          const merged = { ...STRATEGIES };
          for (const spec of (data.strategies || [])) {
            if (spec.source !== 'builtin' && spec.key && spec.key !== 'custom') {
              merged[spec.key] = {
                name: spec.name,
                shortName: spec.name.length > 12 ? spec.name.slice(0, 11) + '…' : spec.name,
                description: spec.description,
                fullText: spec.full_text,
                source: spec.source,
              };
            }
          }
          if (!cancelled) setStrategies(merged);
        }
      } catch (e) {
        console.warn('Failed to load extracted strategies from backend:', e);
      }
    };

    void init();
    return () => {
      cancelled = true;
    };
  }, []); // Empty dependency array - run only on mount

  // Auto-save configuration when it changes (with debounce)
  useEffect(() => {
    const timer = setTimeout(() => {
      const success = saveConfig({
        datasets,
        llmConfig,
        embeddingConfig,
        apiConfig,
        darkMode,
        selectedStrategy,
        customStrategyText
      });
      if (success) {
        console.log('Configuration auto-saved');
      }
    }, 1000); // Debounce: wait 1 second after last change

    return () => clearTimeout(timer);
  }, [datasets, llmConfig, embeddingConfig, apiConfig, darkMode, selectedStrategy, customStrategyText]);

  // Reset configuration to defaults
  const handleResetConfig = () => {
    setDatasets(DEFAULT_DATASETS);
    setLLMConfig(DEFAULT_LLM_CONFIG);
    setEmbeddingConfig(DEFAULT_EMBEDDING_CONFIG);
    setApiConfig(DEFAULT_API_CONFIG);
    clearConfig();
    console.log('Configuration reset to defaults');
  };

  const parseJsonSafely = async (response) => {
    const text = await response.text();
    if (!text) return { ok: response.ok, data: null, raw: '' };
    try {
      return { ok: response.ok, data: JSON.parse(text), raw: text };
    } catch {
      return { ok: response.ok, data: null, raw: text };
    }
  };

  const buildApiUrl = (path) => {
    const rawBase = apiConfig.api_base_url || '';
    const trimmedBase = rawBase.trim().replace(/\/+$/, '');
    if (!trimmedBase) {
      return path.startsWith('/') ? path : `/${path}`;
    }
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${trimmedBase}${normalizedPath}`;
  };

  const fetchDataSummary = async () => {
    const backendConfig = convertToBackendConfig(
      datasets,
      llmConfig,
      embeddingConfig,
      selectedStrategy,
      strategies,
      customStrategyText
    );

    const response = await fetch(buildApiUrl('/api/data-summary'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config: backendConfig
      })
    });

    const { ok, data, raw } = await parseJsonSafely(response);
    if (!ok) {
      throw new Error((data && data.detail) || raw || 'Failed to load data summary.');
      }
    return data;
    };

  const handleOpenSummary = async () => {
    if (summaryLoading) return;
    setShowDataSummary(true);
    setSummaryError('');
    setSummaryLoading(true);
    setDataSummary(null);
    try {
      const data = await fetchDataSummary();
      setDataSummary(data);
    } catch (err) {
      setSummaryError(`Connection Failed: ${err.message}`);
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input };

    // 先把用户输入渲染出来（乐观更新）
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setFinalText('');
    setStrategyUsed('');
    setOutputComplianceScore(null);

    try {
      let dataSummary = null;
      if (selectedStrategy === 'auto') {
        try {
          dataSummary = await fetchDataSummary();
        } catch (err) {
          setMessages(prev => [
            ...prev,
            { role: 'system', content: `Data summary unavailable, falling back to auto without summary: ${err.message}` }
          ]);
        }
      }

      const backendConfig = convertToBackendConfig(
        datasets,
        llmConfig,
        embeddingConfig,
        selectedStrategy,
        strategies,
        customStrategyText,
        dataSummary,
        userMsg.content
      );

      const response = await fetch(buildApiUrl('/api/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg.content,
          config: backendConfig
        })
      });

      const { ok, data, raw } = await parseJsonSafely(response);

      if (ok) {
        if (data && typeof data.final_text === 'string') {
          setFinalText(data.final_text);
        } else {
          setFinalText('');
        }
        if (selectedStrategy === 'auto' && data && typeof data.strategy_used === 'string') {
          const strategyKey = data.strategy_used;
          const strategyName = strategies[strategyKey]?.name || strategyKey;
          setStrategyUsed(strategyName);
        }
        if (data && typeof data.output_compliance_score === 'number') {
          setOutputComplianceScore(data.output_compliance_score);
        }
        if (data && Array.isArray(data.messages)) {
          setMessages(bundleToolCalls(data.messages));
        }
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'system', content: `Error: ${(data && data.detail) || raw || 'Unknown error'}` }
        ]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'system', content: `Connection Failed: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  // 把 messages 切成两组：主对话 / 调试轨迹
  const { mainMessages, traceMessages } = useMemo(() => splitMessages(messages), [messages]);

  return (
    <div className={`flex h-screen font-sans ${darkMode ? 'bg-slate-950' : 'bg-gray-100'}`}>

      {/* --- 左侧：数据集配置面板（可折叠，默认折叠） --- */}
      <div
        className={`
        flex flex-col border-r
        transition-all duration-300 ease-in-out
        ${showConfig ? 'w-1/3' : 'w-12'}
        ${darkMode ? 'bg-slate-900 text-white border-slate-700' : 'bg-white text-slate-800 border-slate-200'}
      `}
      >

        {/* header */}
        <div className={`border-b relative ${
          darkMode ? 'border-slate-700/50 bg-slate-800' : 'border-slate-200 bg-gray-50'
        }`}>
          {showConfig ? (
            <div className="p-3 flex justify-between items-center">
              <div>
                <h2 className={`font-bold text-base ${darkMode ? 'text-white' : 'text-slate-800'}`}>Configuration</h2>
                <span className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Manage data sources and model</span>
              </div>

              {/* 展开态：正常折叠按钮 */}
              <button
                onClick={() => setShowConfig(v => !v)}
                className={`text-xs px-2.5 py-1.5 rounded-md transition-colors ${
                  darkMode
                    ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                    : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
                }`}
                title="Collapse"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowConfig(true)}
              className={`
                w-full h-14 flex flex-col items-center justify-center gap-0.5
                transition-colors group
                ${darkMode
                  ? 'text-slate-400 hover:text-white hover:bg-slate-800 active:bg-slate-700'
                  : 'text-slate-500 hover:text-slate-800 hover:bg-gray-100 active:bg-gray-200'
                }
              `}
              title="Expand Configuration"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className={`text-[9px] uppercase tracking-wide font-semibold ${
                darkMode ? 'text-slate-500 group-hover:text-slate-400' : 'text-slate-400 group-hover:text-slate-600'
              }`}>Config</span>
            </button>
          )}
        </div>

        {/* body - 使用新的配置面板组件 */}
        {showConfig && (
          <DatasetConfigPanel
            datasets={datasets}
            onDatasetsChange={setDatasets}
            llmConfig={llmConfig}
            onLLMConfigChange={setLLMConfig}
            embeddingConfig={embeddingConfig}
            onEmbeddingConfigChange={setEmbeddingConfig}
            apiConfig={apiConfig}
            onApiConfigChange={setApiConfig}
            darkMode={darkMode}
            onResetConfig={handleResetConfig}
          />
        )}

      </div>

      {/* --- 右侧：聊天窗口 --- */}
      <div className={`${showConfig ? 'w-2/3' : 'flex-1'} flex flex-col transition-all duration-300 ease-in-out ${
        darkMode ? 'bg-slate-900' : 'bg-slate-50'
      }`}>

        {/* 头部 */}
        <ChatHeader
          darkMode={darkMode}
          setDarkMode={setDarkMode}
          loading={loading}
          showTrace={showTrace}
          setShowTrace={setShowTrace}
          traceMessagesLength={traceMessages.length}
          selectedStrategy={selectedStrategy}
          setSelectedStrategy={setSelectedStrategy}
          strategies={strategies}
          customStrategyText={customStrategyText}
          setCustomStrategyText={setCustomStrategyText}
          showStrategyMenu={showStrategyMenu}
          setShowStrategyMenu={setShowStrategyMenu}
          onOpenSummary={handleOpenSummary}
          llmConfig={llmConfig}
          apiBaseUrl={apiConfig.api_base_url || ''}
          onStrategiesUpdated={setStrategies}
          onStrategyDeleted={(key) => {
            setStrategies(prev => {
              const next = { ...prev };
              delete next[key];
              return next;
            });
            if (selectedStrategy === key) setSelectedStrategy('auto');
          }}
        />

        {/* 消息列表 */}
        <ChatMessages
          mainMessages={mainMessages}
          traceMessages={traceMessages}
          showTrace={showTrace}
          finalText={finalText}
          strategyUsed={strategyUsed}
          outputComplianceScore={outputComplianceScore}
          loading={loading}
          darkMode={darkMode}
          bottomRef={bottomRef}
          apiBaseUrl={apiConfig.api_base_url || ''}
        />

        {/* 输入框 */}
        <div className={`px-6 py-4 border-t ${
          darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
        }`}>
          <div className="flex gap-3">
            <textarea
              ref={textareaRef}
              rows="1"
              className={`flex-1 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all resize-none overflow-y-auto ${
                darkMode
                  ? 'bg-slate-900 border border-slate-700 text-white placeholder-slate-500'
                  : 'border border-slate-300 text-slate-900'
              }`}
              style={{ maxHeight: '150px', minHeight: '48px' }}
              placeholder="Ask me anything about your data..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              onInput={(e) => {
                // Auto-resize textarea
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
              }}
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-all font-medium text-sm shadow-sm hover:shadow-md self-end"
            >
              Send
            </button>
          </div>
          <div className={`mt-2 text-xs text-center ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>
            Press Enter to send • Shift + Enter for new line
          </div>
        </div>
      </div>
      <DataSummaryModal
        open={showDataSummary}
        onClose={() => setShowDataSummary(false)}
        loading={summaryLoading}
        error={summaryError}
        summary={dataSummary}
        darkMode={darkMode}
      />
    </div>
  );
}
