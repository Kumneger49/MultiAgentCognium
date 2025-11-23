"""
Client recommendation rotation manager.
Tracks which recommendation set each client should see next.
"""

import json
from pathlib import Path
from typing import Dict, Optional

# Default paths
ROTATION_STATE_FILE = Path("rotation_state.json")
RECOMMENDATIONS_DIR = Path("recommendation_sets")
NUM_SETS = 5

class RotationManager:
    """Manages per-client rotation through recommendation sets."""
    
    def __init__(self, state_file: Path = ROTATION_STATE_FILE, num_sets: int = NUM_SETS):
        self.state_file = state_file
        self.num_sets = num_sets
        self.state: Dict[str, int] = self._load_state()
    
    def _load_state(self) -> Dict[str, int]:
        """Load rotation state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_state(self):
        """Save rotation state to file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
    
    def get_current_set(self, client_id: str) -> int:
        """
        Get the current recommendation set number for a client.
        New clients start at set 1.
        """
        if client_id not in self.state:
            # New client - start at set 1
            self.state[client_id] = 1
            self._save_state()
        
        return self.state[client_id]
    
    def advance_client(self, client_id: str) -> int:
        """
        Advance client to next set and return the new set number.
        Cycles: 1 → 2 → 3 → 4 → 5 → 1 → ...
        """
        current = self.get_current_set(client_id)
        next_set = (current % self.num_sets) + 1
        self.state[client_id] = next_set
        self._save_state()
        return next_set
    
    def get_set_for_client(self, client_id: str, advance: bool = True) -> int:
        """
        Get recommendation set for client and optionally advance to next.
        
        Args:
            client_id: Client identifier
            advance: If True, advance to next set and return the new set number
        
        Returns:
            Set number (1-5) - current set if advance=False, new set if advance=True
        """
        if advance:
            # Advance and return the new set number
            return self.advance_client(client_id)
        else:
            # Just return current set without advancing
            return self.get_current_set(client_id)
    
    def reset_client(self, client_id: str, set_number: int = 1):
        """Reset client to a specific set number."""
        if 1 <= set_number <= self.num_sets:
            self.state[client_id] = set_number
            self._save_state()
        else:
            raise ValueError(f"Set number must be between 1 and {self.num_sets}")
    
    def get_all_clients(self) -> Dict[str, int]:
        """Get all clients and their current set numbers."""
        return self.state.copy()

