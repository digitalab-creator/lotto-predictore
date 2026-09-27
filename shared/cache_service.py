import json
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union
import hashlib
from collections import Counter
from shared.logging_service import get_backend_logger

# Import config paths
import sys
sys.path.append('/app')
from config import CACHE_PATH

class CacheService:
    """
    File-based cache service with automatic expiration.
    Cache files are stored in JSON format for readability and debugging.
    """
    
    def __init__(self, cache_name: str, expiration_days: int = 2):
        """
        Initialize the cache service.
        
        Args:
            cache_name (str): Name of the cache (used for file naming)
            expiration_days (int): Number of days before cache expires (default: 2)
        """
        self.cache_name = cache_name
        self.expiration_days = expiration_days
        self.logger = get_backend_logger()
        
        # Create cache directory using config path
        self.cache_dir = CACHE_PATH
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache file path
        self.cache_file = self.cache_dir / f"{cache_name}_cache.json"
        
        self.logger.debug(
            f"Cache service initialized: {cache_name} -> {self.cache_file} (expires in {expiration_days} days)",
            context={
                "cache_name": cache_name,
                "cache_file": str(self.cache_file),
                "expiration_days": expiration_days
            }
        )
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            str: MD5 hash of the serialized arguments
        """
        # Create a string representation of all arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())  # Sort for consistent hashing
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        
        # Generate MD5 hash
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """
        Serialize a value with type information for proper deserialization.
        
        Args:
            value (Any): Value to serialize
            
        Returns:
            Dict[str, Any]: Serialized value with type information
        """
        if isinstance(value, Counter):
            counter_dict = dict(value)
            # Debug: log the types of keys in the Counter
            key_types = [(k, type(k)) for k in counter_dict.keys()]
            self.logger.debug(
                f"Serializing Counter with key types: {key_types[:5]}",
                context={"counter_key_types": key_types[:5]}
            )
            return {
                'type': 'Counter',
                'data': counter_dict
            }
        elif isinstance(value, (dict, list, str, int, float, bool, type(None))):
            return {
                'type': type(value).__name__,
                'data': value
            }
        else:
            # For other types, use pickle as fallback
            return {
                'type': 'pickle',
                'data': pickle.dumps(value).hex()
            }
    
    def _deserialize_value(self, serialized: Dict[str, Any]) -> Any:
        """
        Deserialize a value based on its type information.
        
        Args:
            serialized (Dict[str, Any]): Serialized value with type information
            
        Returns:
            Any: Deserialized value
        """
        value_type = serialized.get('type')
        data = serialized.get('data')
        
        if value_type == 'Counter':
            # Debug: log what we're deserializing
            key_types = [(k, type(k)) for k in data.keys()]
            self.logger.debug(
                f"Deserializing Counter with key types: {key_types[:5]}",
                context={"counter_key_types": key_types[:5]}
            )
            
            # Convert string keys back to integers for Counter objects
            counter_data = {}
            for key, value in data.items():
                try:
                    # Try to convert key to integer if it's a string
                    if isinstance(key, str) and key.isdigit():
                        counter_data[int(key)] = value
                    else:
                        counter_data[key] = value
                except (ValueError, TypeError):
                    counter_data[key] = value
            
            # Debug: log the final counter data types
            final_key_types = [(k, type(k)) for k in counter_data.keys()]
            self.logger.debug(
                f"Final Counter key types: {final_key_types[:5]}",
                context={"final_counter_key_types": final_key_types[:5]}
            )
            
            return Counter(counter_data)
        elif value_type in ['dict', 'list', 'str', 'int', 'float', 'bool', 'NoneType']:
            return data
        elif value_type == 'pickle':
            return pickle.loads(bytes.fromhex(data))
        else:
            # Fallback for unknown types
            return data
    
    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Load cache from file.
        
        Returns:
            Dict[str, Dict[str, Any]]: Cache data with timestamps
        """
        if not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Deserialize values
            for entry in cache_data.values():
                if 'value' in entry and isinstance(entry['value'], dict) and 'type' in entry['value']:
                    entry['value'] = self._deserialize_value(entry['value'])
            
            self.logger.debug(
                f"Cache loaded from file: {len(cache_data)} entries",
                context={
                    "cache_file": str(self.cache_file),
                    "cache_entries": len(cache_data)
                }
            )
            return cache_data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            self.logger.warning(
                f"Error loading cache, starting fresh: {e}",
                context={
                    "cache_file": str(self.cache_file),
                    "error": str(e)
                }
            )
            return {}
    
    def _save_cache(self, cache_data: Dict[str, Dict[str, Any]]) -> None:
        """
        Save cache to file.
        
        Args:
            cache_data (Dict[str, Dict[str, Any]]): Cache data to save
        """
        try:
            # Create a copy for serialization
            serialized_data = {}
            for key, entry in cache_data.items():
                serialized_entry = entry.copy()
                serialized_entry['value'] = self._serialize_value(entry['value'])
                serialized_data[key] = serialized_entry
            
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.cache_file.with_suffix(self.cache_file.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(serialized_data, f, indent=2)
            tmp_path.replace(self.cache_file)

            self.logger.debug(
                f"Cache saved to file: {len(cache_data)} entries",
                context={
                    "cache_file": str(self.cache_file),
                    "cache_entries": len(cache_data)
                }
            )
        except Exception as e:
            self.logger.error(
                f"Error saving cache: {e}",
                context={
                    "cache_file": str(self.cache_file),
                    "error": str(e)
                }
            )
    
    def _is_expired(self, timestamp: str) -> bool:
        """
        Check if a cache entry is expired.
        
        Args:
            timestamp (str): ISO format timestamp string
            
        Returns:
            bool: True if expired, False otherwise
        """
        try:
            cache_time = datetime.fromisoformat(timestamp)
            expiration_time = datetime.now() - timedelta(days=self.expiration_days)
            return cache_time < expiration_time
        except ValueError:
            # If timestamp is invalid, consider it expired
            return True
    
    def get(self, *args, **kwargs) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
            
        Returns:
            Optional[Any]: Cached value if found and not expired, None otherwise
        """
        cache_key = self._generate_key(*args, **kwargs)
        cache_data = self._load_cache()
        
        if cache_key not in cache_data:
            self.logger.debug(
                f"Cache miss - key not found: {cache_key}",
                context={"cache_key": cache_key}
            )
            return None
        
        entry = cache_data[cache_key]
        if self._is_expired(entry['timestamp']):
            self.logger.debug(
                f"Cache miss - entry expired: {cache_key} (timestamp: {entry['timestamp']})",
                context={
                    "cache_key": cache_key,
                    "timestamp": entry['timestamp']
                }
            )
            # Remove expired entry
            del cache_data[cache_key]
            self._save_cache(cache_data)
            return None
        
        self.logger.debug(
            f"Cache hit: {cache_key} (timestamp: {entry['timestamp']})",
            context={
                "cache_key": cache_key,
                "timestamp": entry['timestamp']
            }
        )
        return entry['value']
    
    def set(self, value: Any, *args, **kwargs) -> None:
        """
        Set a value in cache.
        
        Args:
            value (Any): Value to cache
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
        """
        cache_key = self._generate_key(*args, **kwargs)
        cache_data = self._load_cache()
        
        # Clean up expired entries first
        expired_keys = [
            key for key, entry in cache_data.items()
            if self._is_expired(entry['timestamp'])
        ]
        for key in expired_keys:
            del cache_data[key]
        
        # Add new entry
        cache_data[cache_key] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        
        self._save_cache(cache_data)
        
        self.logger.debug(
            f"Value cached successfully: {cache_key} (total entries: {len(cache_data)})",
            context={
                "cache_key": cache_key,
                "cache_entries": len(cache_data)
            }
        )
    
    def clear(self) -> None:
        """
        Clear all cache entries.
        """
        if self.cache_file.exists():
            self.cache_file.unlink()
        
        self.logger.info(
            f"Cache cleared: {self.cache_file}",
            context={"cache_file": str(self.cache_file)}
        )
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            int: Number of entries removed
        """
        cache_data = self._load_cache()
        initial_count = len(cache_data)
        
        expired_keys = [
            key for key, entry in cache_data.items()
            if self._is_expired(entry['timestamp'])
        ]
        
        for key in expired_keys:
            del cache_data[key]
        
        if expired_keys:
            self._save_cache(cache_data)
        
        removed_count = initial_count - len(cache_data)
        
        self.logger.info(
            f"Cache cleanup completed: {removed_count} entries removed, {len(cache_data)} remaining",
            context={
                "removed_entries": removed_count,
                "remaining_entries": len(cache_data)
            }
        )
        
        return removed_count

# Singleton instances for different cache types
_strong_number_cache = None
_database_cache = None

def get_strong_number_cache() -> CacheService:
    """Get the strong number cache instance"""
    global _strong_number_cache
    if _strong_number_cache is None:
        _strong_number_cache = CacheService('strong_number', expiration_days=2)
    return _strong_number_cache

def get_database_cache() -> CacheService:
    """Get the database cache instance"""
    global _database_cache
    if _database_cache is None:
        _database_cache = CacheService('database', expiration_days=1)
    return _database_cache 