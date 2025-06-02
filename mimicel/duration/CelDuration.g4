// CelDuration.g4
grammar CelDuration;

parse: duration_input EOF;

duration_input
    : sign? component (component)* | sign? zero_value_with_optional_s // "0", "0s", "0.0s", BUT ALSO "1s", "1.2s"
    ;                                  // This rule might be too broad, or needs careful handling in Visitor

component: amount unit;
amount: DECIMAL | INT;

// 'zero_value_with_optional_s' is intended for "0", "0s", or a single component with 's' unit.
// Non-zero without 's' should be an error.
// This rule name might be misleading if it can parse "123s".
// Better: single_component_or_zero
zero_value_with_optional_s
    : amount SECONDS?
    ;

unit: HOURS | MINUTES | SECONDS | MILLIS | MICROS | NANOS;
sign: PLUS | MINUS;

HOURS   : 'h';
MINUTES : 'm';
SECONDS : 's';
MILLIS  : 'ms';
MICROS  : 'us' | 'µs';
NANOS   : 'ns';

PLUS    : '+';
MINUS   : '-';

// DECIMAL: Requires digits after decimal point if decimal point exists.
// Or must have an exponent.
DECIMAL
    : DIGIT+ '.' DIGIT+ EXPONENT?  // 1.23, 1.0 (not 1.)
    | '.' DIGIT+ EXPONENT?         // .5
    | DIGIT+ EXPONENT              // 1e3 (INT followed by E)
    ;
INT     : DIGIT+ ; // 123, 0

fragment DIGIT    : [0-9];
fragment EXPONENT : ('e'|'E') ('+'|'-')? DIGIT+;

WS      : [ \t\r\n]+ -> skip;