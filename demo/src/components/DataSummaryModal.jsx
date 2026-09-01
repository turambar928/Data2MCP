export default function DataSummaryModal({
  open,
  onClose,
  loading,
  error,
  summary,
  darkMode
}) {
  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-30 bg-black/40"
        onClick={onClose}
      />
      <div className={`fixed inset-0 z-40 flex items-center justify-center p-6`}>
        <div className={`w-full max-w-4xl max-h-[80vh] rounded-xl shadow-xl overflow-hidden ${
          darkMode ? 'bg-slate-900 text-slate-200 border border-slate-700' : 'bg-white text-slate-800 border border-slate-200'
        }`}>
          <div className={`px-4 py-3 border-b flex items-center justify-between ${
            darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-200'
          }`}>
            <div>
              <div className="text-sm font-semibold">Data Source Summary</div>
              <div className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                {summary?.generated_at ? `Generated at ${summary.generated_at}` : 'Generated on demand'}
              </div>
            </div>
            <button
              onClick={onClose}
              className={`text-xs px-2.5 py-1.5 rounded-md transition-colors ${
                darkMode ? 'bg-slate-700 hover:bg-slate-600 text-slate-200' : 'bg-slate-200 hover:bg-slate-300 text-slate-700'
              }`}
            >
              Close
            </button>
          </div>

          <div className="p-4 overflow-y-auto max-h-[70vh]">
            {loading && (
              <div className={`text-sm ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>Loading summary...</div>
            )}
            {error && (
              <div className="text-sm text-red-500">{error}</div>
            )}
            {!loading && !error && summary?.sources?.length === 0 && (
              <div className={`text-sm ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>No data sources configured.</div>
            )}
            {!loading && !error && summary?.sources?.length > 0 && (
              <div className="space-y-3">
                {summary.sources.map((source, idx) => (
                  <div
                    key={`${source.name}-${idx}`}
                    className={`rounded-lg border p-3 ${
                      darkMode ? 'border-slate-700 bg-slate-800/40' : 'border-slate-200 bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-semibold text-sm">{source.name || `Source ${idx + 1}`}</div>
                      <div className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                        {source.agent_type || 'unknown'}
                      </div>
                    </div>
                    {source.description && (
                      <div className={`text-xs mb-2 ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                        {source.description}
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {source.data_type && <div><span className="font-semibold">Data Type:</span> {source.data_type}</div>}
                      {source.path && <div className="truncate"><span className="font-semibold">Path:</span> {source.path}</div>}
                      {source.size_human && <div><span className="font-semibold">Size:</span> {source.size_human}</div>}
                      {source.row_count !== undefined && source.row_count !== null && (
                        <div><span className="font-semibold">Rows:</span> {source.row_count}</div>
                      )}
                      {source.columns && (
                        <div className="col-span-2">
                          <span className="font-semibold">Columns:</span> {source.columns.join(', ')}
                        </div>
                      )}
                      {source.file_count !== undefined && (
                        <div><span className="font-semibold">Files:</span> {source.file_count}</div>
                      )}
                      {source.total_size_human && (
                        <div><span className="font-semibold">Total Size:</span> {source.total_size_human}</div>
                      )}
                      {source.db_type && (
                        <div><span className="font-semibold">DB Type:</span> {source.db_type}</div>
                      )}
                      {source.db_name && (
                        <div className="truncate"><span className="font-semibold">DB Name:</span> {source.db_name}</div>
                      )}
                      {source.host && (
                        <div className="truncate"><span className="font-semibold">Host:</span> {source.host}</div>
                      )}
                      {source.port && (
                        <div><span className="font-semibold">Port:</span> {source.port}</div>
                      )}
                    </div>
                    {source.sample_rows && (
                      <div className="mt-2 text-xs">
                        <div className={`font-semibold mb-1 ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>Sample Rows:</div>
                        <pre className={`text-[11px] rounded-md p-2 overflow-x-auto ${
                          darkMode ? 'bg-slate-900 border border-slate-700 text-slate-300' : 'bg-white border border-slate-200 text-slate-700'
                        }`}>
                          {JSON.stringify(source.sample_rows, null, 2)}
                        </pre>
                      </div>
                    )}
                    {source.sample_text && (
                      <div className="mt-2 text-xs">
                        <div className={`font-semibold mb-1 ${darkMode ? 'text-slate-300' : 'text-slate-600'}`}>Sample Text:</div>
                        <pre className={`text-[11px] rounded-md p-2 overflow-x-auto whitespace-pre-wrap ${
                          darkMode ? 'bg-slate-900 border border-slate-700 text-slate-300' : 'bg-white border border-slate-200 text-slate-700'
                        }`}>
                          {source.sample_text}
                        </pre>
                      </div>
                    )}
                    {source.error && (
                      <div className="mt-2 text-xs text-red-500">Error: {source.error}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

