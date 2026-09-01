/**
 * StrategyValidationBadge - 显示策略选择和验证信息
 */

export default function StrategyValidationBadge({ validationReport, strategyUsed, darkMode }) {
  if (!validationReport && !strategyUsed) return null;

  const { compliance_score, strategy_name, violations = [], compliance_details = [] } = validationReport || {};

  // 根据合规分数选择颜色和图标
  const getScoreColor = (score) => {
    if (score >= 0.7) return 'bg-green-500/10 text-green-400 border-green-500/30';
    if (score >= 0.5) return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    return 'bg-red-500/10 text-red-400 border-red-500/30';
  };

  const getScoreIcon = (score) => {
    if (score >= 0.7) return '✅';
    if (score >= 0.5) return '⚠️';
    return '❌';
  };

  return (
    <div className={`px-4 py-3 border-b ${
      darkMode ? 'bg-slate-800/50 border-slate-700' : 'bg-slate-50 border-slate-200'
    }`}>
      <div className="flex items-center justify-between">
        {/* 左侧：策略信息 */}
        <div className="flex items-center gap-3">
          <div className={`px-2.5 py-1 rounded-md text-xs font-semibold ${
            darkMode ? 'bg-blue-500/20 text-blue-300' : 'bg-blue-50 text-blue-700'
          }`}>
            {strategy_name || strategyUsed || 'No Strategy'}
          </div>

          {compliance_score !== undefined && (
            <div className={`px-2.5 py-1 rounded-md text-xs font-semibold border ${getScoreColor(compliance_score)}`}>
              {getScoreIcon(compliance_score)} {(compliance_score * 100).toFixed(0)}% Compliance
            </div>
          )}
        </div>

        {/* 右侧：详情按钮 */}
        {validationReport && (
          <button
            onClick={() => {
              // 点击显示详细报告
              const details = [
                `Strategy: ${strategy_name}`,
                `Compliance: ${(compliance_score * 100).toFixed(1)}%`,
                `\nExecution Pattern:`,
                `  • Total calls: ${validationReport.total_tool_calls}`,
                `  • Parallel: ${validationReport.parallel_calls}`,
                `  • Sequential: ${validationReport.sequential_calls}`,
                `  • Distinct tools: ${validationReport.distinct_tools}`,
                `  • Pattern: ${validationReport.tool_call_pattern}`,
                `\nCompliance Checks:`,
                ...compliance_details.map(d => `  ${d}`),
                ...(violations.length > 0 ? ['\nViolations:', ...violations.map(v => `  ${v}`)] : [])
              ].join('\n');
              alert(details);
            }}
            className={`text-xs px-2 py-1 rounded hover:bg-opacity-80 transition-colors ${
              darkMode ? 'text-slate-400 hover:text-slate-300' : 'text-slate-600 hover:text-slate-700'
            }`}
            title="View detailed validation report"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        )}
      </div>

      {/* 违规提示 */}
      {violations && violations.length > 0 && (
        <div className={`mt-2 text-xs ${
          darkMode ? 'text-amber-400' : 'text-amber-600'
        }`}>
          <span className="font-semibold">⚠️ Strategy may not be fully followed:</span>
          <ul className="ml-4 mt-1 space-y-0.5">
            {violations.slice(0, 2).map((v, idx) => (
              <li key={idx}>• {v.replace(/^(?:❌|⚠|✅)\uFE0F?\s*/u, '')}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
