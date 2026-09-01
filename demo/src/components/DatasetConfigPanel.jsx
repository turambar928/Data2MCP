import { useState } from 'react';
import { TYPE_COLORS } from '../constants';
import { getFieldSchema, shouldDisplayField } from '../utils/configUtils';

export default function DatasetConfigPanel({ datasets, onDatasetsChange, llmConfig, onLLMConfigChange, embeddingConfig, onEmbeddingConfigChange, apiConfig, onApiConfigChange, darkMode = false, onResetConfig }) {
  const [expandedDatasets, setExpandedDatasets] = useState({});
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [showEmbeddingAdvanced, setShowEmbeddingAdvanced] = useState(false);

  // Check if any document-based data sources are present (requires embeddings)
  const documentTypes = ['md', 'txt', 'pdf', 'html', 'doc', 'docx'];
  const hasDocumentDataSources = datasets.some(d => documentTypes.includes(d.type) && d.enabled);

  const handleDatasetToggle = (index) => {
    const newDatasets = [...datasets];
    newDatasets[index].enabled = !newDatasets[index].enabled;
    onDatasetsChange(newDatasets);
  };

  const handleDatasetEdit = (index, field, value) => {
    const newDatasets = [...datasets];
    newDatasets[index][field] = value;
    onDatasetsChange(newDatasets);
  };

  const handleRemoveDataset = (index) => {
    const newDatasets = datasets.filter((_, i) => i !== index);
    onDatasetsChange(newDatasets);
  };

  const toggleExpanded = (index) => {
    setExpandedDatasets(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const addDataSource = (type) => {
    const newDataset = {
      name: `new_${type}_source`,
      type,
      description: 'New data source - click to edit',
      enabled: true,
      ...(type === 'sql' && { db_type: 'sqlite' }),
    };

    onDatasetsChange([...datasets, newDataset]);
    setShowAddMenu(false);

    // Auto-expand the newly added dataset
    setTimeout(() => {
      setExpandedDatasets(prev => ({
        ...prev,
        [datasets.length]: true
      }));
    }, 100);
  };

  const renderField = (field, dataset, index) => {
    if (!shouldDisplayField(field, dataset)) return null;

    const value = field.group
      ? (dataset[field.group]?.[field.key] ?? field.default ?? '')
      : (dataset[field.key] ?? field.default ?? '');

    const handleChange = (newValue) => {
      if (field.group) {
        const groupData = dataset[field.group] || {};
        handleDatasetEdit(index, field.group, {
          ...groupData,
          [field.key]: newValue,
        });
      } else {
        handleDatasetEdit(index, field.key, newValue);
      }
    };

    switch (field.type) {
      case 'text':
      case 'password':
        return (
          <div key={field.key}>
            <label className={`block text-[10px] mb-1 font-medium uppercase tracking-wide ${
              darkMode ? 'text-slate-500' : 'text-slate-600'
            }`}>
              {field.label}
            </label>
            <input
              type={field.type}
              value={value}
              onChange={(e) => handleChange(e.target.value)}
              placeholder={field.placeholder}
              className={`w-full text-xs px-2.5 py-1.5 rounded border focus:border-blue-500/50 focus:outline-none font-mono transition-colors ${
                darkMode
                  ? 'bg-slate-900/50 text-slate-300 border-slate-700/50'
                  : 'bg-white text-slate-700 border-slate-300'
              }`}
            />
          </div>
        );

      case 'number':
        return (
          <div key={field.key}>
            <label className={`block text-[10px] mb-1 font-medium uppercase tracking-wide ${
              darkMode ? 'text-slate-500' : 'text-slate-600'
            }`}>
              {field.label}
            </label>
            <input
              type="number"
              value={value}
              onChange={(e) => handleChange(parseFloat(e.target.value))}
              min={field.min}
              max={field.max}
              step={field.step || 1}
              className={`w-full text-xs px-2.5 py-1.5 rounded border focus:border-blue-500/50 focus:outline-none transition-colors ${
                darkMode
                  ? 'bg-slate-900/50 text-slate-300 border-slate-700/50'
                  : 'bg-white text-slate-700 border-slate-300'
              }`}
            />
          </div>
        );

      case 'boolean':
        return (
          <div key={field.key} className="flex items-center justify-between py-1">
            <label className={`text-[10px] font-medium uppercase tracking-wide ${
              darkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>
              {field.label}
            </label>
            <button
              onClick={() => handleChange(!value)}
              className={`w-9 h-5 rounded-full transition-all relative flex-shrink-0 ${
                value ? 'bg-blue-500' : (darkMode ? 'bg-slate-700' : 'bg-slate-300')
              }`}
            >
              <div
                className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm ${
                  value ? 'right-0.5' : 'left-0.5'
                }`}
              ></div>
            </button>
          </div>
        );

      case 'select':
        return (
          <div key={field.key}>
            <label className={`block text-[10px] mb-1 font-medium uppercase tracking-wide ${
              darkMode ? 'text-slate-500' : 'text-slate-600'
            }`}>
              {field.label}
            </label>
            <select
              value={value}
              onChange={(e) => handleChange(e.target.value)}
              className={`w-full text-xs px-2.5 py-1.5 rounded border focus:border-blue-500/50 focus:outline-none transition-colors ${
                darkMode
                  ? 'bg-slate-900/50 text-slate-300 border-slate-700/50'
                  : 'bg-white text-slate-700 border-slate-300'
              }`}
            >
              {field.options.map(option => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`flex-1 overflow-y-auto ${darkMode ? 'bg-slate-900' : 'bg-gray-50'}`}>
      {/* LLM 配置 */}
      <div className={`p-4 border-b ${darkMode ? 'border-slate-700/50' : 'border-slate-200'}`}>
        <h3 className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          darkMode ? 'text-slate-400' : 'text-slate-600'
        }`}>Model Configuration</h3>
        <div className="space-y-3">
          <div>
            <label className={`block text-xs mb-1.5 font-medium ${
              darkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>Model Name</label>
            <input
              type="text"
              value={llmConfig.model}
              onChange={(e) => onLLMConfigChange({ ...llmConfig, model: e.target.value })}
              className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                darkMode
                  ? 'bg-slate-800/50 text-white border-slate-700'
                  : 'bg-white text-slate-800 border-slate-300'
              }`}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={`block text-xs mb-1.5 font-medium ${
                darkMode ? 'text-slate-400' : 'text-slate-600'
              }`}>Max Tokens</label>
              <input
                type="number"
                value={llmConfig.max_tokens}
                onChange={(e) => onLLMConfigChange({ ...llmConfig, max_tokens: parseInt(e.target.value) })}
                className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                  darkMode
                    ? 'bg-slate-800/50 text-white border-slate-700'
                    : 'bg-white text-slate-800 border-slate-300'
                }`}
              />
            </div>
            <div>
              <label className={`block text-xs mb-1.5 font-medium ${
                darkMode ? 'text-slate-400' : 'text-slate-600'
              }`}>Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                value={llmConfig.temperature}
                onChange={(e) => onLLMConfigChange({ ...llmConfig, temperature: parseFloat(e.target.value) })}
                className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                  darkMode
                    ? 'bg-slate-800/50 text-white border-slate-700'
                    : 'bg-white text-slate-800 border-slate-300'
                }`}
              />
            </div>
          </div>
          <div>
            <label className={`block text-xs mb-1.5 font-medium ${
              darkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>Base URL</label>
            <input
              type="text"
              value={llmConfig.base_url}
              onChange={(e) => onLLMConfigChange({ ...llmConfig, base_url: e.target.value })}
              className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                darkMode
                  ? 'bg-slate-800/50 text-white border-slate-700'
                  : 'bg-white text-slate-800 border-slate-300'
              }`}
              placeholder="https://api.example.com/v1"
            />
          </div>
          <div>
            <label className={`block text-xs mb-1.5 font-medium ${
              darkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>API Key</label>
            <input
              type="password"
              value={llmConfig.api_key}
              onChange={(e) => onLLMConfigChange({ ...llmConfig, api_key: e.target.value })}
              className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all font-mono ${
                darkMode
                  ? 'bg-slate-800/50 text-white border-slate-700'
                  : 'bg-white text-slate-800 border-slate-300'
              }`}
              placeholder="sk-..."
            />
          </div>
        </div>
      </div>

      {/* Embedding Model Configuration - Only show when document data sources exist */}
      {hasDocumentDataSources && (
        <div className={`p-4 border-b ${darkMode ? 'border-slate-700/50' : 'border-slate-200'}`}>
          <div className="mb-3">
            <h3 className={`text-xs font-semibold uppercase tracking-wider ${
              darkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>Embedding Model</h3>
            <p className={`text-[10px] mt-0.5 ${
              darkMode ? 'text-slate-500' : 'text-slate-500'
            }`}>Required for document-based vector search</p>
          </div>

          <div className="space-y-3">
            {/* Embedding Model Name - Always visible */}
            <div>
              <label className={`block text-xs mb-1.5 font-medium ${
                darkMode ? 'text-slate-400' : 'text-slate-600'
              }`}>Model Name</label>
              <input
                type="text"
                value={embeddingConfig.model}
                onChange={(e) => onEmbeddingConfigChange({ ...embeddingConfig, model: e.target.value })}
                className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                  darkMode
                    ? 'bg-slate-800/50 text-white border-slate-700'
                    : 'bg-white text-slate-800 border-slate-300'
                }`}
                placeholder="text-embedding-v4"
              />
            </div>

            {/* Advanced Connection Settings */}
            <div className={`border-t pt-3 ${darkMode ? 'border-slate-700/30' : 'border-slate-200'}`}>
              <button
                onClick={() => setShowEmbeddingAdvanced(!showEmbeddingAdvanced)}
                className={`w-full flex items-center justify-between text-xs hover:text-blue-400 transition-colors mb-2 ${
                  darkMode ? 'text-slate-400' : 'text-slate-600'
                }`}
              >
                <span className="font-medium">Advanced Connection Settings</span>
                <svg
                  className={`w-3.5 h-3.5 transition-transform duration-300 ${
                    showEmbeddingAdvanced ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <div
                className={`overflow-hidden transition-all duration-300 ease-in-out ${
                  showEmbeddingAdvanced ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
                }`}
              >
                <div className="space-y-3 pt-1">
                  <div className={`p-2.5 rounded-lg border ${
                    darkMode
                      ? 'bg-slate-800/20 border-slate-700/30'
                      : 'bg-blue-50 border-blue-200'
                  }`}>
                    <p className={`text-[10px] leading-relaxed ${
                      darkMode ? 'text-slate-400' : 'text-slate-600'
                    }`}>
                      Leave empty to use the same connection as your LLM.
                      Override only if your embedding model is hosted elsewhere.
                    </p>
                  </div>

                  <div>
                    <label className={`block text-xs mb-1.5 font-medium ${
                      darkMode ? 'text-slate-400' : 'text-slate-600'
                    }`}>Base URL Override</label>
                    <input
                      type="text"
                      value={embeddingConfig.base_url}
                      onChange={(e) => onEmbeddingConfigChange({ ...embeddingConfig, base_url: e.target.value })}
                      className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                        darkMode
                          ? 'bg-slate-800/50 text-white border-slate-700'
                          : 'bg-white text-slate-800 border-slate-300'
                      }`}
                      placeholder={`${llmConfig.base_url}`}
                    />
                  </div>

                  <div>
                    <label className={`block text-xs mb-1.5 font-medium ${
                      darkMode ? 'text-slate-400' : 'text-slate-600'
                    }`}>API Key Override</label>
                    <input
                      type="password"
                      value={embeddingConfig.api_key}
                      onChange={(e) => onEmbeddingConfigChange({ ...embeddingConfig, api_key: e.target.value })}
                      className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all font-mono ${
                        darkMode
                          ? 'bg-slate-800/50 text-white border-slate-700'
                          : 'bg-white text-slate-800 border-slate-300'
                      }`}
                      placeholder=""
                    />
                  </div>

                  <div>
                    <label className={`block text-xs mb-1.5 font-medium ${
                      darkMode ? 'text-slate-400' : 'text-slate-600'
                    }`}>Dimensions</label>
                    <input
                      type="number"
                      value={embeddingConfig.dimensions ?? ''}
                      onChange={(e) => onEmbeddingConfigChange({
                        ...embeddingConfig,
                        dimensions: e.target.value ? parseInt(e.target.value, 10) : null
                      })}
                      className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                        darkMode
                          ? 'bg-slate-800/50 text-white border-slate-700'
                          : 'bg-white text-slate-800 border-slate-300'
                      }`}
                      placeholder="Optional (e.g., 1536)"
                    />
                    <p className={`text-[10px] mt-1 ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>Output dimension for embedding vectors (leave empty for model default)</p>
                  </div>

                  <div>
                    <label className={`block text-xs mb-1.5 font-medium ${
                      darkMode ? 'text-slate-400' : 'text-slate-600'
                    }`}>Encoding Format</label>
                    <select
                      value={embeddingConfig.encoding_format || 'base64'}
                      onChange={(e) => onEmbeddingConfigChange({ ...embeddingConfig, encoding_format: e.target.value })}
                      className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                        darkMode
                          ? 'bg-slate-800/50 text-white border-slate-700'
                          : 'bg-white text-slate-800 border-slate-300'
                      }`}
                    >
                      <option value="base64">Base64</option>
                      <option value="float">Float</option>
                    </select>
                    <p className={`text-[10px] mt-1 ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>Format for embedding vectors (base64 is more efficient)</p>
                  </div>

                  <div>
                    <label className={`block text-xs mb-1.5 font-medium ${
                      darkMode ? 'text-slate-400' : 'text-slate-600'
                    }`}>Chunk Size</label>
                    <input
                      type="number"
                      value={embeddingConfig.chunk_size ?? 1000}
                      onChange={(e) => onEmbeddingConfigChange({
                        ...embeddingConfig,
                        chunk_size: e.target.value ? parseInt(e.target.value, 10) : 1000
                      })}
                      className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all ${
                        darkMode
                          ? 'bg-slate-800/50 text-white border-slate-700'
                          : 'bg-white text-slate-800 border-slate-300'
                      }`}
                      placeholder="1000"
                    />
                    <p className={`text-[10px] mt-1 ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>Number of characters per document chunk (default: 1000)</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* API 配置 */}
      <div className={`p-4 border-b ${darkMode ? 'border-slate-700/50' : 'border-slate-200'}`}>
        <h3 className={`text-xs font-semibold mb-3 uppercase tracking-wider ${
          darkMode ? 'text-slate-400' : 'text-slate-600'
        }`}>API Configuration</h3>
        <div className="space-y-3">
          <div>
            <label className={`block text-xs mb-1.5 font-medium ${
              darkMode ? 'text-slate-400' : 'text-slate-600'
            }`}>Backend API URL</label>
            <input
              type="text"
              value={apiConfig.api_base_url}
              onChange={(e) => onApiConfigChange({ ...apiConfig, api_base_url: e.target.value })}
              className={`w-full text-sm px-3 py-2 rounded-md border focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 transition-all font-mono ${
                darkMode
                  ? 'bg-slate-800/50 text-white border-slate-700'
                  : 'bg-white text-slate-800 border-slate-300'
              }`}
              placeholder="http://localhost:2734"
            />
            <p className={`text-[10px] mt-1.5 ${darkMode ? 'text-slate-500' : 'text-slate-500'}`}>The backend server address for data2mcp API</p>
          </div>
        </div>
      </div>

      {/* 数据集列表 */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className={`text-xs font-semibold uppercase tracking-wider ${
            darkMode ? 'text-slate-400' : 'text-slate-600'
          }`}>Data Sources</h3>
          <span className={`text-xs font-medium ${
            darkMode ? 'text-slate-500' : 'text-slate-500'
          }`}>{datasets.filter(d => d.enabled).length} / {datasets.length} Active</span>
        </div>
        <div className="space-y-2.5">
          {datasets.map((dataset, index) => {
            const schema = getFieldSchema(dataset.type);
            const isExpanded = expandedDatasets[index];

            return (
              <div
                key={index}
                className={`rounded-lg border transition-all ${
                  darkMode
                    ? dataset.enabled
                      ? 'bg-slate-800/30 border-slate-700/50'
                      : 'bg-slate-800/30 border-slate-800 opacity-60'
                    : dataset.enabled
                      ? 'bg-white border-slate-200'
                      : 'bg-gray-50 border-slate-200 opacity-60'
                }`}
              >
                {/* Header */}
                <div className="p-3 pb-2">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-sm font-medium truncate ${
                          darkMode ? 'text-white' : 'text-slate-800'
                        }`}>{dataset.name}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold uppercase ${TYPE_COLORS[dataset.type]}`}>
                          {dataset.type}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-3">
                      <button
                        onClick={() => handleDatasetToggle(index)}
                        className={`w-10 h-5 rounded-full transition-all relative flex-shrink-0 ${
                          dataset.enabled ? 'bg-blue-500' : (darkMode ? 'bg-slate-700' : 'bg-slate-300')
                        }`}
                        title={dataset.enabled ? 'Enabled' : 'Disabled'}
                      >
                        <div
                          className={`w-4 h-4 bg-white rounded-full absolute top-0.5 transition-all shadow-sm ${
                            dataset.enabled ? 'right-0.5' : 'left-0.5'
                          }`}
                        ></div>
                      </button>
                      <button
                        onClick={() => handleRemoveDataset(index)}
                        className={`transition-colors p-0.5 ${
                          darkMode ? 'text-slate-500 hover:text-red-400' : 'text-slate-400 hover:text-red-500'
                        }`}
                        title="Remove"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Essential Fields */}
                  <div className="space-y-2">
                    {schema.essential.map(field => renderField(field, dataset, index))}
                  </div>
                </div>

                {/* Advanced Fields (Collapsible) */}
                {schema.advanced.length > 0 && (
                  <>
                    <div
                      className={`overflow-hidden transition-all duration-300 ease-in-out ${
                        isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <div className={`px-3 pb-2 pt-1 space-y-2 border-t ${
                        darkMode ? 'border-slate-700/30' : 'border-slate-200'
                      }`}>
                        {schema.advanced.map(field => renderField(field, dataset, index))}
                      </div>
                    </div>

                    {/* Expand/Collapse Button */}
                    <button
                      onClick={() => toggleExpanded(index)}
                      className={`w-full px-3 py-2 flex items-center justify-center gap-1.5 text-xs hover:text-blue-400 transition-all border-t group ${
                        darkMode
                          ? 'text-slate-400 hover:bg-slate-800/30 border-slate-700/30'
                          : 'text-slate-600 hover:bg-slate-50 border-slate-200'
                      }`}
                    >
                      <span className="font-medium">{isExpanded ? 'Hide' : 'Show'} Advanced Options</span>
                      <svg
                        className={`w-3.5 h-3.5 transition-transform duration-300 ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 添加按钮 */}
      <div className="p-4 pt-0 relative">
        {showAddMenu && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-10"
              onClick={() => setShowAddMenu(false)}
            ></div>

            {/* Type selection menu */}
            <div className={`absolute bottom-full left-4 right-4 mb-2 border rounded-lg shadow-2xl z-20 overflow-hidden ${
              darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
            }`}>
              <div className="p-2">
                <div className={`text-[10px] uppercase tracking-wider font-semibold px-2 py-1.5 ${
                  darkMode ? 'text-slate-400' : 'text-slate-600'
                }`}>
                  Select Data Source Type
                </div>
                {[
                  { type: 'csv', label: 'CSV File', desc: 'Comma-separated values', icon: '📊' },
                  { type: 'json', label: 'JSON File', desc: 'JSON data file', icon: '📄' },
                  { type: 'md', label: 'Markdown', desc: 'Markdown document with RAG', icon: '📝' },
                  { type: 'txt', label: 'Text File', desc: 'Plain text document with RAG', icon: '📃' },
                  { type: 'pdf', label: 'PDF Document', desc: 'PDF file with RAG', icon: '📕' },
                  { type: 'sql', label: 'SQL Database', desc: 'MySQL, PostgreSQL, SQLite', icon: '🗄️' },
                  { type: 'neo4j', label: 'Knowledge Graph', desc: 'Neo4j graph database', icon: '🕸️' },
                ].map(({ type, label, desc, icon }) => (
                  <button
                    key={type}
                    onClick={() => addDataSource(type)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md transition-all text-left group ${
                      darkMode
                        ? `hover:bg-slate-700/50 ${TYPE_COLORS[type].replace('bg-', 'hover:bg-').replace('/10', '/20')}`
                        : `hover:bg-slate-50 ${TYPE_COLORS[type].replace('bg-', 'hover:bg-').replace('/10', '/20')}`
                    }`}
                  >
                    <span className="text-2xl">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm font-medium group-hover:text-blue-500 transition-colors ${
                        darkMode ? 'text-white' : 'text-slate-800'
                      }`}>
                        {label}
                      </div>
                      <div className={`text-[10px] truncate ${
                        darkMode ? 'text-slate-400' : 'text-slate-500'
                      }`}>{desc}</div>
                    </div>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-semibold uppercase ${TYPE_COLORS[type]}`}>
                      {type}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        <button
          onClick={() => setShowAddMenu(!showAddMenu)}
          className={`w-full py-2.5 rounded-lg border-2 border-dashed text-sm transition-all font-medium flex items-center justify-center gap-2 ${
            darkMode
              ? 'border-slate-700/50 text-slate-400 hover:border-blue-500/50 hover:text-blue-400 hover:bg-blue-500/5'
              : 'border-slate-300 text-slate-600 hover:border-blue-400 hover:text-blue-500 hover:bg-blue-50'
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Data Source
        </button>

        {/* Reset to Defaults Button */}
        {onResetConfig && (
          <button
            onClick={() => {
              if (window.confirm('Are you sure you want to reset all configurations to defaults? This will clear all your custom settings.')) {
                onResetConfig();
              }
            }}
            className={`w-full mt-2 py-2.5 rounded-lg border text-sm transition-all font-medium flex items-center justify-center gap-2 ${
              darkMode
                ? 'border-slate-700 text-slate-400 hover:border-red-500/50 hover:text-red-400 hover:bg-red-500/5'
                : 'border-slate-300 text-slate-600 hover:border-red-400 hover:text-red-500 hover:bg-red-50'
            }`}
            title="Reset all configurations to default values"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset to Defaults
          </button>
        )}
      </div>
    </div>
  );
}
