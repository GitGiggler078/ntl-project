import pytest
import tempfile
import os
import sys
from pathlib import Path
from ntl_to_excel import load_cities

def test_load_cities_python_module():
    # Create a temporary Python file with cities list
    cities_content = '''
cities = [
    "Delhi",
    "Mumbai",
    "Kolkata"
]
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(cities_content)
        temp_file = f.name

    try:
        result = load_cities(temp_file)
        assert result == ["Delhi", "Mumbai", "Kolkata"]
    finally:
        os.unlink(temp_file)

def test_load_cities_missing_file():
    with pytest.raises(RuntimeError, match="CITIES_FILE not found"):
        load_cities("nonexistent.py")

def test_load_cities_invalid_module():
    cities_content = '''
# No cities variable
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(cities_content)
        temp_file = f.name

    try:
        with pytest.raises(RuntimeError, match="must define a top-level variable named `cities`"):
            load_cities(temp_file)
    finally:
        os.unlink(temp_file)

def test_load_cities_empty_list():
    cities_content = '''
cities = []
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(cities_content)
        temp_file = f.name

    try:
        with pytest.raises(RuntimeError, match="No cities found"):
            load_cities(temp_file)
    finally:
        os.unlink(temp_file)