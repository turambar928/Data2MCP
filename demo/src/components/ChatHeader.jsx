import StrategySelector from './StrategySelector';

export default function ChatHeader({
  darkMode,
  setDarkMode,
  loading,
  showTrace,
  setShowTrace,
  traceMessagesLength,
  // Strategy props
  selectedStrategy,
  setSelectedStrategy,
  strategies,
  customStrategyText,
  setCustomStrategyText,
  showStrategyMenu,
  setShowStrategyMenu,
  onOpenSummary,
  // Upload props
  llmConfig,
  apiBaseUrl,
  onStrategiesUpdated,
  onStrategyDeleted,
}) {
  return (
    <div className={`px-6 py-4 border-b shadow-sm flex justify-between items-center ${
      darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
    }`}>
      <div>
        <h1 className={`text-lg font-semibold ${darkMode ? 'text-white' : 'text-slate-800'}`}>
          Data2MCP<span className="text-blue-500">v2</span>
        </h1>
        <p className={`text-xs mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
          Powered by Multi-Agent System
        </p>
      </div>

      <div className="flex items-center gap-4">
        {/* 数据摘要按钮 */}
        <button
          onClick={onOpenSummary}
          className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-all flex items-center gap-2 ${
            darkMode
              ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
          }`}
          title="Data Source Summary"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M12 21a9 9 0 110-18 9 9 0 010 18z" />
          </svg>
          <span className="font-semibold">Data Info</span>
        </button>

        {/* Strategy 选择器 (Retrieval Strategy) */}
        <StrategySelector
          darkMode={darkMode}
          selectedStrategy={selectedStrategy}
          setSelectedStrategy={setSelectedStrategy}
          strategies={strategies}
          customStrategyText={customStrategyText}
          setCustomStrategyText={setCustomStrategyText}
          showStrategyMenu={showStrategyMenu}
          setShowStrategyMenu={setShowStrategyMenu}
          loading={loading}
          llmConfig={llmConfig}
          apiBaseUrl={apiBaseUrl}
          onStrategiesUpdated={onStrategiesUpdated}
          onStrategyDeleted={onStrategyDeleted}
        />

        {/* 主题切换按钮 */}
        <button
          onClick={() => setDarkMode(v => !v)}
          className={`p-2 rounded-lg transition-colors ${
            darkMode
              ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
          }`}
          title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {darkMode ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>

        {/* trace toggle */}
        {traceMessagesLength > 0 && (
          <button
            onClick={() => setShowTrace(v => !v)}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
              darkMode
                ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            {showTrace ? 'Hide Trace' : `Debug Trace (${traceMessagesLength})`}
          </button>
        )}

        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${loading ? 'bg-amber-400 animate-pulse' : 'bg-emerald-500'}`}></div>
          <span className={`text-xs font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
            {loading ? 'Processing' : 'Ready'}
          </span>
        </div>
      </div>
    </div>
  );
}
