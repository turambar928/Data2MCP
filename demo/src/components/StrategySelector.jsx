/**
 * StrategySelector — right-side drawer panel.
 *
 * Layout:
 *   ① Auto
 *   ② Built-in strategies (collapsible group)
 *   ③ Per-source groups  (one group per source file, collapsible)
 *   ④ Custom (pinned at bottom)
 *
 * Each strategy row: select · edit inline · delete
 */
import { useRef, useState } from 'react';

export default function StrategySelector({
  darkMode,
  selectedStrategy,
  setSelectedStrategy,
  strategies,
  customStrategyText,
  setCustomStrategyText,
  showStrategyMenu,
  setShowStrategyMenu,
  loading,
  llmConfig,
  apiBaseUrl,
  onStrategiesUpdated,
  onStrategyDeleted,
}) {
  const [tab, setTab] = useState('list');
  const [editingKey, setEditingKey] = useState(null);
  const [editDraft, setEditDraft] = useState({});
  // which source groups are expanded: { [source]: bool }
  const [expandedGroups, setExpandedGroups] = useState({ '__builtin__': true });

  const [dragOver, setDragOver] = useState(false);
  const [uploadState, setUploadState] = useState('idle');
  const [uploadError, setUploadError] = useState('');
  const [extractedPreviews, setExtractedPreviews] = useState([]);
  const fileInputRef = useRef(null);

  const buildUrl = (path) => {
    const base = (apiBaseUrl || '').trim().replace(/\/+$/, '');
    return base ? `${base}${path}` : path;
  };

  const toggleGroup = (src) =>
    setExpandedGroups(prev => ({ ...prev, [src]: !prev[src] }));

  /* ── edit ── */
  const startEdit = (key, spec) => {
    setEditingKey(key);
    setEditDraft({ name: spec.name || '', description: spec.description || '', fullText: spec.fullText || '' });
  };
  const cancelEdit = () => { setEditingKey(null); setEditDraft({}); };
  const saveEdit = (key) => {
    if (!editDraft.name.trim()) return;
    const updated = {
      ...strategies,
      [key]: {
        ...strategies[key],
        name: editDraft.name,
        shortName: editDraft.name.length > 12 ? editDraft.name.slice(0, 11) + '…' : editDraft.name,
        description: editDraft.description,
        fullText: editDraft.fullText,
      },
    };
    onStrategiesUpdated(updated);
    setEditingKey(null);
    setEditDraft({});
  };

  /* ── delete whole source group ── */
  const handleDeleteSource = async (source, entries) => {
    if (!window.confirm(`删除来自「${source}」的全部 ${entries.length} 个策略？`)) return;
    try {
      const res = await fetch(buildUrl(`/api/strategies-by-source?source=${encodeURIComponent(source)}`), { method: 'DELETE' });
      if (!res.ok && res.status !== 404) {
        const d = await res.json().catch(() => ({}));
        alert(d.detail || '删除失败');
        return;
      }
    } catch { /* best-effort */ }
    const updated = { ...strategies };
    for (const [k] of entries) {
      delete updated[k];
      if (onStrategyDeleted) onStrategyDeleted(k);
    }
    onStrategiesUpdated(updated);
    if (entries.some(([k]) => k === selectedStrategy)) setSelectedStrategy('auto');
  };

  /* ── delete ── */
  const handleDelete = async (key) => {
    if (!window.confirm(`删除策略「${strategies[key]?.name}」？`)) return;
    try {
      const res = await fetch(buildUrl(`/api/strategies/${key}`), { method: 'DELETE' });
      if (!res.ok && res.status !== 404) {
        const d = await res.json().catch(() => ({}));
        alert(d.detail || '删除失败');
        return;
      }
    } catch { /* best-effort */ }
    const updated = { ...strategies };
    delete updated[key];
    onStrategiesUpdated(updated);
    if (onStrategyDeleted) onStrategyDeleted(key);
    if (selectedStrategy === key) setSelectedStrategy('auto');
  };

  /* ── upload / extract ── */
  const handleFile = async (file) => {
    if (!file) return;
    const allowed = ['.pdf', '.txt', '.md', '.rst'];
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    if (!allowed.includes(ext)) {
      setUploadError(`不支持的格式"${ext}"，请上传 ${allowed.join(' / ')}`);
      setUploadState('error');
      return;
    }
    setUploadState('extracting');
    setUploadError('');
    setExtractedPreviews([]);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('config', JSON.stringify({
        _target_: 'data2mcp_v2.config.Data2McpConfig',
        route_type: 'agentic', tool_call_timeout: 300,
        tool_call_max_length: 10000, max_turns: 10, retrieval_strategy: '',
        llm: {
          _target_: 'data2mcp_v2.config.LLMConfig',
          model: 'gpt-4o', temperature: 0, max_tokens: 4096,
          timeout_seconds: 600, max_retries: 3,
          base_url: llmConfig?.base_url || '', api_key: llmConfig?.api_key || '',
        },
        agents: { _target_: 'data2mcp_v2.config.AgentConfig', default_llm_config: null, agent_configs: [] },
      }));
      formData.append('max_pages', '30');
      formData.append('chunk_size', '3000');

      const res = await fetch(buildUrl('/api/upload-and-extract'), { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '提取失败');

      setExtractedPreviews(data.strategies || []);
      setUploadState('done');

      if (onStrategiesUpdated && data.strategies?.length) {
        const updated = { ...strategies };
        for (const spec of data.strategies) {
          if (spec.key && spec.key !== 'custom') {
            updated[spec.key] = {
              name: spec.name,
              shortName: spec.name.length > 12 ? spec.name.slice(0, 11) + '…' : spec.name,
              description: spec.description,
              fullText: spec.full_text,
              source: spec.source || file.name,
            };
          }
        }
        onStrategiesUpdated(updated);
        // auto-expand the new source group
        const newSource = data.strategies[0]?.source || file.name;
        setExpandedGroups(prev => ({ ...prev, [newSource]: true }));
      }
    } catch (e) {
      setUploadError(e.message || '未知错误');
      setUploadState('error');
    }
  };

  const resetUpload = () => { setUploadState('idle'); setUploadError(''); setExtractedPreviews([]); };
  const onDrop = (e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files?.[0]); };
  const onFileChange = (e) => { handleFile(e.target.files?.[0]); e.target.value = ''; };

  /* ── group strategies by source ── */
  const builtinEntries = [];
  const sourceMap = {};   // { [source]: [key, spec][] }

  for (const [key, spec] of Object.entries(strategies)) {
    if (key === 'custom') continue;
    if (!spec.source || spec.source === 'builtin') {
      builtinEntries.push([key, spec]);
    } else {
      if (!sourceMap[spec.source]) sourceMap[spec.source] = [];
      sourceMap[spec.source].push([key, spec]);
    }
  }
  const sourceGroups = Object.entries(sourceMap); // [[source, entries[]]]

  const totalCount = builtinEntries.length + Object.values(sourceMap).reduce((s, a) => s + a.length, 0);

  /* ── styles ── */
  const dm = darkMode;
  const surfaceCls  = dm ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200';
  const textPrimary = dm ? 'text-slate-100' : 'text-slate-800';
  const textMuted   = dm ? 'text-slate-400' : 'text-slate-500';
  const rowBase     = dm ? 'bg-slate-700/40 border-slate-600/60' : 'bg-slate-50 border-slate-200';
  const rowSelected = dm ? 'bg-blue-600/15 border-blue-500' : 'bg-blue-50 border-blue-400';
  const inputCls    = `w-full px-2.5 py-1.5 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none ${
    dm ? 'bg-slate-900 border border-slate-600 text-white placeholder-slate-500'
       : 'bg-white border border-slate-300 text-slate-900 placeholder-slate-400'
  }`;

  /* ── strategy row (shared between builtin & source groups) ── */
  const StrategyRow = ({ entryKey, spec }) => {
    const isSelected = selectedStrategy === entryKey;
    const isEditing  = editingKey === entryKey;

    return (
      <div className={`rounded-lg border transition-all ${isSelected ? rowSelected : rowBase}`}>
        {isEditing ? (
          <div className="p-3 space-y-2">
            <input className={inputCls} value={editDraft.name}
              onChange={e => setEditDraft(d => ({ ...d, name: e.target.value }))} placeholder="名称" />
            <input className={inputCls} value={editDraft.description}
              onChange={e => setEditDraft(d => ({ ...d, description: e.target.value }))} placeholder="简短描述" />
            <textarea className={`${inputCls} h-20`} value={editDraft.fullText}
              onChange={e => setEditDraft(d => ({ ...d, fullText: e.target.value }))}
              placeholder="详细指令（供 Agent 使用）" />
            <div className="flex gap-2 pt-0.5">
              <button onClick={() => saveEdit(entryKey)}
                className="px-3 py-1 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold">保存</button>
              <button onClick={cancelEdit}
                className={`px-3 py-1 rounded-md text-xs font-semibold ${dm ? 'bg-slate-600 hover:bg-slate-500 text-slate-200' : 'bg-slate-200 hover:bg-slate-300 text-slate-700'}`}>取消</button>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-2 px-3 py-2.5">
            <button
              onClick={() => setSelectedStrategy(entryKey)}
              disabled={loading}
              className="flex items-start gap-2 flex-1 min-w-0 text-left"
            >
              <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${isSelected ? 'bg-blue-500' : dm ? 'bg-slate-500' : 'bg-slate-300'}`} />
              <div className="flex-1 min-w-0">
                <span className={`text-xs font-semibold ${isSelected ? (dm ? 'text-blue-300' : 'text-blue-700') : textPrimary}`}>
                  {spec.name}
                </span>
                <div className={`text-[11px] mt-0.5 leading-snug line-clamp-2 ${textMuted}`}>{spec.description}</div>
              </div>
            </button>
            <div className="flex items-center gap-1 flex-shrink-0 ml-1">
              <button onClick={() => startEdit(entryKey, spec)} title="编辑"
                className={`p-1 rounded-md transition-colors ${dm ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-600' : 'text-slate-400 hover:text-slate-700 hover:bg-slate-200'}`}>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button onClick={() => handleDelete(entryKey)} title="删除"
                className={`p-1 rounded-md transition-colors ${dm ? 'text-slate-500 hover:text-red-400 hover:bg-red-900/30' : 'text-slate-400 hover:text-red-600 hover:bg-red-50'}`}>
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  /* ── collapsible group header ── */
  const GroupHeader = ({ groupKey, label, count, badge, onDeleteGroup }) => {
    const expanded = expandedGroups[groupKey];
    return (
      <div className="flex items-center gap-1">
        <button
          onClick={() => toggleGroup(groupKey)}
          className={`flex-1 flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors ${
            dm ? 'hover:bg-slate-700/60' : 'hover:bg-slate-100'
          }`}
        >
          <svg className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${expanded ? 'rotate-90' : ''} ${textMuted}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {badge && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold flex-shrink-0 ${
              dm ? 'bg-emerald-900/60 text-emerald-400' : 'bg-emerald-100 text-emerald-700'
            }`}>{badge}</span>
          )}
          <span className={`text-xs font-semibold flex-1 min-w-0 truncate ${textPrimary}`}>{label}</span>
          <span className={`text-[11px] flex-shrink-0 ${textMuted}`}>{count}</span>
        </button>
        {onDeleteGroup && (
          <button
            onClick={onDeleteGroup}
            title={`删除来自「${label}」的全部策略`}
            className={`p-1 rounded-md flex-shrink-0 transition-colors ${
              dm ? 'text-slate-500 hover:text-red-400 hover:bg-red-900/30' : 'text-slate-400 hover:text-red-600 hover:bg-red-50'
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="relative">
      {/* trigger */}
      <button
        onClick={() => setShowStrategyMenu(v => !v)}
        className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-all flex items-center gap-2 ${
          dm ? 'bg-slate-700 hover:bg-slate-600 text-slate-200' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
        }`}
        title={strategies[selectedStrategy]?.fullText || ''}
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
        <span className="font-semibold">{strategies[selectedStrategy]?.shortName || 'Strategy'}</span>
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {showStrategyMenu && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setShowStrategyMenu(false)} />

          <div className={`absolute right-0 mt-2 w-[500px] max-h-[82vh] rounded-xl shadow-2xl z-20 flex flex-col overflow-hidden border ${surfaceCls}`}>

            {/* header + tabs */}
            <div className={`px-4 pt-3 pb-0 border-b flex-shrink-0 ${dm ? 'bg-slate-700/50 border-slate-600' : 'bg-slate-50 border-slate-200'}`}>
              <div className={`text-sm font-bold mb-2 ${textPrimary}`}>
                分析方法管理
                <span className={`ml-2 text-xs font-normal ${textMuted}`}>共 {totalCount} 个方法</span>
              </div>
              <div className="flex gap-1">
                {[
                  { id: 'list',   label: '策略列表' },
                  { id: 'upload', label: '+ 从文件提取' },
                ].map(t => (
                  <button key={t.id}
                    onClick={() => { setTab(t.id); if (t.id === 'upload') resetUpload(); }}
                    className={`px-3 py-1.5 text-xs font-medium rounded-t-md transition-colors border-b-2 ${
                      tab === t.id
                        ? dm ? 'text-blue-400 border-blue-400 bg-slate-800' : 'text-blue-600 border-blue-600 bg-white'
                        : dm ? 'text-slate-400 border-transparent hover:text-slate-200' : 'text-slate-500 border-transparent hover:text-slate-700'
                    }`}
                  >{t.label}</button>
                ))}
              </div>
            </div>

            {/* ── TAB: list ── */}
            {tab === 'list' && (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">

                  {/* ① Auto */}
                  <button
                    onClick={() => setSelectedStrategy('auto')}
                    disabled={loading}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-all ${
                      selectedStrategy === 'auto' ? rowSelected : rowBase
                    } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-400/50'}`}
                  >
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                      selectedStrategy === 'auto' ? 'bg-blue-500 text-white' : dm ? 'bg-slate-600 text-slate-300' : 'bg-slate-200 text-slate-500'
                    }`}>A</div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-xs font-semibold ${selectedStrategy === 'auto' ? (dm ? 'text-blue-300' : 'text-blue-700') : textPrimary}`}>
                        自动选择
                      </div>
                      <div className={`text-[11px] truncate ${textMuted}`}>由模型根据问题自动选择最合适的分析方法</div>
                    </div>
                    {selectedStrategy === 'auto' && (
                      <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>

                  {/* ② Built-in group */}
                  {builtinEntries.length > 0 && (
                    <div>
                      <GroupHeader groupKey="__builtin__" label="内置方法" count={builtinEntries.length} />
                      {expandedGroups['__builtin__'] && (
                        <div className="ml-4 mt-1 space-y-1.5">
                          {builtinEntries.map(([k, s]) => <StrategyRow key={k} entryKey={k} spec={s} />)}
                        </div>
                      )}
                    </div>
                  )}

                  {/* ③ Per-source groups */}
                  {sourceGroups.map(([source, entries]) => (
                    <div key={source}>
                      <GroupHeader
                        groupKey={source}
                        label={source}
                        count={entries.length}
                        badge="提取"
                        onDeleteGroup={() => handleDeleteSource(source, entries)}
                      />
                      {expandedGroups[source] && (
                        <div className="ml-4 mt-1 space-y-1.5">
                          {entries.map(([k, s]) => <StrategyRow key={k} entryKey={k} spec={s} />)}
                        </div>
                      )}
                    </div>
                  ))}

                  {totalCount === 0 && (
                    <div className={`text-center py-8 text-xs ${textMuted}`}>
                      暂无方法，请切换到「从文件提取」导入
                    </div>
                  )}
                </div>

                {/* ④ Custom — pinned bottom */}
                <div className={`flex-shrink-0 border-t px-3 py-3 ${dm ? 'border-slate-700 bg-slate-800/60' : 'border-slate-200 bg-slate-50/80'}`}>
                  <button
                    onClick={() => setSelectedStrategy('custom')}
                    disabled={loading}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg border transition-all text-left ${
                      selectedStrategy === 'custom' ? rowSelected : rowBase
                    } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-blue-400/50'}`}
                  >
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                      selectedStrategy === 'custom' ? 'bg-blue-500 text-white' : dm ? 'bg-slate-600 text-slate-300' : 'bg-slate-200 text-slate-500'
                    }`}>C</div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-xs font-semibold ${selectedStrategy === 'custom' ? (dm ? 'text-blue-300' : 'text-blue-700') : textPrimary}`}>
                        {strategies.custom?.name || '自定义策略'}
                      </div>
                      <div className={`text-[11px] truncate ${textMuted}`}>{strategies.custom?.description}</div>
                    </div>
                    {selectedStrategy === 'custom' && (
                      <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>

                  {selectedStrategy === 'custom' && (
                    <div className="mt-2">
                      <textarea
                        value={customStrategyText}
                        onChange={e => setCustomStrategyText(e.target.value)}
                        className={`w-full h-24 px-3 py-2 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none ${
                          dm ? 'bg-slate-900 border border-slate-600 text-white placeholder-slate-500'
                             : 'bg-white border border-slate-300 text-slate-900 placeholder-slate-400'
                        }`}
                        placeholder="输入自定义分析策略指令，例如：先查询交易表中的异常记录，再与用户画像交叉比对..."
                      />
                      <button
                        onClick={() => setShowStrategyMenu(false)}
                        className="mt-1.5 w-full px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors"
                      >应用自定义策略</button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── TAB: upload ── */}
            {tab === 'upload' && (
              <div className="p-4 overflow-y-auto flex-1">
                <p className={`text-xs mb-3 ${textMuted}`}>
                  上传 PDF、TXT 或 Markdown 文件，系统将自动识别并提取其中的结构化分析方法，按来源归类后添加到策略列表。
                </p>

                {(uploadState === 'idle' || uploadState === 'error') && (
                  <>
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                      onDragLeave={() => setDragOver(false)}
                      onDrop={onDrop}
                      className={`flex flex-col items-center justify-center gap-2 h-36 rounded-xl border-2 border-dashed cursor-pointer transition-colors ${
                        dragOver
                          ? dm ? 'border-blue-400 bg-blue-900/20' : 'border-blue-500 bg-blue-50'
                          : dm ? 'border-slate-600 hover:border-slate-500 bg-slate-700/20' : 'border-slate-300 hover:border-slate-400 bg-slate-50'
                      }`}
                    >
                      <svg className={`w-8 h-8 ${textMuted}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <div className={`text-sm font-medium ${dm ? 'text-slate-300' : 'text-slate-600'}`}>点击或拖拽文件到此处</div>
                      <div className={`text-xs ${textMuted}`}>支持 PDF（含扫描件）、TXT、MD · 最多 30 页</div>
                    </div>
                    <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md,.rst" className="hidden" onChange={onFileChange} />
                    {uploadState === 'error' && (
                      <div className={`mt-2 px-3 py-2 rounded-lg text-xs ${dm ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'}`}>
                        {uploadError}
                      </div>
                    )}
                  </>
                )}

                {uploadState === 'extracting' && (
                  <div className={`flex flex-col items-center justify-center gap-3 h-36 rounded-xl border ${dm ? 'border-slate-700 bg-slate-700/20' : 'border-slate-200 bg-slate-50'}`}>
                    <svg className="w-7 h-7 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <div className={`text-sm font-medium ${dm ? 'text-slate-300' : 'text-slate-600'}`}>正在提取分析方法...</div>
                    <div className={`text-xs ${textMuted}`}>大文件可能需要较长时间，请耐心等待</div>
                  </div>
                )}

                {uploadState === 'done' && (
                  <div>
                    <div className={`flex items-center gap-2 mb-3 text-sm font-medium ${dm ? 'text-emerald-400' : 'text-emerald-600'}`}>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      成功提取 {extractedPreviews.length} 个分析方法
                    </div>
                    <div className="flex flex-col gap-1.5 max-h-52 overflow-y-auto">
                      {extractedPreviews.map((s, i) => (
                        <div key={s.key || i} className={`px-3 py-2 rounded-lg border ${dm ? 'bg-slate-700/30 border-slate-600' : 'bg-slate-50 border-slate-200'}`}>
                          <div className={`font-semibold text-xs mb-0.5 ${dm ? 'text-slate-200' : 'text-slate-700'}`}>{s.name}</div>
                          <div className={`text-[11px] ${textMuted}`}>{s.description}</div>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2 mt-3">
                      <button onClick={() => setTab('list')}
                        className="flex-1 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors">
                        查看策略列表
                      </button>
                      <button onClick={resetUpload}
                        className={`px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${dm ? 'bg-slate-700 hover:bg-slate-600 text-slate-300' : 'bg-slate-100 hover:bg-slate-200 text-slate-600'}`}>
                        继续上传
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        </>
      )}
    </div>
  );
}
