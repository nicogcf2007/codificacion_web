import React from 'react';
import { getResponsesDownloadUrl, getCodesDownloadUrl, getReviewedDownloadUrl } from '../services/api';
import type { ProcessingResults } from '../types';

interface ResultsProps {
  sessionId: string;
  results: ProcessingResults;
  onReset: () => void;
}

const Results: React.FC<ResultsProps> = ({ sessionId, results, onReset }) => {
  const handleDownload = (type: 'responses' | 'codes' | 'reviewed') => {
    let url = '';
    if (type === 'responses') url = getResponsesDownloadUrl(sessionId);
    else if (type === 'codes') url = getCodesDownloadUrl(sessionId);
    else if (type === 'reviewed') url = getReviewedDownloadUrl(sessionId);
    
    window.location.href = url;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Success Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-green-500 rounded-full mb-4">
            <svg
              className="w-12 h-12 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            ¡Procesamiento Completado!
          </h1>
          <p className="text-gray-600">
            Tus archivos han sido procesados exitosamente
          </p>
        </div>

        {/* Results Summary */}
        <div className="card mb-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">
            Resumen del Procesamiento
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-600 font-medium mb-1">
                    Columnas Procesadas
                  </p>
                  <p className="text-3xl font-bold text-blue-900">
                    {results.processed_columns}
                  </p>
                </div>
                <svg
                  className="w-12 h-12 text-blue-500 opacity-50"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
                  />
                </svg>
              </div>
            </div>

            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border border-purple-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-purple-600 font-medium mb-1">
                    Registros Totales
                  </p>
                  <p className="text-3xl font-bold text-purple-900">
                    {results.total_records}
                  </p>
                </div>
                <svg
                  className="w-12 h-12 text-purple-500 opacity-50"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-600 font-medium mb-1">
                    Nuevas Etiquetas
                  </p>
                  <p className="text-3xl font-bold text-green-900">
                    {results.new_labels_created || 0}
                  </p>
                </div>
                <svg
                  className="w-12 h-12 text-green-500 opacity-50"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* Review Results Summary */}
        {results.review_results && (
          <div className="card mb-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6">
              Resultados de la Revisión Automática
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-gradient-to-br from-yellow-50 to-orange-100 rounded-lg p-6 border border-orange-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-orange-600 font-medium mb-1">
                      Correcciones Realizadas
                    </p>
                    <p className="text-3xl font-bold text-orange-900">
                      {results.review_results.corrections_made}
                    </p>
                  </div>
                  <svg
                    className="w-12 h-12 text-orange-500 opacity-50"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                    />
                  </svg>
                </div>
              </div>

              <div className="bg-gradient-to-br from-teal-50 to-teal-100 rounded-lg p-6 border border-teal-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-teal-600 font-medium mb-1">
                      Registros Revisados
                    </p>
                    <p className="text-3xl font-bold text-teal-900">
                      {results.review_results.total_reviewed}
                    </p>
                  </div>
                  <svg
                    className="w-12 h-12 text-teal-500 opacity-50"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Download Section */}
        <div className="card mb-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-6">
            Descargar Resultados
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={() => handleDownload('responses')}
              className="flex items-center justify-between p-6 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg transition-all duration-200 shadow-md hover:shadow-lg"
            >
              <div className="flex items-center space-x-4">
                <svg
                  className="w-10 h-10"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <div className="text-left">
                  <p className="font-semibold text-lg">Respuestas Codificadas</p>
                  <p className="text-sm text-blue-100">
                    Archivo Excel con códigos asignados
                  </p>
                </div>
              </div>
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>

            <button
              onClick={() => handleDownload('codes')}
              className="flex items-center justify-between p-6 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white rounded-lg transition-all duration-200 shadow-md hover:shadow-lg"
            >
              <div className="flex items-center space-x-4">
                <svg
                  className="w-10 h-10"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <div className="text-left">
                  <p className="font-semibold text-lg">Códigos Actualizados</p>
                  <p className="text-sm text-purple-100">
                    Archivo Excel con nuevas etiquetas
                  </p>
                </div>
              </div>
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>

            <button
              onClick={() => handleDownload('reviewed')}
              className="flex items-center justify-between p-6 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white rounded-lg transition-all duration-200 shadow-md hover:shadow-lg col-span-1 md:col-span-2"
            >
              <div className="flex items-center space-x-4">
                <svg
                  className="w-10 h-10"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div className="text-left">
                  <p className="font-semibold text-lg">Respuestas Revisadas (IA)</p>
                  <p className="text-sm text-orange-100">
                    Archivo con asignaciones verificadas y corregidas
                  </p>
                </div>
              </div>
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="card">
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={onReset}
              className="btn-primary flex-1"
            >
              Procesar Nuevos Archivos
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Results;
