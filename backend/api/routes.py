"""
API Routes - REST endpoints for the survey coding application
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
import os
import pandas as pd
from pydantic import BaseModel

from core.session import SessionManager
from core.processor import SurveyProcessor
from core.reviewer import SurveyReviewer
from core.websocket import WebSocketManager

# Create router
router = APIRouter(prefix="/api", tags=["api"])

# Global instances (will be set by main.py)
session_manager: SessionManager = None
ws_manager: WebSocketManager = None
active_tasks: Dict[str, Any] = {}


def set_managers(session_mgr: SessionManager, websocket_mgr: WebSocketManager):
    """Set global manager instances"""
    global session_manager, ws_manager
    session_manager = session_mgr
    ws_manager = websocket_mgr


# Request/Response Models
class UploadResponse(BaseModel):
    session_id: str
    columns: List[str]
    questions: List[str]
    message: str


class ColumnConfig(BaseModel):
    name: str
    multiLabel: bool
    maxLabels: int
    context: str
    maxNewLabels: Optional[int] = 8 # Added field

class ProcessRequest(BaseModel):
    session_id: str
    columns: List[ColumnConfig]
    question_column: str = "Nombre de la Pregunta"
    max_new_labels: int = 0 # Deprecated, now per column
    start_code: int = 501
    manual_mappings: Dict[str, Dict[str, str]] = {} # New field for manual codes

class AnalyzeRequest(BaseModel):
    session_id: str
    columns: List[str]
    top_n: int = 20
    similarity_threshold: float = 80.0

class AnalyzeResponse(BaseModel):
    frequencies: Dict[str, List[Dict[str, Any]]]
    message: str


class ProcessResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    progress: float
    status: str
    message: str
    current_column: str = ""


class StopResponse(BaseModel):
    status: str
    message: str



@router.post("/analyze-frequencies", response_model=AnalyzeResponse)
async def analyze_frequencies(request: AnalyzeRequest):
    """
    Analyze frequent responses for selected columns
    """
    try:
        # Validate session
        if not session_manager.session_exists(request.session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get file paths
        responses_path = session_manager.get_file_path(request.session_id, 'responses')
        codes_path = session_manager.get_file_path(request.session_id, 'codes')
        
        # Load files (we only need responses_df really, but load_files does both)
        processor = SurveyProcessor(request.session_id)
        # Run in executor to avoid blocking
        import asyncio
        loop = asyncio.get_running_loop()
        
        responses_df, _ = await loop.run_in_executor(
            None, processor.load_files, responses_path, codes_path
        )
        
        from core import logic
        frequencies = await loop.run_in_executor(
            None, 
            logic.get_frequent_responses,
            responses_df, 
            request.columns, 
            request.top_n, 
            request.similarity_threshold
        )
        
        return AnalyzeResponse(
            frequencies=frequencies,
            message="Analysis completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in analyze_frequencies endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    responses: UploadFile = File(..., description="Responses Excel file"),
    codes: UploadFile = File(..., description="Codes Excel file")
):
    """
    Upload responses and codes Excel files
    
    Args:
        responses: Responses Excel file (.xlsx or .xls)
        codes: Codes Excel file (.xlsx or .xls)
        
    Returns:
        UploadResponse with session_id, available columns and questions
    """
    try:
        # Validate file types
        valid_extensions = ['.xlsx', '.xls']
        
        if not any(responses.filename.endswith(ext) for ext in valid_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid responses file type. Must be {', '.join(valid_extensions)}"
            )
        
        if not any(codes.filename.endswith(ext) for ext in valid_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid codes file type. Must be {', '.join(valid_extensions)}"
            )
        
        # Create session
        session_id = session_manager.create_session()
        
        # Read file contents
        responses_content = await responses.read()
        codes_content = await codes.read()
        
        # Save files
        responses_path = session_manager.save_file(
            session_id, 'responses', responses_content, responses.filename
        )
        codes_path = session_manager.save_file(
            session_id, 'codes', codes_content, codes.filename
        )
        
        # Load files to extract metadata
        processor = SurveyProcessor(session_id)
        responses_df, codes_df = processor.load_files(responses_path, codes_path)
        
        # Get available columns
        columns = processor.get_columns(responses_df)
        
        # Get available questions from codes file
        if 'Nombre de la Pregunta' in codes_df.columns:
            questions = codes_df['Nombre de la Pregunta'].dropna().unique().tolist()
        else:
            questions = []
        
        # Update session
        session_manager.update_session_status(session_id, 'idle')
        
        return UploadResponse(
            session_id=session_id,
            columns=columns,
            questions=questions,
            message="Files uploaded successfully"
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="One or both files are empty")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing Excel file: {str(e)}")
    except Exception as e:
        print(f"Error in upload endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



async def process_survey_task(session_id: str, config: Dict[str, Any]):
    """
    Background task to process survey responses
    
    Args:
        session_id: Session identifier
        config: Processing configuration
    """
    import asyncio  # Importar asyncio aquí
    try:
        # Update status
        session_manager.update_session_status(session_id, 'processing')
        await ws_manager.emit_status(session_id, 'processing', 'Iniciando procesamiento...')
        
        # Get file paths
        responses_path = session_manager.get_file_path(session_id, 'responses')
        codes_path = session_manager.get_file_path(session_id, 'codes')
        
        if not responses_path or not codes_path:
            raise ValueError("Files not found for session")
        
        # Create processor
        processor = SurveyProcessor(session_id)
        
        # Set up WebSocket callbacks
        progress_cb, status_cb = SurveyProcessor.create_websocket_callbacks(
            ws_manager, session_id
        )
        processor.set_progress_callback(progress_cb)
        processor.set_status_callback(status_cb)
        
        # Load files
        await ws_manager.emit_status(session_id, 'processing', 'Cargando archivos...')
        
        # Run loading in executor to avoid blocking
        loop = asyncio.get_running_loop()
        responses_df, codes_df = await loop.run_in_executor(
            None, processor.load_files, responses_path, codes_path
        )
        
        # Process
        await ws_manager.emit_status(session_id, 'processing', 'Procesando respuestas...')
        
        # Run processing in executor to avoid blocking
        processed_responses_df, updated_codes_df = await loop.run_in_executor(
            None, processor.process, responses_df, codes_df, config
        )
        
        # Save results
        await ws_manager.emit_status(session_id, 'processing', 'Guardando resultados de codificación...')
        
        # Generate output paths
        import os
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.dirname(responses_path)
        
        output_responses_path = os.path.join(
            session_dir, f"responses_processed_{timestamp}.xlsx"
        )
        output_codes_path = os.path.join(
            session_dir, f"codes_updated_{timestamp}.xlsx"
        )
        
        processor.save_results(
            processed_responses_df, updated_codes_df,
            output_responses_path, output_codes_path
        )
        
        # --- Start Review Process ---
        await ws_manager.emit_status(session_id, 'processing', 'Iniciando revisión automática...')
        
        # Helper to bridge reviewer progress to websocket
        def review_progress_cb(progress: float):
            try:
                # Review happens after coding, so we map 0-1 progress to a "Reviewing" state
                # or just reuse the progress bar but maybe reset it or keep it at 100%?
                # The user wants to see progress of review. 
                # Let's say review is a separate phase. We'll emit progress events.
                asyncio.run_coroutine_threadsafe(
                    ws_manager.emit_progress(session_id, progress, "Revisando asignaciones..."),
                    loop
                )
            except Exception as e:
                print(f"Error in review progress callback: {e}")

        def review_status_cb(message: str):
            try:
                asyncio.run_coroutine_threadsafe(
                    ws_manager.emit_status(session_id, 'processing', message),
                    loop
                )
            except Exception as e:
                print(f"Error in review status callback: {e}")

        # Extract columns to check (all columns processed)
        columns_to_check = [col['name'] for col in config['columns']]
        
        reviewer = SurveyReviewer(output_responses_path, output_codes_path, columns_to_check)
        reviewer.set_progress_callback(review_progress_cb)
        reviewer.set_status_callback(review_status_cb)
        
        # Run reviewer in executor
        review_results = await loop.run_in_executor(None, reviewer.run)
        
        # Update session with results (including review)
        results = {
            'processed_columns': len(config.get('columns', [])),
            'total_records': len(processed_responses_df),
            'output_responses': output_responses_path,
            'output_codes': output_codes_path,
            'review_results': review_results,
            'output_reviewed': review_results['output_file']
        }
        
        session_manager.update_session_results(session_id, results)
        session_manager.update_session_status(session_id, 'completed')
        
        # Emit completion
        await ws_manager.emit_complete(session_id, results)
        await ws_manager.emit_status(session_id, 'completed', 'Procesamiento y revisión completados')
        
        # Remove from active tasks
        if session_id in active_tasks:
            del active_tasks[session_id]
        
    except Exception as e:
        print(f"Error in process_survey_task: {e}")
        session_manager.update_session_status(session_id, 'error')
        await ws_manager.emit_error(session_id, str(e))
        
        if session_id in active_tasks:
            del active_tasks[session_id]


@router.post("/process", response_model=ProcessResponse)
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Start processing survey responses
    
    Args:
        request: Processing configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        ProcessResponse with task_id and status
    """
    try:
        # Validate session
        if not session_manager.session_exists(request.session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(request.session_id)
        
        # Check if files are uploaded
        if 'responses' not in session['files'] or 'codes' not in session['files']:
            raise HTTPException(status_code=400, detail="Files not uploaded")
        
        # Check if already processing
        if session['status'] == 'processing':
            raise HTTPException(status_code=400, detail="Session is already processing")
        
        # Prepare config
        # Convert Pydantic models to dicts for internal processing
        columns_config = [col.dict() for col in request.columns]
        
        config = {
            'columns': columns_config,
            'question_column': request.question_column,
            'max_new_labels': request.max_new_labels,
            'start_code': request.start_code,
            'manual_mappings': request.manual_mappings
        }
        
        # Save config to session
        session_manager.update_session_config(request.session_id, config)
        
        # Generate task ID
        import uuid
        task_id = str(uuid.uuid4())
        session_manager.set_task_id(request.session_id, task_id)
        
        # Store in active tasks
        active_tasks[request.session_id] = {
            'task_id': task_id,
            'status': 'starting'
        }
        
        # Start background task
        background_tasks.add_task(process_survey_task, request.session_id, config)
        
        return ProcessResponse(
            task_id=task_id,
            status='started',
            message='Processing started'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in start_processing endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.get("/progress/{session_id}", response_model=ProgressResponse)
async def get_progress(session_id: str):
    """
    Get processing progress for a session (fallback for WebSocket)
    
    Args:
        session_id: Session identifier
        
    Returns:
        ProgressResponse with current progress and status
    """
    try:
        # Validate session
        if not session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        status = session['status']
        
        # Get task info if available
        task_info = active_tasks.get(session_id, {})
        
        # Build response based on status
        if status == 'idle':
            return ProgressResponse(
                progress=0.0,
                status='idle',
                message='Esperando inicio de procesamiento'
            )
        elif status == 'processing':
            return ProgressResponse(
                progress=task_info.get('progress', 0.0),
                status='processing',
                message=task_info.get('message', 'Procesando...'),
                current_column=task_info.get('current_column', '')
            )
        elif status == 'completed':
            results = session.get('results', {})
            return ProgressResponse(
                progress=1.0,
                status='completed',
                message=f"Completado: {results.get('processed_columns', 0)} columnas procesadas"
            )
        elif status == 'error':
            return ProgressResponse(
                progress=0.0,
                status='error',
                message='Error durante el procesamiento'
            )
        else:
            return ProgressResponse(
                progress=0.0,
                status='unknown',
                message='Estado desconocido'
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_progress endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.post("/stop/{session_id}", response_model=StopResponse)
async def stop_processing(session_id: str):
    """
    Stop processing for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        StopResponse with status
    """
    try:
        # Validate session
        if not session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Check if processing
        if session['status'] != 'processing':
            return StopResponse(
                status='not_processing',
                message='Session is not currently processing'
            )
        
        # Stop the processor
        # This sets the global PROCESS_STOPPED flag
        from core import logic
        logic.stop_process()
        
        # Update session status
        session_manager.update_session_status(session_id, 'stopped')
        
        # Emit stop notification
        await ws_manager.emit_status(
            session_id, 'stopped', 
            'Procesamiento detenido por el usuario'
        )
        
        # Remove from active tasks
        if session_id in active_tasks:
            del active_tasks[session_id]
        
        return StopResponse(
            status='stopped',
            message='Processing stopped successfully'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in stop_processing endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    Delete session and cleanup temporary files
    """
    try:
        # Check if session exists (even if not, we return success for idempotency)
        if session_manager.session_exists(session_id):
            session_manager.delete_session(session_id)
            
        return {"status": "ok", "message": "Session cleaned up successfully"}
            
    except Exception as e:
        print(f"Error in cleanup_session endpoint: {e}")
        # Log error but return 500
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.get("/download/responses/{session_id}")
async def download_responses(session_id: str):
    """
    Download processed responses file
    
    Args:
        session_id: Session identifier
        
    Returns:
        Excel file with processed responses
    """
    try:
        # Validate session
        if not session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Check if processing is complete
        if session['status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail="Processing not completed yet"
            )
        
        # Get output file path
        results = session.get('results', {})
        file_path = results.get('output_responses')
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Processed file not found")
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"responses_codificadas_{timestamp}.xlsx"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in download_responses endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/download/codes/{session_id}")
async def download_codes(session_id: str):
    """
    Download updated codes file
    
    Args:
        session_id: Session identifier
        
    Returns:
        Excel file with updated codes
    """
    try:
        # Validate session
        if not session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Check if processing is complete
        if session['status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail="Processing not completed yet"
            )
        
        # Get output file path
        results = session.get('results', {})
        file_path = results.get('output_codes')
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Processed file not found")
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"codigos_actualizados_{timestamp}.xlsx"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
@router.get("/download/reviewed/{session_id}")
async def download_reviewed(session_id: str):
    """
    Download reviewed responses file
    
    Args:
        session_id: Session identifier
        
    Returns:
        Excel file with reviewed responses
    """
    try:
        # Validate session
        if not session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_manager.get_session(session_id)
        
        # Check if processing is complete
        if session['status'] != 'completed':
            raise HTTPException(
                status_code=400, 
                detail="Processing not completed yet"
            )
        
        # Get output file path
        results = session.get('results', {})
        file_path = results.get('output_reviewed')
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Reviewed file not found")
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"respuestas_revisadas_{timestamp}.xlsx"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in download_reviewed endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
