import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import MessageBubble from './MessageBubble';

// 自定义图片渲染：将 /charts/xxx.png 替换为完整的后端 URL
function makeComponents(apiBaseUrl) {
  return {
    img({ src, alt }) {
      const resolvedSrc = src && src.startsWith('/charts/')
        ? `${apiBaseUrl}${src}`
        : src;
      return (
        <img
          src={resolvedSrc}
          alt={alt}
          style={{ maxWidth: '100%', borderRadius: '8px', margin: '8px 0' }}
        />
      );
    },
    // 段落保留正常间距
    p({ children }) {
      return <p style={{ margin: '4px 0' }}>{children}</p>;
    },
  };
}

export default function ChatMessages({
  mainMessages,
  traceMessages,
  showTrace,
  finalText,
  strategyUsed,
  outputComplianceScore,
  loading,
  darkMode,
  bottomRef,
  apiBaseUrl = '',
}) {
  const strategyLabel = strategyUsed ? strategyUsed : '';
  const mdComponents = makeComponents(apiBaseUrl);

  // compliance badge helpers
  const hasScore = outputComplianceScore !== null && outputComplianceScore !== undefined;
  const scorePct = hasScore ? Math.round(outputComplianceScore * 100) : null;
  const scoreColor = hasScore
    ? outputComplianceScore >= 0.7
      ? darkMode ? 'bg-emerald-900/50 text-emerald-400 border-emerald-700' : 'bg-emerald-50 text-emerald-700 border-emerald-300'
      : outputComplianceScore >= 0.4
        ? darkMode ? 'bg-amber-900/50 text-amber-400 border-amber-700' : 'bg-amber-50 text-amber-700 border-amber-300'
        : darkMode ? 'bg-red-900/50 text-red-400 border-red-700' : 'bg-red-50 text-red-700 border-red-300'
    : '';
  const scoreIcon = hasScore
    ? outputComplianceScore >= 0.7 ? '✅' : outputComplianceScore >= 0.4 ? '⚠️' : '❌'
    : '';

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      {/* 主对话 */}
      {mainMessages.map((msg, idx) => (
        <MessageBubble key={`main-${idx}`} msg={msg} darkMode={darkMode} />
      ))}

      {finalText && (
        <div className="mb-6">
          <div className={`text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-2 ${
            darkMode ? 'text-slate-400' : 'text-slate-500'
          }`}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Final Answer
            {strategyLabel && (
              <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                darkMode
                  ? 'bg-slate-700 text-slate-200 border border-slate-600'
                  : 'bg-slate-200 text-slate-700 border border-slate-300'
              }`}>
                Strategy: {strategyLabel}
              </span>
            )}
            {hasScore && (
              <span className={`ml-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${scoreColor}`}
                title="产出合规分数：评估最终答案是否符合所选策略的预期产出特征">
                {scoreIcon} 合规 {scorePct}%
              </span>
            )}
          </div>
          <div className={`rounded-2xl p-5 shadow-sm ${
            darkMode
              ? 'bg-slate-800 border border-slate-700'
              : 'bg-white border border-slate-200'
          }`}>
            <div className={`text-sm leading-relaxed ${
              darkMode ? 'text-slate-200' : 'text-slate-800'
            }`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {finalText}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* 调试轨迹（system/tool） */}
      {showTrace && traceMessages.length > 0 && (
        <div className={`mt-6 pt-6 ${darkMode ? 'border-slate-700' : 'border-slate-200'} border-t`}>
          <div className={`text-xs font-semibold uppercase tracking-wider mb-3 ${
            darkMode ? 'text-slate-400' : 'text-slate-500'
          }`}>
            Debug Trace
          </div>
          {traceMessages.map((msg, idx) => (
            <MessageBubble key={`trace-${idx}`} msg={msg} darkMode={darkMode} />
          ))}
        </div>
      )}

      {/* loading 气泡 */}
      {loading && (
        <div className="flex justify-start mb-4">
          <div className={`rounded-2xl px-5 py-4 shadow-sm flex items-center gap-3 ${
            darkMode
              ? 'bg-slate-800 border border-slate-700'
              : 'bg-white border border-slate-200'
          }`}>
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
              <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
            </div>
            <span className={`text-sm ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Thinking...</span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
