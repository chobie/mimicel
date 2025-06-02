import pytest
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_EVEN  # テストケースの期待値計算用
# from mimicel.duration import parse_duration # 実際のインポートパスに合わせる
from mimicel.duration import parse_duration
from mimicel.duration.duration_visitor import UNIT_TO_NANOS



# Helper to calculate expected microseconds using ROUND_HALF_EVEN for testing
def expected_micros_round_half_even(nanos_val: float) -> int:
    if nanos_val == 0: return 0
    # Use Decimal for precise rounding similar to Python 3's round()
    # Convert nanos to micros
    micros_decimal = Decimal(str(nanos_val)) / Decimal('1000')
    # Round to nearest even for .5 cases
    rounded_micros = micros_decimal.quantize(Decimal('0'), rounding=ROUND_HALF_EVEN)
    return int(rounded_micros)


#@pytest.mark.parametrize("duration_str, expected_total_micros", [
    # Basic units
    #("1h", 3600 * 1_000_000),
    #("2m", 2 * 60 * 1_000_000),
    #("3s", 3 * 1_000_000),
    #("4ms", 4 * 1_000),
    #("5us", 5),
    #("6ns", expected_micros_round_half_even(6)),  # 0.006µs -> 0µs
    #("1000ns", expected_micros_round_half_even(1000)),  # 1.0µs -> 1µs
    #("1999ns", expected_micros_round_half_even(1999)),  # 1.999µs -> 2µs
    #("2000ns", expected_micros_round_half_even(2000)),  # 2.0µs -> 2µs

    # Zero values (これらの期待値は変わらない)
    #("0", 0),
    #("0s", 0),
    #("0.0s", 0),

    # Negative values
    #("-1h", -3600 * 1_000_000),
    #("-6ns", expected_micros_round_half_even(-6)),  # -0.006µs -> 0µs

    # Fractional values
    #("1.5h", expected_micros_round_half_even(1.5 * UNIT_TO_NANOS['h'])),
    #("5.5us", expected_micros_round_half_even(5.5 * UNIT_TO_NANOS['us'])),  # 5.5µs -> 6µs
    #("0.0000005s", expected_micros_round_half_even(0.0000005 * UNIT_TO_NANOS['s'])),  # 0.5µs -> 0µs
    #("0.5us", expected_micros_round_half_even(0.5 * UNIT_TO_NANOS['us'])),  # 0.5µs -> 0µs
    #("0.9us", expected_micros_round_half_even(0.9 * UNIT_TO_NANOS['us'])),  # 0.9µs -> 1µs
    #("1.9us", expected_micros_round_half_even(1.9 * UNIT_TO_NANOS['us'])),  # 1.9µs -> 2µs

    # Compound values
    #("1us500ns", expected_micros_round_half_even(1 * UNIT_TO_NANOS['us'] + 500 * UNIT_TO_NANOS['ns'])),  # 1.5µs -> 2µs
    #("1h0m0.000000001s", expected_micros_round_half_even(1 * UNIT_TO_NANOS['h'] + 1e-9 * UNIT_TO_NANOS['s'])),
    # 1h + 1ns -> 1h (1ns rounds to 0µs)

    # Values requiring careful float arithmetic and timedelta conversion
    #("1.2345678s", expected_micros_round_half_even(1.2345678 * UNIT_TO_NANOS['s'])),  # 1s + 234567.8µs -> 1s + 234568µs
    #("1.234567ms", expected_micros_round_half_even(1.234567 * UNIT_TO_NANOS['ms'])),  # 1234.567µs -> 1235µs
    #("1.234us", expected_micros_round_half_even(1.234 * UNIT_TO_NANOS['us'])),  # 1.234µs -> 1µs

    # Scientific notation
    #("1.5e-6s", expected_micros_round_half_even(1.5e-6 * UNIT_TO_NANOS['s'])),  # 1.5µs -> 2µs

    # 0.000000001h = 3.6µs -> round_half_even(3.6) -> 4µs
    #("0.000000001h", expected_micros_round_half_even(0.000000001 * UNIT_TO_NANOS['h'])),
#])
#def test_parse_duration_valid_cases(duration_str, expected_total_micros):
#    expected_timedelta = timedelta(microseconds=expected_total_micros)
#    assert parse_duration(duration_str) == expected_timedelta

# test_duration_fractional_seconds_to_microseconds も同様に期待値を修正
# def test_duration_fractional_seconds_to_microseconds():
#     assert parse_duration("0.5us") == timedelta(microseconds=expected_micros_round_half_even(0.5 * UNIT_TO_NANOS['us']))  # 0µs
#     assert parse_duration("0.999us") == timedelta(microseconds=expected_micros_round_half_even(0.999 * UNIT_TO_NANOS['us'])) # 1µs
#     assert parse_duration("1.999us") == timedelta(microseconds=expected_micros_round_half_even(1.999 * UNIT_TO_NANOS['us'])) # 2µs
#     assert parse_duration("0.0000005s") == timedelta(microseconds=expected_micros_round_half_even(0.0000005 * UNIT_TO_NANOS['s'])) # 0µs

# test_duration_all_units も同様に期待値を修正
# def test_duration_all_units():
#     # 1h1m1s1ms1us1ns -> 3661001001001 ns -> 3661001001.001 µs -> round -> 3661001001 µs
#     nanos_val = (1*UNIT_TO_NANOS['h'] + 1*UNIT_TO_NANOS['m'] + 1*UNIT_TO_NANOS['s'] +
#                  1*UNIT_TO_NANOS['ms'] + 1*UNIT_TO_NANOS['us'] + 1*UNIT_TO_NANOS['ns'])
#     assert parse_duration("1h1m1s1ms1us1ns") == timedelta(microseconds=expected_micros_round_half_even(nanos_val))
#
#     # 1h1m1s1ms1us500ns -> 1.5µs for last part -> round(X.5) to nearest even.
#     # 1h1m1s1ms0us + 1us + 500ns = 3661001000000ns + 1000ns + 500ns = 3661001001500 ns
#     # 3661001001.5 µs -> round_half_even -> 3661001002 µs
#     nanos_val_complex = (1*UNIT_TO_NANOS['h'] + 1*UNIT_TO_NANOS['m'] + 1*UNIT_TO_NANOS['s'] +
#                          1*UNIT_TO_NANOS['ms'] + 1*UNIT_TO_NANOS['us'] + 500*UNIT_TO_NANOS['ns'])
#     assert parse_duration("1h1m1s1ms1us500ns") == timedelta(microseconds=expected_micros_round_half_even(nanos_val_complex))
#
#     nanos_val_neg_complex = -nanos_val_complex
#     assert parse_duration("-1h1m1s1ms1us500ns") == timedelta(microseconds=expected_micros_round_half_even(nanos_val_neg_complex))