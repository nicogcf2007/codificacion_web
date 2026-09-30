import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-toastify';
import { uploadFiles, handleAPIError } from '../services/api';
import type { UploadResponse } from '../types';

interface FileUploadProps {
  onFilesUploaded: (data: UploadResponse) => void;
  title?: string;
  subtitle?: string;
  onBack?: () => void;
  projectId?: string;
}

const FileUploadReview: React.FC<FileUploadProps> = ({ 
    onFilesUploaded, 
    title = "Cargar Archivos para Revisión",
    subtitle = "Sube el archivo de respuestas ya codificado y el archivo de códigos",
    onBack,
    projectId
}) => {
  const [responsesFile, setResponsesFile] = React.useState<File | null>(null);
  const [codesFile, setCodesFile] = React.useState<File | null>(null);
  const [uploading, setUploading] = React.useState(false);

  const onDropResponses = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setResponsesFile(acceptedFiles[0]);
    }
  }, []);

  const onDropCodes = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setCodesFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps: getRootPropsResponses, getInputProps: getInputPropsResponses, isDragActive: isDragActiveResponses } = useDropzone({
    onDrop: onDropResponses,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
  });

  const { getRootProps: getRootPropsCodes, getInputProps: getInputPropsCodes, isDragActive: isDragActiveCodes } = useDropzone({
    onDrop: onDropCodes,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
  });

  const handleUpload = async () => {
    if (!responsesFile || !codesFile) {
      toast.error('Por favor selecciona ambos archivos');
      return;
    }

    setUploading(true);
    try {
      const response = await uploadFiles(responsesFile, codesFile, projectId);
      toast.success('Archivos cargados exitosamente');
      onFilesUploaded(response);
    } catch (error) {
      const errorMessage = handleAPIError(error);
      toast.error(`Error al cargar archivos: ${errorMessage}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 py-12 px-4 flex items-center justify-center">
      <div className="max-w-4xl w-full bg-white rounded-2xl shadow-xl overflow-hidden">
        <div className="bg-purple-600 px-8 py-6 flex items-center justify-between">
            <div>
                <h2 className="text-2xl font-bold text-white">{title}</h2>
                <p className="text-purple-100 mt-1">{subtitle}</p>
            </div>
            {onBack && (
                <button 
                    onClick={onBack}
                    className="text-white hover:bg-purple-700 px-3 py-1 rounded transition"
                >
                    Volver
                </button>
            )}
        </div>

        <div className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            {/* Responses File Dropzone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Archivo de Respuestas (Codificado)
              </label>
              <div
                {...getRootPropsResponses()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
                  isDragActiveResponses
                    ? 'border-purple-500 bg-purple-50'
                    : responsesFile
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
                }`}
              >
                <input {...getInputPropsResponses()} />
                {responsesFile ? (
                  <div className="flex flex-col items-center">
                    <svg className="w-12 h-12 text-green-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-green-700 font-medium truncate max-w-full">
                      {responsesFile.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {(responsesFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <svg className="w-12 h-12 text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-gray-600 font-medium">Arrastra el archivo aquí</p>
                    <p className="text-sm text-gray-400 mt-1">o haz clic para seleccionar</p>
                  </div>
                )}
              </div>
            </div>

            {/* Codes File Dropzone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Archivo de Códigos (Maestro)
              </label>
              <div
                {...getRootPropsCodes()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
                  isDragActiveCodes
                    ? 'border-purple-500 bg-purple-50'
                    : codesFile
                    ? 'border-green-500 bg-green-50'
                    : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
                }`}
              >
                <input {...getInputPropsCodes()} />
                {codesFile ? (
                  <div className="flex flex-col items-center">
                    <svg className="w-12 h-12 text-green-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-green-700 font-medium truncate max-w-full">
                      {codesFile.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {(codesFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <svg className="w-12 h-12 text-gray-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <p className="text-gray-600 font-medium">Arrastra el archivo aquí</p>
                    <p className="text-sm text-gray-400 mt-1">o haz clic para seleccionar</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-center">
            <button
              onClick={handleUpload}
              disabled={uploading || !responsesFile || !codesFile}
              className={`
                px-8 py-4 rounded-xl font-bold text-lg shadow-lg transform transition-all duration-200
                ${
                  uploading || !responsesFile || !codesFile
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:from-purple-700 hover:to-indigo-700 hover:scale-105 hover:shadow-xl'
                }
              `}
            >
              {uploading ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Subiendo archivos...
                </span>
              ) : (
                'Continuar a Configuración'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileUploadReview;
