"""Test Union type flattening functionality."""

from __future__ import annotations

import typing
from typing import Union

import pytest
from pydantic import BaseModel, Field
import funcnodes as fn

from funcnodes_pydantic.union_flattener import (
    collect_union_fields,
    flatten_union_output,
    resolve_union_models,
)


class SuccessResponse(BaseModel):
    status: typing.Literal["success"] = "success"
    data: str = Field(..., description="Success data")
    timestamp: float = Field(..., description="Success timestamp")


class ErrorResponse(BaseModel):
    status: typing.Literal["error"] = "error"
    error_code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")


class WarningResponse(BaseModel):
    status: typing.Literal["warning"] = "warning"
    warning_level: int = Field(..., description="Warning severity level")
    details: list[str] = Field(default_factory=list, description="Warning details")


ApiResponse = Union[SuccessResponse, ErrorResponse, WarningResponse]


def test_resolve_union_models():
    """Test extracting BaseModel types from Union."""
    models = resolve_union_models(ApiResponse)
    assert models is not None
    assert len(models) == 3
    assert SuccessResponse in models
    assert ErrorResponse in models
    assert WarningResponse in models


def test_collect_union_fields():
    """Test collecting all fields from Union members."""
    models = resolve_union_models(ApiResponse)
    fields = collect_union_fields(models)
    
    # Should have all unique fields from all models
    expected_fields = {
        "status",
        "data",
        "timestamp",
        "error_code",
        "message",
        "warning_level",
        "details",
    }
    assert set(fields.keys()) == expected_fields


def test_flatten_union_output_success():
    """Test flattening a success response."""
    response = SuccessResponse(data="test", timestamp=123.45)
    models = resolve_union_models(ApiResponse)
    fields = collect_union_fields(models)
    
    flattened = flatten_union_output(response, fields)
    
    # Check present fields
    assert flattened["status"] == "success"
    assert flattened["data"] == "test"
    assert flattened["timestamp"] == 123.45
    assert flattened["__typename__"] == "SuccessResponse"
    
    # Check sentinel values for fields from other models
    assert flattened["error_code"] is fn.NoValue
    assert flattened["message"] is fn.NoValue
    assert flattened["warning_level"] is fn.NoValue
    assert flattened["details"] is fn.NoValue


def test_flatten_union_output_error():
    """Test flattening an error response."""
    response = ErrorResponse(error_code=404, message="Not found")
    models = resolve_union_models(ApiResponse)
    fields = collect_union_fields(models)
    
    flattened = flatten_union_output(response, fields)
    
    # Check present fields
    assert flattened["status"] == "error"
    assert flattened["error_code"] == 404
    assert flattened["message"] == "Not found"
    assert flattened["__typename__"] == "ErrorResponse"
    
    # Check sentinel values
    assert flattened["data"] is fn.NoValue
    assert flattened["timestamp"] is fn.NoValue
    assert flattened["warning_level"] is fn.NoValue
    assert flattened["details"] is fn.NoValue


def test_optional_union():
    """Test handling Optional[Union[...]]."""
    OptionalApi = typing.Optional[ApiResponse]
    
    models = resolve_union_models(OptionalApi)
    assert models is not None
    assert len(models) == 3  # None is filtered out
