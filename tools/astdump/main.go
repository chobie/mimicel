package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/google/cel-go/cel"
	"google.golang.org/protobuf/encoding/protojson"
)

func main() {
	var expression string
	var outputFile string

	flag.StringVar(&expression, "expr", "", "CEL expression to evaluate")
	flag.StringVar(&outputFile, "output", "ast.json", "Output file for AST in JSON format")
	flag.Parse()

	if expression == "" {
		fmt.Fprintf(os.Stderr, "Error: expression is required\n")
		fmt.Fprintf(os.Stderr, "Usage: %s -expr \"<expression>\" [-output <file>]\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "Example: %s -expr \"1 + 1\"\n", os.Args[0])
		os.Exit(1)
	}

	// Create CEL environment
	env, err := cel.NewEnv(
		cel.StdLib(),
		cel.Variable("x", cel.IntType),
		cel.Variable("y", cel.StringType),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating CEL environment: %v\n", err)
		os.Exit(1)
	}

	// Parse the expression
	ast, issues := env.Parse(expression)
	if issues != nil && issues.Err() != nil {
		fmt.Fprintf(os.Stderr, "Error parsing expression: %v\n", issues.Err())
		os.Exit(1)
	}

	// Type-check the expression
	checked, issues := env.Check(ast)
	if issues != nil && issues.Err() != nil {
		fmt.Fprintf(os.Stderr, "Error type-checking expression: %v\n", issues.Err())
		os.Exit(1)
	}

	// Convert AST to protobuf format and then to JSON
	parsedExpr := ast.Expr()
	checkedExpr := checked.Expr()

	// Create a combined output with both parsed and checked expressions
	output := map[string]interface{}{
		"expression": expression,
		"parsed":     nil,
		"checked":    nil,
	}

	// Convert parsed expression to JSON
	if parsedJSON, err := protojson.Marshal(parsedExpr); err == nil {
		var parsedMap map[string]interface{}
		if err := json.Unmarshal(parsedJSON, &parsedMap); err == nil {
			output["parsed"] = parsedMap
		}
	}

	// Convert checked expression to JSON  
	if checkedJSON, err := protojson.Marshal(checkedExpr); err == nil {
		var checkedMap map[string]interface{}
		if err := json.Unmarshal(checkedJSON, &checkedMap); err == nil {
			output["checked"] = checkedMap
		}
	}

	// Write AST to file
	file, err := os.Create(outputFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating output file: %v\n", err)
		os.Exit(1)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(output); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing AST to file: %v\n", err)
		os.Exit(1)
	}

	// Create program from AST
	prg, err := env.Program(checked)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating program: %v\n", err)
		os.Exit(1)
	}

	// Evaluate the expression with sample values
	vars := map[string]interface{}{
		"x": int64(10),
		"y": "hello",
	}

	result, _, err := prg.Eval(vars)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error evaluating expression: %v\n", err)
		os.Exit(1)
	}

	// Output result to console
	fmt.Printf("Expression: %s\n", expression)
	fmt.Printf("Result: %v (type: %s)\n", result.Value(), result.Type())
	fmt.Printf("AST written to: %s\n", outputFile)
}