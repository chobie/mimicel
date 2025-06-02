# --- 基底クラスとヘルパー ---
from datetime import timedelta, datetime
from typing import Any, MutableMapping, MutableSequence

from google.protobuf.duration_pb2 import Duration
from google.protobuf.message import Message
from google.protobuf.struct_pb2 import Value, Struct, ListValue
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import Int32Value, UInt32Value, Int64Value, UInt64Value, DoubleValue, BoolValue, \
    BytesValue, FloatValue, StringValue
from google.protobuf.any_pb2 import Any as PbAny

from .base import CelValue
from .base import (
    _check_int64_range,
    _check_uint64_range,
    _check_timestamp_range,
    _check_duration_operation_result
)

# --- 定数 ---
from .constants import (
    INT64_MAX, INT64_MIN, UINT64_MAX,
    TIMESTAMP_MIN_DATETIME, TIMESTAMP_MAX_DATETIME
)
from .errors import CelErrorValue

# --- プリミティブ型 ---
from .primitives import (
    CelInt, CelUInt, CelDouble,
    CelString, CelBytes,
    CelBool, CelNull
)

# --- 複合型 ---
from .composites import CelList, CelMap, CelStruct

# --- Well-Known Types ---
from .well_known_types import (
    CelTimestamp, CelDuration,
    CelProtobufInt32Value, CelProtobufValue, CelProtobufUInt32Value, CelProtobufInt64Value, CelProtobufUInt64Value,
    CelProtobufDoubleValue, CelProtobufStruct, CelProtobufListValue, CelWrappedProtoMessage, CelProtobufBoolValue,
    CelProtobufBytesValue, CelProtobufFloatValue, CelProtobufStringValue, CelProtobufAny, CelProtobufTimestamp,
    CelProtobufDuration
    # 今後追加するWKTラッパーもここに
)
from .cel_types import CEL_VALUE_WRAPPER, ParameterizedCelType, _LIST_BASE_TYPE, _MAP_BASE_TYPE, CelType, CelDynValue

try:
    from google._upb._message import RepeatedScalarContainer, RepeatedCompositeContainer
    _UPB_CONTAINERS_LOADED = True
except ImportError:
    _UPB_CONTAINERS_LOADED = False
    RepeatedScalarContainer, RepeatedCompositeContainer = None, None # ダミー定義


def wrap_value(v: Any) -> 'CelValue':
    if isinstance(v, PbAny):
        return CelProtobufAny(v)
    if isinstance(v, CelValue):
        return v
    if isinstance(v, ListValue):
        return CelProtobufListValue(v)
    if isinstance(v, bool):
        return CelBool(v)
    if isinstance(v, Struct):
        return CelProtobufStruct(v)
    if isinstance(v, int):
        return CelInt(v)
    if isinstance(v, float):
        return CelDouble(v)
    if isinstance(v, str):
        return CelString(v)
    if isinstance(v, bytes):
        return CelBytes(v)
    if v is None:
        return CelNull()
    if isinstance(v, Timestamp):
        return CelProtobufTimestamp(v)
    if isinstance(v, Duration):
        return CelProtobufDuration(v)
    if isinstance(v, Value):
        return CelProtobufValue(v)
    if isinstance(v, list):
        return CelList([wrap_value(elem) for elem in v])
    if isinstance(v, Int32Value):
        return CelProtobufInt32Value(v)
    if isinstance(v, UInt32Value):
        return CelProtobufUInt32Value(v)
    if isinstance(v, Int64Value):
        return CelProtobufInt64Value(v)
    if isinstance(v, UInt64Value):
        return CelProtobufUInt64Value(v)
    if isinstance(v, FloatValue):
        return CelProtobufFloatValue(v)
    if isinstance(v, DoubleValue):
        return CelProtobufDoubleValue(v)
    if isinstance(v, BoolValue):
        return CelProtobufBoolValue(v)
    if isinstance(v, BytesValue):
        return CelProtobufBytesValue(v)
    if isinstance(v, StringValue):
        return CelProtobufStringValue(v)

    if _UPB_CONTAINERS_LOADED:
        if isinstance(v, (RepeatedScalarContainer, RepeatedCompositeContainer)):
            return CelList([wrap_value(elem) for elem in v])

    if isinstance(v, dict):
        # マップのキーはCELで許可された型のみ
        wrapped_dict = {}
        for k_raw, v_raw in v.items():
            # ここでキーの型チェックとラップを行うべきだが、現状はCelMapコンストラクタに委ねている
            # CelMapコンストラクタでキーのラップが行われる想定
            wrapped_dict[wrap_value(k_raw)] = wrap_value(v_raw)
        return CelMap(wrapped_dict)

    if isinstance(v, datetime):
        # datetimeオブジェクトは aware であることを期待 (UTCが望ましい)
        # naiveな場合はUTCとみなすか、エラーにするか設計による。
        # CelTimestampコンストラクタで処理。
        return CelTimestamp(v)
    if isinstance(v, timedelta):
        return CelDuration(v)

    # --- Generic ProtobufMessage (上記WKT以外) ---
    from google.protobuf.message import Message as ProtobufMessage
    if isinstance(v, ProtobufMessage):
        return CelWrappedProtoMessage(v)

    # 不明な型はそのまま返すか、エラーとするか、CelDynでラップするか。
    # ここでは、現状の実装に合わせてそのまま返す。
    # print(f"Warning: wrap_value received an unknown type ({type(v)}). Returning as is.")
    return v


