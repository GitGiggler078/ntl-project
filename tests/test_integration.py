import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ntl_to_excel import load_cities

def test_geocoding_and_gee_processing(monkeypatch):
    # Mock environment variables
    monkeypatch.setenv('GEE_PROJECT_ID', 'test-project')
    monkeypatch.setenv('START_DATE', '2025-04-15')
    monkeypatch.setenv('END_DATE', '2026-04-15')
    monkeypatch.setenv('CITIES_FILE', 'tests/test_cities.py')

    # Create a test cities file
    test_cities_path = Path('tests/test_cities.py')
    test_cities_path.write_text('cities = ["Delhi", "Mumbai"]')
    
    # Mock geopy
    mock_location = MagicMock()
    mock_location.longitude = 77.1025
    mock_location.latitude = 28.7041
    monkeypatch.setattr('geopy.geocoders.Nominatim.geocode', lambda self, query: mock_location)

    # Test load_cities
    cities = load_cities(str(test_cities_path))
    assert cities == ['Delhi', 'Mumbai']

    # Clean up
    test_cities_path.unlink()