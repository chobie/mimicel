class UnescapeError(ValueError):
    """Custom exception for unescaping errors."""
    pass


def _unhex(b_char_code: int) -> tuple[int, bool]:
    """
    Converts a hex character code to its integer value.
    Corresponds to Go's unhex.
    """
    if ord('0') <= b_char_code <= ord('9'):
        return b_char_code - ord('0'), True
    if ord('a') <= b_char_code <= ord('f'):
        return b_char_code - ord('a') + 10, True
    if ord('A') <= b_char_code <= ord('F'):
        return b_char_code - ord('A') + 10, True
    return 0, False

def _unescape_char(s: str, is_bytes: bool) -> tuple[int, bool, str, UnescapeError | None]:
    if not s:
        return 0, False, "", UnescapeError("Cannot unescape empty string")

    # 1. Character is not an escape sequence.
    char_code = ord(s[0])
    if char_code >= 0x80:  # UTF-8 character (RuneSelf in Go)
        # Python strings handle unicode transparently.
        # We need to simulate Go's utf8.DecodeRuneInString behavior slightly.
        # For simplicity, we assume Python's string slicing handles UTF-8 correctly.
        return char_code, True, s[1:], None
    if s[0] != '\\':
        return char_code, False, s[1:], None

    # 2. Last character is the start of an escape sequence.
    if len(s) <= 1:
        return 0, False, "", UnescapeError("Unable to unescape string, found '\\' as last character")

    c = s[1]
    s_rest = s[2:]
    value: int = 0
    encode_as_utf8: bool = False  # Default for simple escapes

    # 3. Common escape sequences shared with Google SQL
    if c == 'a':
        value = ord('\a')
    elif c == 'b':
        value = ord('\b')
    elif c == 'f':
        value = ord('\f')
    elif c == 'n':
        value = ord('\n')
    elif c == 'r':
        value = ord('\r')
    elif c == 't':
        value = ord('\t')
    elif c == 'v':
        value = ord('\v')
    elif c == '\\':
        value = ord('\\')
    elif c == '\'':
        value = ord('\'')
    elif c == '"':
        value = ord('"')
    elif c == '`':
        value = ord('`')
    elif c == '?':
        value = ord('?')
    # 4. Unicode escape sequences
    elif c in ('x', 'X', 'u', 'U'):
        n = 0
        encode_as_utf8 = True  # Potentially a multi-byte char if not is_bytes
        if c == 'x' or c == 'X':
            n = 2
            if is_bytes:  # \x can be a byte
                encode_as_utf8 = False
        elif c == 'u':
            n = 4
            if is_bytes:
                return 0, False, "", UnescapeError("Cannot use \\u escape in bytes literal")
        elif c == 'U':
            n = 8
            if is_bytes:
                return 0, False, "", UnescapeError("Cannot use \\U escape in bytes literal")

        if len(s_rest) < n:
            return 0, False, "", UnescapeError(f"Invalid escape sequence \\{c}: not enough digits")

        v_hex = 0
        for i in range(n):
            digit_val, ok = _unhex(ord(s_rest[i]))
            if not ok:
                return 0, False, "", UnescapeError(f"Invalid hex digit in \\{c} escape sequence")
            v_hex = (v_hex << 4) | digit_val
        s_rest = s_rest[n:]
        value = v_hex

        if not is_bytes:
            try:
                chr(value)  # Check if it's a valid Unicode code point
            except ValueError:
                return 0, False, "", UnescapeError(f"Invalid Unicode code point: \\{c}{hex(value)[2:]}")
        elif value > 0xFF:  # for \x in bytes
            return 0, False, "", UnescapeError(f"Escape sequence \\{c} out of range for bytes")


    # 5. Octal escape sequences, must be three digits \[0-3][0-7][0-7]
    elif '0' <= c <= '3':
        if len(s_rest) < 2:  # Need two more digits
            return 0, False, "", UnescapeError("Unable to unescape octal sequence: not enough digits")

        v_oct = int(c, 8)
        for i in range(2):
            oct_char = s_rest[i]
            if not ('0' <= oct_char <= '7'):
                return 0, False, "", UnescapeError("Invalid char in octal sequence")
            v_oct = (v_oct * 8) + int(oct_char, 8)

        if v_oct > 0o377 and is_bytes:  # Max for a byte is 0o377 (255)
            return 0, False, "", UnescapeError("Octal escape value out of range for byte")

        value = v_oct
        s_rest = s_rest[2:]
        if is_bytes:
            encode_as_utf8 = False
        else:
            encode_as_utf8 = True  # Octal can represent unicode codepoints
            try:
                chr(value)  # Check if it's a valid Unicode code point
            except ValueError:
                return 0, False, "", UnescapeError(f"Invalid Unicode code point from octal: \\{oct(value)[2:]}")

    # Unknown escape sequence.
    else:
        return 0, False, "", UnescapeError(f"Unknown escape sequence: \\{c}")

    return value, encode_as_utf8, s_rest, None


