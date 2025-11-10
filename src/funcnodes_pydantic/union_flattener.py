"""Extension to PydanticUnpacker for handling Union type flattening.

This module provides utilities to flatten Union[BaseModel, ...] types
in function outputs, creating a combined output with all possible fields
where non-applicable fields are filled with a sentinel value.
"""

from __future__ import annotations

import typing
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel
import funcnodes as fn

# Sentinel object for fields not present in the actual returned union member


def resolve_union_models(annotation: Any) -> list[type[BaseModel]] | None:
    """Extract all BaseModel types from a Union annotation.
    
    Args:
        annotation: Type annotation that may contain Union[BaseModel, ...]
        
    Returns:
        List of BaseModel classes if Union contains BaseModels, None otherwise
    """
    origin = get_origin(annotation)
    
    # Handle Annotated[Union[...], ...]
    if origin is typing.Annotated:
        base_type = get_args(annotation)[0]
        origin = get_origin(base_type)
        annotation = base_type
    
    if origin is not Union:
        return None
        
    union_args = get_args(annotation)
    models = []
    
    for arg in union_args:
        # Skip None type
        if arg is type(None):
            continue
            
        # Extract from Annotated if needed
        if get_origin(arg) is typing.Annotated:
            arg = get_args(arg)[0]
            
        # Check if it's a BaseModel subclass
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            models.append(arg)
            
    return models if models else None


def collect_union_fields(models: list[type[BaseModel]]) -> dict[str, tuple[type, Any]]:
    """Collect all unique fields from a list of BaseModel types.
    
    Args:
        models: List of BaseModel classes to collect fields from
        
    Returns:
        Dictionary mapping field names to (type, field_info) tuples
    """
    all_fields = {}
    
    for model in models:
        for field_name, field_info in model.model_fields.items():
            if field_name not in all_fields:
                all_fields[field_name] = (field_info.annotation, field_info)
                
    return all_fields


def _format_union_field_name(base: str, field: str) -> str:
    return f"{base}_{field}".replace(".", "_")


def flatten_union_output(
    value: BaseModel, all_fields: dict[str, Any], base_name: str | None = None
) -> dict[str, Any]:
    """Flatten a BaseModel instance with sentinel values for missing fields.
    
    Args:
        value: The actual BaseModel instance returned
        all_fields: All possible fields from the union
        base_name: Optional prefix for generated field names
        
    Returns:
        Dictionary with all fields, using fn.NoValue for missing ones
    """
    result = {}
    value_dict = value.model_dump()
    label = base_name or value.__class__.__name__
    
    for field_name in all_fields:
        key = _format_union_field_name(label, field_name)
        if field_name in value_dict:
            result[key] = value_dict[field_name]
        else:
            result[key] = fn.NoValue

    return result
