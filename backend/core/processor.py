"""
Survey Processor - Wrapper around core logic functions
Provides a clean interface for processing surveys with callbacks
"""
import pandas as pd
from typing import Callable, Optional, Dict, List, Tuple
from . import logic as logic


class SurveyProcessor:
    """Processor for survey coding with AI"""
    
    def __init__(self, session_id: str):
        """
        Initialize processor for a session
        
        Args:
            session_id: Unique identifier for this processing session
        """
        self.session_id = session_id
        self.stop_flag = False
        self.progress_callback: Optional[Callable[[float], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        
        # Reset global flags
        logic.reset_process_flag()
    
    def set_progress_callback(self, callback: Callable[[float], None]) -> None:
        """Set callback for progress updates (0.0 to 1.0)"""
        self.progress_callback = callback
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for status messages"""
        self.status_callback = callback
    
    def load_files(self, responses_path: str, codes_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load Excel files for responses and codes
        
        Args:
            responses_path: Path to responses Excel file
            codes_path: Path to codes Excel file
            
        Returns:
            Tuple of (responses_df, codes_df)
        """
        return logic.load_files(responses_path, codes_path)
    
    def get_columns(self, responses_df: pd.DataFrame) -> List[str]:
        """
        Get list of column names from responses dataframe
        
        Args:
            responses_df: Responses dataframe
            
        Returns:
            List of column names
        """
        return responses_df.columns.tolist()
    
    def process(self, responses_df: pd.DataFrame, codes_df: pd.DataFrame,
                config: Dict, save_callback: Optional[Callable[[pd.DataFrame, pd.DataFrame], None]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Process responses with AI coding
        
        Args:
            responses_df: Responses dataframe
            codes_df: Codes dataframe
            config: Configuration dictionary with:
                - columns: List of column names to process
                - question_column: Name of question column (default: 'Nombre de la Pregunta')
                - max_new_labels: Maximum new labels to create (default: 8)
                - start_code: Starting code for _OTRO columns (default: 501)
            save_callback: Optional callback to save intermediate results
                
        Returns:
            Tuple of (processed_responses_df, updated_codes_df)
        """
        # Extract configuration
        columns = config.get('columns', [])
        question_column = config.get('question_column', 'Nombre de la Pregunta')
        max_new_labels = config.get('max_new_labels', 8)
        start_code = config.get('start_code', 501)
        
        # Prepare limit dictionaries
        # Global counter removed, now handled per-column in logic.py
        limit_labels = {
            'count': 0,
            'max': 9999 # Arbitrary high number as global limit is deprecated
        }
        
        limit_77 = {
            'new_labels': []
        }
        
        # 1. Apply Manual Mappings (New Feature)
        manual_mappings = config.get('manual_mappings', {})
        if manual_mappings:
            if self.status_callback:
                self.status_callback("Aplicando codificación manual...")
                
            responses_df, modified = logic.apply_manual_coding(responses_df, manual_mappings)
            
            if self.status_callback:
                self.status_callback(f"Codificación manual completada. {len(modified)} celdas pre-asignadas.")
        
        # Process responses with callbacks
        processed_responses_df, updated_codes_df = logic.process_responses(
            responses_df=responses_df,
            codes_df=codes_df,
            columns_config=columns, # Pass columns config object list
            question_column=question_column,
            limit_77=limit_77,
            limit_labels=limit_labels,
            progress_callback=self.progress_callback,
            status_callback=self.status_callback,
            save_callback=save_callback
        )
        
        return processed_responses_df, updated_codes_df
    
    def stop(self) -> None:
        """Stop the processing"""
        self.stop_flag = True
        logic.stop_process()
        if self.status_callback:
            self.status_callback("Proceso detenido por el usuario")
    
    def is_stopped(self) -> bool:
        """Check if processing has been stopped"""
        return self.stop_flag or logic.PROCESS_STOPPED
    
    def save_results(self, responses_df: pd.DataFrame, codes_df: pd.DataFrame,
                    responses_path: str, codes_path: str) -> None:
        """
        Save processed results to Excel files
        
        Args:
            responses_df: Processed responses dataframe
            codes_df: Updated codes dataframe
            responses_path: Path to save responses
            codes_path: Path to save codes
        """
        responses_df.to_excel(responses_path, index=False)
        codes_df.to_excel(codes_path, index=False, sheet_name='Codificación')
        
        if self.status_callback:
            self.status_callback(f"Resultados guardados en {responses_path} y {codes_path}")


    @staticmethod
    def create_websocket_callbacks(ws_manager, session_id: str):
        """
        Create callbacks that emit via WebSocket
        
        Args:
            ws_manager: WebSocketManager instance
            session_id: Session identifier
            
        Returns:
            Tuple of (progress_callback, status_callback)
        """
        import asyncio
        
        # Capture the running loop (main thread loop)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        def progress_callback(progress: float):
            """Callback for progress updates - Thread safe"""
            try:
                # Schedule in the main loop from the worker thread
                asyncio.run_coroutine_threadsafe(
                    ws_manager.emit_progress(session_id, progress),
                    loop
                )
            except Exception as e:
                print(f"Error in progress callback: {e}")
        
        def status_callback(message: str):
            """Callback for status updates - Thread safe"""
            try:
                # Schedule in the main loop from the worker thread
                asyncio.run_coroutine_threadsafe(
                    ws_manager.emit_status(session_id, 'processing', message),
                    loop
                )
            except Exception as e:
                print(f"Error in status callback: {e}")
        
        return progress_callback, status_callback
