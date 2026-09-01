import { useState } from 'react';
import { ROLE_UI } from '../constants';
import { prettyPrint } from '../utils/messageUtils';

export default function MessageBubble({ msg, darkMode }) {
  const ui = ROLE_UI[msg.role] || ROLE_UI.assistant;
  const [open, setOpen] = useState(false);

  const bundles = msg._toolBundles;

  // 根据主题调整样式
  const bubbleStyle = darkMode && msg.role === 'assistant'
    ? 'bg-slate-800 border border-slate-700 text-slate-200'
    : ui.bubble;

  const badgeStyle = darkMode && msg.role === 'assistant'
    ? 'text-slate-400'
    : ui.badgeClass;

  return (
    <div className={`flex ${ui.align} mb-4`}>
      <div className={`max-w-[75%] rounded-2xl overflow-hidden shadow-sm ${bubbleStyle}`}>
        {/* badge */}
        {msg.role !== 'user' && (
          <div className={`text-[9px] font-bold px-4 pt-3 pb-1 tracking-widest uppercase ${badgeStyle}`}>
            {ui.badge}
          </div>
        )}

        {/* content */}
        {msg.content && (
          <div className="px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</div>
        )}

        {/* tool bundles */}
        {Array.isArray(bundles) && bundles.length > 0 && (
          <div className="px-4 pb-3">
            <button
              onClick={() => setOpen(v => !v)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-slate-700 hover:bg-slate-600 text-slate-300'
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
              }`}
            >
              {open ? 'Hide Tool Calls' : `Show Tool Calls (${bundles.length})`}
            </button>

            {open && (
              <div className="mt-3 space-y-3">
                {bundles.map((b, i) => {
                  const fn = b.call.function;
                  const name = fn?.name || b.call.type || "tool_call";
                  const args = fn?.arguments;

                  return (
                    <div key={b.call.id || i} className="space-y-2">
                      {/* call */}
                      <div className={`rounded-lg p-3 font-mono text-xs overflow-x-auto ${
                        darkMode
                          ? 'bg-slate-900 text-emerald-300'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}>
                        <div className={`text-[10px] mb-2 font-semibold ${
                          darkMode ? 'text-slate-400' : 'text-emerald-600'
                        }`}>
                          CALL #{i + 1} · {name}
                        </div>
                        <pre className="whitespace-pre-wrap break-all">{prettyPrint(args)}</pre>
                      </div>

                      {/* result */}
                      {b.result ? (
                        <div className={`rounded-lg p-3 font-mono text-xs overflow-x-auto ${
                          darkMode
                            ? 'bg-slate-800 text-amber-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}>
                          <div className={`text-[10px] mb-2 font-semibold ${
                            darkMode ? 'text-slate-400' : 'text-amber-600'
                          }`}>
                            RESULT · {b.result.name || name}
                          </div>
                          <pre className="whitespace-pre-wrap break-all">{prettyPrint(b.result.content)}</pre>
                        </div>
                      ) : (
                        <div className={`text-[10px] px-2 italic ${
                          darkMode ? 'text-slate-400' : 'text-slate-500'
                        }`}>
                          No matched tool response
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
