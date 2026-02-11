# backend/agent/expression_loader.py
"""
CSV-based Expression Dictionary Loader

Loads accord and note descriptions from CSV files and provides
case-insensitive lookup methods.
"""

import csv
import os
from pathlib import Path
from typing import Dict, Optional


class ExpressionLoader:
    """
    Singleton loader for accord and note expression dictionaries.
    
    Loads CSV files once at module import time and provides
    case-insensitive lookup methods.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.accord_dict: Dict[str, str] = {}
        self.note_dict: Dict[str, str] = {}
        
        # Docker-compatible path resolution: use PROJECT_ROOT env var, fallback to /app/
        # In Docker: PROJECT_ROOT not set → uses /app/ → CSV files at /app/*.csv
        # In local dev: Can set PROJECT_ROOT=/path/to/project if needed
        project_root = Path(os.getenv('PROJECT_ROOT', '/app/'))
        
        # Load accord dictionary
        accord_path = project_root / "accord_desc_dictionary.csv"
        self._load_accord_dict(accord_path)
        
        # Load note dictionary
        note_path = project_root / "note_desc_dictionary.csv"
        self._load_note_dict(note_path)
        
        self._initialized = True
    
    def _load_accord_dict(self, path: Path):
        """Load accord descriptions from CSV."""
        try:
            # Try utf-8-sig first (handles BOM)
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    accord = row.get('accord', '').strip()
                    desc1 = row.get('desc1', '').strip()
                    desc2 = row.get('desc2', '').strip()
                    desc3 = row.get('desc3', '').strip()
                    
                    if accord:
                        # Combine all descriptions
                        combined = f"{desc1}, {desc2}, {desc3}"
                        # Store with normalized key (lowercase)
                        self.accord_dict[accord.lower()] = combined
        except UnicodeDecodeError:
            # Fallback to cp949 for Korean compatibility
            try:
                with open(path, 'r', encoding='cp949') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        accord = row.get('accord', '').strip()
                        desc1 = row.get('desc1', '').strip()
                        desc2 = row.get('desc2', '').strip()
                        desc3 = row.get('desc3', '').strip()
                        
                        if accord:
                            combined = f"{desc1}, {desc2}, {desc3}"
                            self.accord_dict[accord.lower()] = combined
            except Exception as e:
                print(f"⚠️ [ExpressionLoader] Failed to load accord dictionary: {e}")
        except FileNotFoundError:
            print(f"⚠️ [ExpressionLoader] Accord dictionary not found: {path}")
        except Exception as e:
            print(f"⚠️ [ExpressionLoader] Error loading accord dictionary: {e}")
    
    def _load_note_dict(self, path: Path):
        """Load note descriptions from CSV."""
        try:
            # Try utf-8-sig first
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Column name is "노트 (Note)"
                    note = row.get('노트 (Note)', '').strip()
                    desc = row.get('한글 설명', '').strip()
                    
                    if note and desc:
                        # Store with normalized key (lowercase)
                        self.note_dict[note.lower()] = desc
        except UnicodeDecodeError:
            # Fallback to cp949
            try:
                with open(path, 'r', encoding='cp949') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        note = row.get('노트 (Note)', '').strip()
                        desc = row.get('한글 설명', '').strip()
                        
                        if note and desc:
                            self.note_dict[note.lower()] = desc
            except Exception as e:
                print(f"⚠️ [ExpressionLoader] Failed to load note dictionary: {e}")
        except FileNotFoundError:
            print(f"⚠️ [ExpressionLoader] Note dictionary not found: {path}")
        except Exception as e:
            print(f"⚠️ [ExpressionLoader] Error loading note dictionary: {e}")
    
    def get_accord_desc(self, name: str) -> str:
        """
        Get accord description by name (case-insensitive).
        
        Args:
            name: Accord name (e.g., "Woody", "woody", "WOODY")
        
        Returns:
            Combined description string, or empty string if not found
        """
        if not name:
            return ""
        
        normalized = name.strip().lower()
        return self.accord_dict.get(normalized, "")
    
    def get_note_desc(self, name: str) -> str:
        """
        Get note description by name (case-insensitive).
        
        Args:
            name: Note name (e.g., "Musk", "musk", "MUSK")
        
        Returns:
            Description string, or empty string if not found
        """
        if not name:
            return ""
        
        normalized = name.strip().lower()
        return self.note_dict.get(normalized, "")


# Create singleton instance at module import
_loader = ExpressionLoader()


# Convenience functions for direct access
def get_accord_desc(name: str) -> str:
    """Get accord description (convenience function)."""
    return _loader.get_accord_desc(name)


def get_note_desc(name: str) -> str:
    """Get note description (convenience function)."""
    return _loader.get_note_desc(name)