def unescape(value: str, is_bytes: bool) -> str | bytes:
    """
    Unescapes a quoted string.
    Corresponds to Go's unescape.
    This function performs escaping compatible with GoogleSQL.
    """
    # All strings normalize newlines to the \n representation.
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    n = len(value)

    # Nothing to unescape / decode.
    if n < 2:
        # Go returns (value, errors.New("unable to unescape string"))
        # Pythonic way is to raise an error if it's truly an unrecoverable state for "unquoting"
        # However, if the original Go code proceeds with 'value', we might reconsider.
        # For CEL, an unquoted string that's too short is likely an invalid literal.
        raise UnescapeError("Unable to unescape string: too short")

    # Raw string preceded by the 'r|R' prefix.
    is_raw_literal = False
    if value[0] == 'r' or value[0] == 'R':
        value = value[1:]
        n = len(value)
        is_raw_literal = True
        if n < 2:  # e.g. r" or r'
            raise UnescapeError("Unable to unescape raw string: too short after prefix")

    # Quoted string of some form, must have same first and last char.
    if value[0] != value[n - 1] or (value[0] != '"' and value[0] != '\''):
        raise UnescapeError("Unable to unescape string: mismatched or invalid quotes")

    # Normalize the multi-line CEL string representation
    if n >= 6:
        if value.startswith("'''") and value.endswith("'''"):
            value = "\"" + value[3:n - 3] + "\""
        elif value.startswith('"""') and value.endswith('"""'):
            value = "\"" + value[3:n - 3] + "\""
        n = len(value)  # Recalculate n after potential normalization

    # Remove outer quotes
    value_inner = value[1: n - 1]

    # If there is nothing to escape, then return.
    if is_raw_literal or '\\' not in value_inner:
        if is_bytes:
            # For raw bytes, we need to ensure the string content is ASCII or handle encoding.
            # CEL spec for bytes implies the content of a raw string would be taken literally.
            # If the original Go unescape for raw strings doesn't do further processing,
            # then we assume value_inner is the content.
            try:
                return value_inner.encode('utf-8')  # Or 'ascii' if strictly for byte values
            except UnicodeEncodeError as e:
                raise UnescapeError(f"Cannot encode raw string to bytes: {e}")
        return value_inner

    # Otherwise the string contains escape characters.
    # The following logic is adapted from `strconv/quote.go`

    result_parts = []  # For string
    byte_result = bytearray()  # For bytes

    current_str = value_inner
    while current_str:
        char_val, encode_utf8, rest, err = _unescape_char(current_str, is_bytes)
        if err:
            raise err

        current_str = rest

        if is_bytes:
            if char_val > 0xFF:
                # This case should ideally be caught by _unescape_char for \u, \U if is_bytes
                # or for octal/hex escapes that result in a value > 255
                raise UnescapeError(f"Escaped character value {char_val} out of range for byte")
            byte_result.append(char_val)
        else:
            if encode_utf8 or char_val >= 0x80:  # Needs unicode handling
                result_parts.append(chr(char_val))
            else:  # Simple ASCII char
                result_parts.append(chr(char_val))

    if is_bytes:
        return bytes(byte_result)
    else:
        return "".join(result_parts)


def unquote(value: str, is_bytes: bool = False) -> str | bytes:
    """
    Python equivalent of the Go parser's unquote method.
    It calls unescape and handles errors by raising them.
    The 'ctx' and 'reportError' from Go are handled by Python's exception mechanism.
    """
    try:
        return unescape(value, is_bytes)
    except UnescapeError as e:
        # In a real parser, you might log this or handle it based on 'ctx'.
        # For this standalone function, re-raising or returning the original value
        # (as in the Go example's error case) are options.
        # Raising the error is more Pythonic for indicating a failure.
        # If the Go `p.reportError` doesn't stop processing and returns `value`,
        # then a try-except returning `value` would be closer.
        # Given the Go `unquote`'s structure, it seems `reportError` logs but
        # the function still returns the original erroneous `value`.
        # Let's match that behavior for the top-level `unquote` if an error occurs.
        # However, the prompt asks for a "complete code" which implies robustness,
        # and just returning the original string on error can hide issues.
        # For now, let's make `unquote` simpler and let `unescape` raise.
        # If the specific behavior of `reportError` (log and return original) is critical,
        # the caller of this python `unquote` would do:
        # try:
        #   result = unquote(...)
        # except UnescapeError:
        #   log_error()
        #   result = original_value
        raise  # Re-raise the specific UnescapeError