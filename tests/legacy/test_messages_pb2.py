# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: test_messages.proto
# Protobuf Python Version: 6.30.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    30,
    2,
    '',
    'test_messages.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13test_messages.proto\x12\ttestproto\"o\n\x11SimpleTestMessage\x12\x14\n\x0cstring_field\x18\x01 \x01(\t\x12\x11\n\tint_field\x18\x02 \x01(\x03\x12\x12\n\nbool_field\x18\x03 \x01(\x08\x12\x1d\n\x15repeated_string_field\x18\x04 \x03(\t\"^\n\x11NestedTestMessage\x12\x34\n\x0esimple_message\x18\x01 \x01(\x0b\x32\x1c.testproto.SimpleTestMessage\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\",\n\x0f\x45qualityMessage\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x0b\n\x03\x61ge\x18\x02 \x01(\x03\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'test_messages_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_SIMPLETESTMESSAGE']._serialized_start=34
  _globals['_SIMPLETESTMESSAGE']._serialized_end=145
  _globals['_NESTEDTESTMESSAGE']._serialized_start=147
  _globals['_NESTEDTESTMESSAGE']._serialized_end=241
  _globals['_EQUALITYMESSAGE']._serialized_start=243
  _globals['_EQUALITYMESSAGE']._serialized_end=287
# @@protoc_insertion_point(module_scope)
