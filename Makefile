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
	bazel test //tests/legacy:all