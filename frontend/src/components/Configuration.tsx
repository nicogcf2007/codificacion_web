import React, { useState } from 'react';
import { toast } from 'react-toastify';
import type { ProcessingConfig, ColumnConfig } from '../types';

interface ConfigurationProps {
  columns: string[];
  onStartProcessing: (config: ProcessingConfig) => void;
  onBack: () => void;
  mode?: 'codify' | 'review';
}

const Configuration: React.FC<ConfigurationProps> = ({
  columns,
  onStartProcessing,
  onBack,
  mode = 'codify'
}) => {
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [columnConfigs, setColumnConfigs] = useState<Record<string, ColumnConfig>>({});
  const [maxNewLabels, setMaxNewLabels] = useState(8);
  const [codingMode, setCodingMode] = useState<import('../types').CodingMode>('hybrid_luna');
  const [enableClustering, setEnableClustering] = useState<boolean>(true);
  const [clusterThreshold, setClusterThreshold] = useState<number>(80);
  // const [startCode, setStartCode] = useState(501); // Removed per requirement
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedColumn, setExpandedColumn] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<'selection' | 'settings'>('selection');

  const filteredColumns = columns.filter((col) =>
    col.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleColumnToggle = (column: string) => {
    setSelectedColumns((prev) => {
      const isSelected = prev.includes(column);
      if (isSelected) {
        const newConfigs = { ...columnConfigs };
        delete newConfigs[column];
        setColumnConfigs(newConfigs);
        return prev.filter((c) => c !== column);
      } else {
        setColumnConfigs(prev => ({
          ...prev,
          [column]: {
            name: column,
            multiLabel: false,
            maxLabels: 1,
            context: ''
          }
        }));
        return [...prev, column];
      }
    });
  };

  const updateColumnConfig = (column: string, updates: Partial<ColumnConfig>) => {
    setColumnConfigs(prev => ({
      ...prev,
      [column]: { ...prev[column], ...updates }
    }));
  };

  const handleNextStep = () => {
    if (selectedColumns.length === 0) {
      toast.error('Por favor selecciona al menos una columna');
      return;
    }
    setCurrentStep('settings');
  };

  const handleStart = () => {
    if (selectedColumns.length === 0) {
      toast.error('Por favor selecciona al menos una columna');
      return;
    }

    // if (maxNewLabels < 1) { ... } // Removed validation since 0 is valid

    const finalConfigs = selectedColumns.map(col => ({
      ...columnConfigs[col],
      maxNewLabels: maxNewLabels // Apply global setting to each column
    }));

    const config: ProcessingConfig = {
      columns: finalConfigs,
      question_column: 'Nombre de la Pregunta',
      max_new_labels: maxNewLabels, // Kept for backward compat, but logic uses per-column
      start_code: 501, 
      coding_mode: codingMode,
      enable_clustering: enableClustering,
      cluster_threshold: clusterThreshold,
    };

    onStartProcessing(config);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Configurar Procesamiento
          </h1>
          <p className="text-gray-600">
            {currentStep === 'selection' 
              ? 'Paso 1: Selecciona las columnas que deseas procesar'
              : 'Paso 2: Configura las opciones para cada columna seleccionada'
            }
          </p>
        </div>

        {currentStep === 'selection' ? (
          /* STEP 1: COLUMN SELECTION */
          <div className="flex flex-col-reverse lg:flex-row gap-6 max-w-7xl mx-auto">
            {/* Left: Search + Available Columns */}
            <div className="flex-1 min-w-0 order-2 lg:order-1">
              <div className="card">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">
                  Disponibles ({columns.length})
                </h2>

                {/* Search - icon beside input, no overlap */}
                <div className="flex items-center mb-4">
                  <div className="flex-1 flex items-center bg-gray-50 border border-gray-200 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-shadow">
                    <span className="pl-4 pr-2 text-gray-400 shrink-0">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </span>
                    <input
                      type="text"
                      placeholder="Buscar columnas por nombre..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="flex-1 py-3 pr-4 bg-transparent border-0 text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-0 min-w-0"
                    />
                  </div>
                </div>

                {/* Column List */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-[420px] overflow-y-auto pr-1 -mr-1">
                  {filteredColumns.map((column) => {
                    const isSelected = selectedColumns.includes(column);
                    return (
                      <button
                        key={column}
                        type="button"
                        onClick={() => handleColumnToggle(column)}
                        className={`
                          text-left rounded-lg px-3 py-2.5 flex items-center gap-3 transition-all border
                          ${isSelected 
                            ? 'bg-blue-50 border-blue-200 text-blue-800' 
                            : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700'}
                        `}
                      >
                        <div className={`
                          shrink-0 w-4 h-4 rounded border-2 flex items-center justify-center
                          ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'}
                        `}>
                          {isSelected && (
                            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                        <span className="text-sm font-medium truncate" title={column}>
                          {column}
                        </span>
                      </button>
                    );
                  })}
                </div>

                {filteredColumns.length === 0 && (
                  <p className="text-center text-gray-500 py-8 text-sm">
                    No hay columnas que coincidan con "{searchTerm}"
                  </p>
                )}
              </div>
            </div>

            {/* Right: COLUMNAS SELECCIONADAS - siempre visible */}
            <div className="lg:w-96 shrink-0 order-1 lg:order-2">
              <div className="card sticky top-4 bg-white/95 backdrop-blur">
                <h2 className="text-lg font-semibold text-gray-800 mb-3 flex items-center justify-between">
                  <span>Columnas seleccionadas</span>
                  <span className="text-sm font-normal text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full">
                    {selectedColumns.length}
                  </span>
                </h2>
                <div className="min-h-[120px] max-h-[380px] overflow-y-auto space-y-2 pr-1">
                  {selectedColumns.length === 0 ? (
                    <p className="text-sm text-gray-400 py-6 text-center">
                      Haz clic en las columnas de la izquierda para añadirlas aquí
                    </p>
                  ) : (
                    selectedColumns.map((col) => (
                      <div
                        key={col}
                        className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-blue-50 border border-blue-100 group"
                      >
                        <span className="text-sm font-medium text-gray-800 truncate" title={col}>
                          {col}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleColumnToggle(col)}
                          className="shrink-0 p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                          title="Quitar"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))
                  )}
                </div>

                {/* Navigation Buttons */}
                <div className="mt-6 pt-4 border-t space-y-3">
                  <button
                    onClick={handleNextStep}
                    disabled={selectedColumns.length === 0}
                    className={`
                      w-full py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
                      ${selectedColumns.length > 0 
                        ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm' 
                        : 'bg-gray-200 text-gray-500 cursor-not-allowed'}
                    `}
                  >
                    Continuar a Configuración
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </button>
                  <button
                    onClick={onBack}
                    className="btn-secondary w-full flex items-center justify-center gap-2"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Volver
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* STEP 2: CONFIGURATION */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fadeIn">
            {/* Left Column: List of Selected Columns to Configure */}
            <div className="lg:col-span-2 space-y-4">
               <div className="flex justify-between items-center mb-2">
                 <h2 className="text-xl font-semibold text-gray-800">
                    Configurar Columnas Seleccionadas ({selectedColumns.length})
                 </h2>
                 <button 
                    onClick={() => setCurrentStep('selection')}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium hover:underline"
                 >
                    Modificar selección
                 </button>
               </div>

               <div className="space-y-4">
                 {selectedColumns.map((column, index) => {
                    const config = columnConfigs[column];
                    const isExpanded = expandedColumn === column || (expandedColumn === null && index === 0);
                    
                    if (!config) return null;

                    return (
                      <div key={column} className="card p-0 overflow-hidden border border-gray-200 hover:border-blue-300 transition-colors">
                        <div 
                          className={`
                            p-4 cursor-pointer flex justify-between items-center
                            ${isExpanded ? 'bg-blue-50 border-b border-blue-100' : 'bg-white hover:bg-gray-50'}
                          `}
                          onClick={() => setExpandedColumn(isExpanded && expandedColumn === column ? null : column)}
                        >
                          <div className="flex items-center space-x-3">
                             <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold">
                               {index + 1}
                             </span>
                             <span className="font-semibold text-gray-800">{column}</span>
                          </div>
                          <div className="flex items-center space-x-3">
                            {config.multiLabel && (
                               <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded-full">Multi-label</span>
                            )}
                            {config.context && (
                               <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">Con Contexto</span>
                            )}
                            <svg 
                              className={`w-5 h-5 text-gray-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
                              fill="none" 
                              viewBox="0 0 24 24" 
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>

                        {isExpanded && (
                           <div className="p-5 bg-white space-y-5 animate-fadeIn">
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Multi-label Toggle */}
                                <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
                                  <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                                    <input
                                      type="checkbox"
                                      id={`multilabel-${column}`}
                                      checked={config.multiLabel}
                                      onChange={(e) => updateColumnConfig(column, { multiLabel: e.target.checked })}
                                      className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer"
                                    />
                                    <label 
                                      htmlFor={`multilabel-${column}`} 
                                      className={`toggle-label block overflow-hidden h-5 rounded-full cursor-pointer ${config.multiLabel ? 'bg-blue-600' : 'bg-gray-300'}`}
                                    ></label>
                                  </div>
                                  <div>
                                    <label htmlFor={`multilabel-${column}`} className="block text-sm font-medium text-gray-800 cursor-pointer">
                                      Permitir múltiples códigos
                                    </label>
                                    <p className="text-xs text-gray-500">
                                      La IA podrá asignar más de una categoría a cada respuesta.
                                    </p>
                                  </div>
                                </div>

                                {/* Max Labels Input */}
                                {config.multiLabel && (
                                  <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      Máximo de códigos por respuesta
                                    </label>
                                    <input
                                      type="number"
                                      min="1"
                                      max="10"
                                      value={config.maxLabels}
                                      onChange={(e) => updateColumnConfig(column, { maxLabels: parseInt(e.target.value) || 1 })}
                                      className="input-field w-full"
                                    />
                                  </div>
                                )}
                              </div>

                              {/* Context Textarea */}
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  Contexto específico para la IA (Opcional)
                                </label>
                                <textarea
                                  value={config.context}
                                  onChange={(e) => updateColumnConfig(column, { context: e.target.value })}
                                  placeholder="Describe de qué trata esta pregunta, qué tipo de respuestas esperas, o da ejemplos de cómo clasificar..."
                                  className="input-field min-h-[100px] text-sm"
                                />
                                <p className="text-xs text-gray-500 mt-1 flex justify-between">
                                  <span>Ayuda a la IA a entender mejor el contexto de esta pregunta específica.</span>
                                  {config.context.length > 0 && <span>{config.context.length} caracteres</span>}
                                </p>
                              </div>
                           </div>
                        )}
                      </div>
                    );
                 })}
               </div>
            </div>

            {/* Right Column: Global Params & Actions */}
            <div className="space-y-6">
               <div className="card sticky top-6 border-t-4 border-t-indigo-500 shadow-lg">
                  <h2 className="text-lg font-bold text-gray-800 mb-4 pb-2 border-b">
                    Parámetros Globales
                  </h2>

                  <div className="space-y-5">
                    {/* Selector de Modo de Codificación con IA */}
                    <div>
                      <label className="block text-sm font-bold text-gray-800 mb-2 flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-indigo-600"></span>
                        Modo de Codificación (IA)
                      </label>
                      <div className="space-y-2">
                        <label className={`block p-2.5 rounded-lg border cursor-pointer transition-all ${codingMode === 'hybrid_luna' ? 'bg-indigo-50 border-indigo-500 ring-2 ring-indigo-200' : 'bg-white border-gray-200 hover:border-gray-300'}`}>
                          <div className="flex items-start">
                            <input
                              type="radio"
                              name="codingMode"
                              value="hybrid_luna"
                              checked={codingMode === 'hybrid_luna'}
                              onChange={() => setCodingMode('hybrid_luna')}
                              className="mt-1 text-indigo-600 focus:ring-indigo-500"
                            />
                            <div className="ml-2 text-xs">
                              <div className="flex items-center gap-1 font-bold text-gray-900">
                                <span>🟢 Híbrido Luna</span>
                                <span className="bg-emerald-100 text-emerald-800 px-1.5 py-0.2 rounded text-[10px]">Recomendado</span>
                              </div>
                              <p className="text-gray-500 text-[11px] mt-0.5">Jev Fast-Path + GPT-6-Luna (~$0.038/1k)</p>
                            </div>
                          </div>
                        </label>

                        <label className={`block p-2.5 rounded-lg border cursor-pointer transition-all ${codingMode === 'hybrid_sol' ? 'bg-indigo-50 border-indigo-500 ring-2 ring-indigo-200' : 'bg-white border-gray-200 hover:border-gray-300'}`}>
                          <div className="flex items-start">
                            <input
                              type="radio"
                              name="codingMode"
                              value="hybrid_sol"
                              checked={codingMode === 'hybrid_sol'}
                              onChange={() => setCodingMode('hybrid_sol')}
                              className="mt-1 text-indigo-600 focus:ring-indigo-500"
                            />
                            <div className="ml-2 text-xs">
                              <div className="flex items-center gap-1 font-bold text-gray-900">
                                <span>🔵 Híbrido SOL</span>
                                <span className="bg-blue-100 text-blue-800 px-1.5 py-0.2 rounded text-[10px]">60% Exactitud</span>
                              </div>
                              <p className="text-gray-500 text-[11px] mt-0.5">Jev Fast-Path + GPT-6.1-SOL (~$0.48/1k)</p>
                            </div>
                          </div>
                        </label>

                        <label className={`block p-2.5 rounded-lg border cursor-pointer transition-all ${codingMode === 'jev_express' ? 'bg-indigo-50 border-indigo-500 ring-2 ring-indigo-200' : 'bg-white border-gray-200 hover:border-gray-300'}`}>
                          <div className="flex items-start">
                            <input
                              type="radio"
                              name="codingMode"
                              value="jev_express"
                              checked={codingMode === 'jev_express'}
                              onChange={() => setCodingMode('jev_express')}
                              className="mt-1 text-indigo-600 focus:ring-indigo-500"
                            />
                            <div className="ml-2 text-xs">
                              <div className="flex items-center gap-1 font-bold text-gray-900">
                                <span>⚡ Jev Express</span>
                                <span className="bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded text-[10px]">0.6s / rta</span>
                              </div>
                              <p className="text-gray-500 text-[11px] mt-0.5">Clasificador Puro TypeSafe (~$0.015/1k)</p>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>

                    {/* Max New Labels */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Máximo de nuevas etiquetas (Por Pregunta)
                      </label>
                      <div className="flex items-center space-x-2">
                        <input
                          type="number"
                          min="0"
                          max="100"
                          value={maxNewLabels}
                          onChange={(e) => setMaxNewLabels(parseInt(e.target.value) || 0)}
                          className="input-field w-24 text-center font-mono text-lg"
                        />
                        <span className="text-gray-500 text-sm">etiquetas</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-2 bg-yellow-50 p-2 rounded border border-yellow-100">
                        <strong>Nota:</strong> Este es el límite de códigos <em>nuevos</em> que la IA puede crear si no encuentra uno existente. (0 = Solo usar lista existente)
                      </p>
                    </div>

                    {/* Pre-agrupamiento Difuso Inteligente */}
                    <div className="p-3 bg-indigo-50/60 rounded-lg border border-indigo-100 shadow-sm">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-bold text-gray-800 flex items-center gap-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={enableClustering}
                            onChange={(e) => setEnableClustering(e.target.checked)}
                            className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                          />
                          <span>🎯 Pre-agrupamiento Inteligente</span>
                        </label>
                        <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded">
                          Ahorro ~50-70%
                        </span>
                      </div>
                      <p className="text-[11px] text-gray-600 mt-1">
                        Pre-limpia vacíos/signos y agrupa variantes difusas similares (ej. <em>"Coca-Cola"</em>, <em>"Me gusta la Coca-Cola"</em>) para codificar solo el prototipo.
                      </p>
                      {enableClustering && (
                        <div className="mt-2.5 pt-2 border-t border-indigo-100 flex items-center justify-between">
                          <span className="text-xs text-gray-700 font-medium">Umbral de Similitud:</span>
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              min="50"
                              max="100"
                              value={clusterThreshold}
                              onChange={(e) => setClusterThreshold(Math.max(50, Math.min(100, parseInt(e.target.value) || 80)))}
                              className="input-field w-16 text-center font-mono text-sm py-1"
                            />
                            <span className="text-xs text-gray-600 font-bold">%</span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="pt-4 border-t space-y-3">
                       <h3 className="text-sm font-bold text-gray-700">Resumen de Configuración:</h3>
                       <ul className="text-sm text-gray-600 space-y-2">
                         <li className="flex justify-between">
                           <span>Columnas a procesar:</span>
                           <span className="font-semibold text-gray-900">{selectedColumns.length}</span>
                         </li>
                         <li className="flex justify-between">
                           <span>Multi-etiqueta activado:</span>
                           <span className="font-semibold text-gray-900">{Object.values(columnConfigs).filter(c => c.multiLabel).length}</span>
                         </li>
                         <li className="flex justify-between">
                           <span>Con contexto personalizado:</span>
                           <span className="font-semibold text-gray-900">{Object.values(columnConfigs).filter(c => c.context).length}</span>
                         </li>
                       </ul>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="mt-8 space-y-3 pt-4 border-t">
                    <button
                      onClick={handleStart}
                      className="btn-primary w-full py-3 text-lg font-semibold shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all"
                    >
                      {mode === 'review' ? 'Iniciar Revisión' : 'Iniciar Codificación'}
                    </button>
                    <button 
                      onClick={() => setCurrentStep('selection')} 
                      className="btn-secondary w-full text-gray-600 border-gray-300"
                    >
                      Atrás
                    </button>
                  </div>
               </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Configuration;