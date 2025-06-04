.PHONY: clean
clean:
	rm -rf dist

.PHONY: package
package:
	mkdir dist
	bazel build //:mimicel_wheel
	cp bazel-bin/mimicel-*.whl dist

.PHONY: conformance
conformance:
	bazel run //conformance:run_basic_test

.PHONY: simple
simple:
	bazel run //examples:simple

.PHONY: test
test:
	bazel test //tests/legacy:all //tests:test_reserved_words

# ANTLR code generation for local development
ANTLR_JAR := third_party/antlr4/antlr-4.13.2-complete.jar
ANTLR := java -cp $(ANTLR_JAR) org.antlr.v4.Tool

.PHONY: antlr
antlr: antlr-cel antlr-duration antlr-joda

.PHONY: antlr-cel
antlr-cel:
	$(ANTLR) -Dlanguage=Python3 -visitor -no-listener mimicel/CEL.g4

.PHONY: antlr-duration
antlr-duration:
	$(ANTLR) -Dlanguage=Python3 -visitor -no-listener mimicel/duration/CelDuration.g4

.PHONY: antlr-joda
antlr-joda:
	$(ANTLR) -Dlanguage=Python3 -visitor -no-listener mimicel/joda/Joda.g4

.PHONY: clean-antlr
clean-antlr:
	rm -f mimicel/CELLexer.py mimicel/CELParser.py mimicel/CELVisitor.py
	rm -f mimicel/duration/CelDurationLexer.py mimicel/duration/CelDurationParser.py mimicel/duration/CelDurationVisitor.py
	rm -f mimicel/joda/JodaLexer.py mimicel/joda/JodaParser.py mimicel/joda/JodaVisitor.py