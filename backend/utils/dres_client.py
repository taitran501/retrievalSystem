"""
DRES (Digital Repository Evaluation System) Client for AI Challenge 2024.
Handles authentication, result formatting, and submission to DRES evaluation server.
"""

import requests
from typing import List, Optional, Dict, Any
import logging

try:
    from .timestamp_utils import (
        frame_to_milliseconds,
        seconds_to_milliseconds,
        remove_file_extension,
        calculate_end_time,
        DEFAULT_FPS
    )
except ImportError:
    # Fallback for when running as script
    from timestamp_utils import (
        frame_to_milliseconds,
        seconds_to_milliseconds,
        remove_file_extension,
        calculate_end_time,
        DEFAULT_FPS
    )


class DRESClient:
    """
    Client for interacting with DRES evaluation server.
    
    Handles:
    - Authentication (login)
    - Getting active evaluations
    - Formatting search results for DRES protocol
    - Submitting KIS (Known-Item Search) and Q&A results
    """
    
    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_id: Optional[str] = None,
        fps: float = DEFAULT_FPS,
        timeout: int = 15
    ):
        """
        Initialize DRES client.
        
        Args:
            base_url: DRES server base URL (e.g., "http://192.168.28.151:5000")
            username: Username for auto-login (optional if session_id provided)
            password: Password for auto-login (optional if session_id provided)
            session_id: Pre-existing session ID (optional, will login if not provided)
            fps: Default FPS for timestamp conversion (default: 25.0)
            timeout: Request timeout in seconds (default: 15)
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_id = session_id
        self.fps = fps
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Cache for evaluation ID
        self._evaluation_id: Optional[str] = None
    
    def login(self) -> str:
        """
        Login to DRES and get session ID.
        
        Returns:
            Session ID string
        
        Raises:
            RuntimeError: If login fails
        """
        if self.session_id:
            self.logger.info("Using provided session ID")
            return self.session_id
        
        if not self.username or not self.password:
            raise RuntimeError(
                "No session_id provided and username/password not set. "
                "Either provide session_id or username/password for auto-login."
            )
        
        login_url = f"{self.base_url}/api/v2/login"
        payload = {"username": self.username, "password": self.password}
        
        try:
            resp = requests.post(login_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            
            data = resp.json()
            # Try different possible keys for session ID
            sid = data.get("sessionId") or data.get("sessionID") or data.get("session_id")
            
            if not sid:
                raise RuntimeError(f"Login response missing sessionId: {data}")
            
            self.session_id = sid
            self.logger.info(f"Login successful. Session ID: {sid[:20]}...")
            return sid
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Login failed: HTTP {getattr(e.response, 'status_code', 'N/A')}"
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {str(e)}"
            raise RuntimeError(error_msg) from e
    
    def get_active_evaluation(self, session_id: Optional[str] = None) -> str:
        """
        Get active evaluation ID from DRES.
        
        Args:
            session_id: Optional session ID (uses self.session_id if not provided)
        
        Returns:
            Active evaluation ID string
        
        Raises:
            RuntimeError: If no active evaluation found or request fails
        """
        if self._evaluation_id:
            return self._evaluation_id
        
        if not session_id:
            session_id = self.session_id or self.login()
        
        url = f"{self.base_url}/api/v2/client/evaluation/list"
        
        try:
            resp = requests.get(
                url,
                params={"session": session_id},
                timeout=self.timeout
            )
            resp.raise_for_status()
            
            evaluations = resp.json()
            
            # Find active evaluation
            active = next(
                (e for e in evaluations if str(e.get("status", "")).upper() == "ACTIVE"),
                None
            )
            
            if not active:
                raise RuntimeError("No active evaluation found in DRES server.")
            
            eval_id = str(active.get("id"))
            self._evaluation_id = eval_id
            self.logger.info(f"Found active evaluation ID: {eval_id}")
            return eval_id
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Get evaluation list failed: HTTP {getattr(e.response, 'status_code', 'N/A')}"
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.text
                    error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {str(e)}"
            raise RuntimeError(error_msg) from e
    
    def format_kis_result(
        self,
        result: Dict[str, Any],
        end_duration_ms: int = 5000
    ) -> Dict[str, Any]:
        """
        Format search result for Known-Item Search (KIS) submission.
        
        Args:
            result: Search result dict with keys:
                - 'video' or 'video_id': Video name (may have extension)
                - 'frame_id': Frame index (integer)
                - 'time': Optional timestamp in seconds (string or float)
            end_duration_ms: Duration to add for end time in milliseconds (default: 5000)
        
        Returns:
            Formatted result dict with:
                - 'mediaItemName': Video name without extension
                - 'start': Start time in milliseconds
                - 'end': End time in milliseconds
        """
        # Get video name and remove extension
        video_name = result.get('video') or result.get('video_id', '')
        media_item_name = remove_file_extension(video_name)
        
        # Calculate start time in milliseconds
        # Priority: use 'time' field if available, otherwise calculate from frame_id
        if 'time' in result and result['time']:
            start_ms = seconds_to_milliseconds(result['time'])
        elif 'frame_id' in result:
            start_ms = frame_to_milliseconds(result['frame_id'], fps=self.fps)
        else:
            raise ValueError("Result must have either 'time' or 'frame_id' field")
        
        # Calculate end time
        end_ms = calculate_end_time(start_ms, duration_ms=end_duration_ms)
        
        return {
            "mediaItemName": media_item_name,
            "start": start_ms,
            "end": end_ms
        }
    
    def format_qa_result(
        self,
        result: Dict[str, Any],
        question: str,
        answer: Optional[str] = None
    ) -> str:
        """
        Format search result for Q&A submission.
        
        Format: <ANSWER>-<VIDEO_NAME>-<TIMESTAMP>
        
        Args:
            result: Search result dict (same format as format_kis_result)
            question: Question text
            answer: Optional answer text (if not provided, uses video name and timestamp)
        
        Returns:
            Formatted Q&A string
        """
        # Get video name and remove extension
        video_name = result.get('video') or result.get('video_id', '')
        media_item_name = remove_file_extension(video_name)
        
        # Calculate timestamp in milliseconds
        if 'time' in result and result['time']:
            timestamp_ms = seconds_to_milliseconds(result['time'])
        elif 'frame_id' in result:
            timestamp_ms = frame_to_milliseconds(result['frame_id'], fps=self.fps)
        else:
            raise ValueError("Result must have either 'time' or 'frame_id' field")
        
        if answer:
            return f"{answer}-{media_item_name}-{timestamp_ms}"
        else:
            # Default format: use question as answer prefix
            return f"{question}-{media_item_name}-{timestamp_ms}"
    
    def submit_kis(
        self,
        results: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        evaluation_id: Optional[str] = None,
        end_duration_ms: int = 5000
    ) -> Dict[str, Any]:
        """
        Submit Known-Item Search results to DRES.
        
        Args:
            results: List of search result dicts (top K results)
            session_id: Optional session ID (uses self.session_id if not provided)
            evaluation_id: Optional evaluation ID (fetches if not provided)
            end_duration_ms: Duration to add for end time in milliseconds
        
        Returns:
            DRES submission response
        """
        if not session_id:
            session_id = self.session_id or self.login()
        
        if not evaluation_id:
            evaluation_id = self.get_active_evaluation(session_id)
        
        # Format results
        formatted_answers = []
        for result in results:
            try:
                formatted = self.format_kis_result(result, end_duration_ms=end_duration_ms)
                formatted_answers.append(formatted)
            except Exception as e:
                self.logger.warning(f"Failed to format result: {e}, skipping...")
                continue
        
        if not formatted_answers:
            raise ValueError("No valid results to submit after formatting")
        
        # Prepare submission body
        body = {
            "answerSets": [
                {
                    "answers": formatted_answers
                }
            ]
        }
        
        # Submit
        url = f"{self.base_url}/api/v2/submit/{evaluation_id}"
        
        try:
            resp = requests.post(
                url,
                params={"session": session_id},
                json=body,
                timeout=self.timeout
            )
            resp.raise_for_status()
            
            response_data = resp.json()
            self.logger.info(f"DRES KIS submission successful: {len(formatted_answers)} results")
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"DRES submission failed: HTTP {getattr(e.response, 'status_code', 'N/A')}"
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.json().get("description", e.response.text)
                    error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {str(e)}"
            raise RuntimeError(error_msg) from e
    
    def submit_qa(
        self,
        result: Dict[str, Any],
        question: str,
        answer: Optional[str] = None,
        session_id: Optional[str] = None,
        evaluation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit Q&A result to DRES.
        
        Args:
            result: Search result dict
            question: Question text
            answer: Optional answer text
            session_id: Optional session ID (uses self.session_id if not provided)
            evaluation_id: Optional evaluation ID (fetches if not provided)
        
        Returns:
            DRES submission response
        """
        if not session_id:
            session_id = self.session_id or self.login()
        
        if not evaluation_id:
            evaluation_id = self.get_active_evaluation(session_id)
        
        # Format Q&A result
        try:
            qa_text = self.format_qa_result(result, question, answer=answer)
        except Exception as e:
            raise ValueError(f"Failed to format Q&A result: {e}")
        
        # Prepare submission body
        body = {
            "answerSets": [
                {
                    "answers": [
                        {"text": qa_text}
                    ]
                }
            ]
        }
        
        # Submit
        url = f"{self.base_url}/api/v2/submit/{evaluation_id}"
        
        try:
            resp = requests.post(
                url,
                params={"session": session_id},
                json=body,
                timeout=self.timeout
            )
            resp.raise_for_status()
            
            response_data = resp.json()
            self.logger.info(f"DRES Q&A submission successful")
            return response_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"DRES submission failed: HTTP {getattr(e.response, 'status_code', 'N/A')}"
            try:
                if hasattr(e, 'response') and e.response:
                    error_detail = e.response.json().get("description", e.response.text)
                    error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {str(e)}"
            raise RuntimeError(error_msg) from e
    
    def submit_batch(
        self,
        results: List[Dict[str, Any]],
        question_type: str = "kis",
        question: Optional[str] = None,
        session_id: Optional[str] = None,
        evaluation_id: Optional[str] = None,
        end_duration_ms: int = 5000
    ) -> Dict[str, Any]:
        """
        Submit batch of results (wrapper for submit_kis or submit_qa).
        
        Args:
            results: List of search result dicts
            question_type: "kis" or "qa" (default: "kis")
            question: Required for "qa" type
            session_id: Optional session ID
            evaluation_id: Optional evaluation ID
            end_duration_ms: Duration for end time (KIS only)
        
        Returns:
            DRES submission response
        """
        if question_type.lower() == "qa":
            if not question:
                raise ValueError("Question is required for Q&A submission")
            if len(results) > 1:
                self.logger.warning("Q&A submission typically uses single result, using first result")
            return self.submit_qa(
                results[0],
                question,
                session_id=session_id,
                evaluation_id=evaluation_id
            )
        else:
            return self.submit_kis(
                results,
                session_id=session_id,
                evaluation_id=evaluation_id,
                end_duration_ms=end_duration_ms
            )

