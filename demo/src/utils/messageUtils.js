/**
 * Bundle tool calls with their results for display
 * Filters out standalone tool messages and attaches them to their corresponding assistant messages
 */
export function bundleToolCalls(messages) {
  if (!Array.isArray(messages)) return [];

  // 1) 收集所有 tool 返回：tool_call_id -> tool message
  const toolResultMap = new Map();
  for (const m of messages) {
    if (m.role === "tool" && m.tool_call_id) {
      toolResultMap.set(m.tool_call_id, m);
    }
  }

  // 2) 把 tool_calls 和返回绑定到 assistant 上
  return messages
    .filter(m => m.role !== "tool")
    .map(m => {
      if (m.role === "assistant" && Array.isArray(m.tool_calls)) {
        const bundles = m.tool_calls.map(tc => {
          const id = tc.id || tc.tool_call_id;
          return {
            call: tc,
            result: id ? toolResultMap.get(id) || null : null
          };
        });
        return { ...m, _toolBundles: bundles };
      }
      return m;
    });
}

/**
 * Pretty print JSON or string content
 */
export function prettyPrint(v) {
  if (v == null) return '';
  if (typeof v === "string") {
    try { return JSON.stringify(JSON.parse(v), null, 2); }
    catch { return v; }
  }
  try { return JSON.stringify(v, null, 2); }
  catch { return String(v); }
}

/**
 * Split messages into main conversation and debug trace
 */
export function splitMessages(messages) {
  const main = [];
  const trace = [];
  for (const m of messages) {
    if (m.role === 'system') trace.push(m);
    else main.push(m);
  }
  return { mainMessages: main, traceMessages: trace };
}