def unwrap_value(v: Any) -> Any:
    if isinstance(v, CelErrorValue):
        # Conformance test の "foo" パターンのような一般的なエラーメッセージを期待する場合、
        # CelErrorValue のメッセージをそのまま使うのが適切。
        raise RuntimeError(v.message)

    if isinstance(v, CelDynValue):
        return v.value

    if isinstance(v, CelProtobufDuration):
        return v._pb_value
    if isinstance(v, CelProtobufTimestamp):
        return v._pb_value

    if isinstance(v, CelProtobufAny):
        return v._pb_any

    if isinstance(v, CelWrappedProtoMessage):
        return v.pb_message

    if isinstance(v, ParameterizedCelType):
        if v.base_type == _LIST_BASE_TYPE:
            return "list"
        elif v.base_type == _MAP_BASE_TYPE:
            return "map"
        return v.name
    elif isinstance(v, CelType):
        return v.name

    # --- ここからコレクション型とProtobufコンテナ型の処理 ---
    # まず、vがCelList, CelMap, CelWrappedProtoMessageの場合、ペイロードを取り出す
    payload = None
    is_cel_list_wrapper = False
    is_cel_map_wrapper = False

    if isinstance(v, CelList):
        payload = getattr(v, 'elements', getattr(v, 'value', None))  # .elements or .value
        is_cel_list_wrapper = True
    elif isinstance(v, CelMap):
        payload = v.value  # CelMapは .value に内部マップを持つと仮定
        is_cel_map_wrapper = True
    elif isinstance(v, CelWrappedProtoMessage):
        payload = getattr(v, 'value', getattr(v, 'pb_message', None))  # .value or .pb_message
    else:
        payload = v  # v が直接コンテナ型である場合

    # --- Protobuf List-like Container (RepeatedScalarContainerなど) の処理 ---
    if isinstance(payload, MutableSequence) and not isinstance(payload, (list, str, bytes)):
        # str, bytes も MutableSequence のサブクラスなので除外
        # payload が Protobuf の repeated フィールドコンテナの場合
        py_list = []
        for elem_from_container in payload:
            if isinstance(elem_from_container, Message):
                # 要素が Protobuf Message なら、wrap->unwrapで再帰処理
                py_list.append(unwrap_value(wrap_value(elem_from_container)))
            else:
                # 要素がスカラーならそのまま (Pythonプリミティブのはず)
                py_list.append(elem_from_container)
        return py_list
    elif is_cel_list_wrapper and isinstance(payload, list):  # CelList が Python list(of CelValue) をラップ
        return [unwrap_value(elem) for elem in payload]

    # --- Protobuf Map-like Container (ScalarMapContainerなど) の処理 ---
    if isinstance(payload, MutableMapping) and not isinstance(payload, dict):
        # payload が Protobuf の map フィールドコンテナの場合
        py_dict = {}
        for k_raw, v_raw in payload.items():  # k_raw は Python プリミティブのはず
            key_py = k_raw  # Protobuf map keys are already Python primitives
            val_py = None

            # v_raw の型に応じてアンラップ (ここは前回のマップ処理ロジックを流用・改良)
            if isinstance(v_raw, StringValue):
                val_py = v_raw.value
            elif isinstance(v_raw, (Int32Value, Int64Value, UInt32Value, UInt64Value,
                                    FloatValue, DoubleValue, BoolValue)):
                val_py = v_raw.value
            elif isinstance(v_raw, BytesValue):
                val_py = v_raw.value
            elif isinstance(v_raw, Message):  # 上記以外の WKT やカスタムメッセージ
                val_py = unwrap_value(wrap_value(v_raw))  # 再帰的に処理
            else:  # Python プリミティブ
                val_py = v_raw
            py_dict[key_py] = val_py
        return py_dict
    elif is_cel_map_wrapper and isinstance(payload, dict):  # CelMap が Python dict(of CelValue) をラップ
        py_dict = {}
        for k_cel, v_cel in payload.items():
            py_dict[unwrap_value(k_cel)] = unwrap_value(v_cel)
        return py_dict


    if isinstance(v, CelProtobufStruct):
        return v.value
    if isinstance(v, CelProtobufListValue):
        return [unwrap_value(elem) for elem in v]
    if isinstance(v, CelList):
        return [unwrap_value(elem) for elem in v.elements]
    if isinstance(v, CelMap):
        return {unwrap_value(k): unwrap_value(val) for k, val in v.items()}
    if isinstance(v, (CelTimestamp, CelDuration)):
        return v.value
    if isinstance(v, CelStruct):
        return {key: unwrap_value(field_val) for key, field_val in v.fields.items()}
    if isinstance(v, CelValue):
        if hasattr(v, 'value'):
            return v.value
        return v
    if isinstance(v, CelProtobufValue):
        return v._pb_value
    # if isinstance(v, CelProtobufInt32Value):
    #     return v._pb_value
    # if isinstance(v, CelProtobufUInt32Value):
    #     return v._pb_value
    # if isinstance(v, CelProtobufInt64Value):
    #     return v._pb_value
    # if isinstance(v, CelProtobufUInt64Value):
    #     return v._pb_value

    return v
