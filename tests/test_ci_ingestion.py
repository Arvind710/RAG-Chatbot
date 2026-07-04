import pytest
import json
import os
from unittest.mock import patch, MagicMock
from scripts.run_ingestion_ci import perform_health_check, get_chunk_count, write_log, main

def test_health_check_success():
    with patch("requests.head") as mock_head:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_head.return_value = mock_response
        
        perform_health_check() # Should not raise
        mock_head.assert_called_once_with("https://groww.in", timeout=10)

def test_health_check_failure():
    with patch("requests.head") as mock_head:
        mock_head.side_effect = Exception("Connection Error")
        
        with pytest.raises(Exception, match="Connection Error"):
            perform_health_check()

def test_write_log(tmp_path):
    log_file = tmp_path / "ingestion_log.json"
    
    with patch("scripts.run_ingestion_ci.LOG_FILE", str(log_file)):
        write_log("success", 12.34, 100)
        
        assert os.path.exists(log_file)
        with open(log_file, "r") as f:
            data = json.load(f)
            
        assert data["status"] == "success"
        assert data["duration_seconds"] == 12.34
        assert data["chunks_count"] == 100
        assert data["error_message"] is None

@patch("sys.exit")
@patch("scripts.run_ingestion_ci.write_log")
@patch("scripts.run_ingestion_ci.get_chunk_count")
@patch("scripts.run_ingestion_ci.run_ingestion_main")
@patch("scripts.run_ingestion_ci.perform_health_check")
def test_main_success(mock_health, mock_run, mock_count, mock_log, mock_exit):
    mock_count.return_value = 55
    
    main()
    
    mock_health.assert_called_once()
    mock_run.assert_called_once()
    mock_log.assert_called_once()
    
    log_args = mock_log.call_args[0]
    assert log_args[0] == "success"
    assert log_args[2] == 55 # chunks_count
    
    mock_exit.assert_called_once_with(0)

@patch("sys.exit")
@patch("scripts.run_ingestion_ci.write_log")
@patch("scripts.run_ingestion_ci.get_chunk_count")
@patch("scripts.run_ingestion_ci.run_ingestion_main")
@patch("scripts.run_ingestion_ci.perform_health_check")
def test_main_failure(mock_health, mock_run, mock_count, mock_log, mock_exit):
    mock_health.side_effect = Exception("Health Check Failed")
    mock_count.return_value = 0
    
    main()
    
    mock_health.assert_called_once()
    mock_run.assert_not_called()
    mock_log.assert_called_once()
    
    log_args = mock_log.call_args[0]
    assert log_args[0] == "failure"
    assert log_args[2] == 0 # chunks_count
    
    log_kwargs = mock_log.call_args[1]
    assert log_kwargs["error_message"] == "Health Check Failed"
    
    mock_exit.assert_called_once_with(1)
