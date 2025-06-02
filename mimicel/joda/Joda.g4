grammar Joda;

timeZone
    : UTC_KEYWORD
    | longTZ
    | fixedTZ
    ;

longTZ
    : LONG_TZ_IDENTIFIER
    ;

fixedTZ
    : (PLUS | MINUS) DIGIT DIGIT COLON DIGIT DIGIT
    ;

UTC_KEYWORD : 'UTC';

LONG_TZ_IDENTIFIER : [a-zA-Z_] [a-zA-Z0-9_/.+-]* ;

PLUS    : '+';
MINUS   : '-';
COLON   : ':';
DIGIT   : [0-9]; // '0'..'9' と同じ

WS      : [ \t\r\n]+ -> skip;