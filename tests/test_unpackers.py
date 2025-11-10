from __future__ import annotations

import inspect
import typing

import pytest
from pydantic import BaseModel, Field

from funcnodes_pydantic.unpackers import PydanticUnpacker


class ChildModel(BaseModel):
    code: int = Field(100, description="Child code", ge=0, le=999)


class ParentModel(BaseModel):
    name: str = Field(..., description="Name field")
    child: ChildModel
    tags: list[str] = Field(default_factory=list, description="Optional tags")


class ResponseModel(BaseModel):
    status: str = Field(..., description="Status text")
    value: str = Field(..., description="Payload value")


def _extract_meta(annotation):
    origin = typing.get_origin(annotation)
    assert origin is typing.Annotated
    base, meta = typing.get_args(annotation)
    return base, meta


def test_signature_flatten_top_level():
    @PydanticUnpacker()
    def process(payload: ParentModel) -> str:  # pragma: no cover - inspected only
        return payload.name

    sig = inspect.signature(process)
    assert tuple(sig.parameters) == ("payload_name", "payload_child", "payload_tags")

    hints = typing.get_type_hints(process, include_extras=True)
    child_ann = hints["payload_child"]
    base, meta = _extract_meta(child_ann)
    assert base is ChildModel
    assert meta["name"] == "payload.child"
    assert meta["description"] == ""  # no description provided on model


def test_nested_flatten_levels():
    @PydanticUnpacker(input_levels=2)
    def process(payload: ParentModel) -> str:
        return payload.child.code + len(payload.tags)

    sig = inspect.signature(process)
    assert tuple(sig.parameters) == (
        "payload_name",
        "payload_child_code",
        "payload_tags",
    )

    hints = typing.get_type_hints(process, include_extras=True)
    code_ann = hints["payload_child_code"]
    base, meta = _extract_meta(code_ann)
    assert base is int
    assert meta["description"] == "Child code"
    assert meta["value_options"]["min"] == 0
    assert meta["value_options"]["max"] == 999


def test_rehydration_and_output_flatten():
    calls: list[ParentModel] = []

    @PydanticUnpacker(input_levels=2, output_levels=1)
    def run(payload: ParentModel) -> ResponseModel:
        calls.append(payload)
        return ResponseModel(status="done", value=str(payload.child.code))

    result = run(
        payload_name="Demo",
        payload_child_code=321,
        payload_tags=["a"],
    )

    assert calls and isinstance(calls[0], ParentModel)
    assert calls[0].child.code == 321
    assert result == ("done", "321")


def test_default_factory_preserved():
    captured: list[list[str]] = []

    @PydanticUnpacker(input_levels=1)
    def collect(payload: ParentModel) -> list[str]:
        captured.append(payload.tags)
        payload.tags.append("x")
        return payload.tags

    first = collect(payload_name="A", payload_child=ChildModel(code=5))
    second = collect(payload_name="B", payload_child=ChildModel(code=6))

    assert captured[0] == ["x"]
    assert captured[1] == ["x"]
    assert captured[0] is not captured[1]
    assert first == ["x"]
    assert second == ["x"]


def test_variadic_base_model_rejected():
    with pytest.raises(TypeError):

        @PydanticUnpacker()
        def broken(*payload: ParentModel):  # pragma: no cover - definition should fail
            return payload
