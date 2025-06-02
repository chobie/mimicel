import ast
from typing import Optional

from cel.expr import syntax_pb2

from .CELVisitor import CELVisitor
from .CELParser import CELParser
from .literal_registry_pb import LITERAL_CONSTRUCTORS_PB
from .macro_registry_pb import MACRO_DISPATCH_PB
from .unquote import UnescapeError, unquote

INT64_MAX = 2**63 - 1  # 9223372036854775807
UINT64_MAX = 2**64 - 1
INT64_MIN_ABS_VALUE = 2**63  # 9223372036854775808 (int64最小値の絶対値)
INT64_MIN = -2**63     # -9223372036854775808


class CelASTBuilder(CELVisitor):
    def __init__(self):
        self.id_counter = 0

    def _next_id(self, ctx=None):
        self.id_counter += 1
        return self.id_counter


    # unary ルールに対応
    def visitMemberExpr(self, ctx: CELParser.MemberExprContext): # unary #MemberExpr
        # method_name = "visitMemberExpr"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: member #MemberExpr (unaryルールの一部)
        # ctx は MemberExprContext (UnaryContextのサブクラス)
        result = self.visit(ctx.member())
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitMemberCall(self, ctx: CELParser.MemberCallContext):
        target_expr = self.visit(ctx.member())
        method_name = ctx.IDENTIFIER().getText()

        args_expr_list: list[syntax_pb2.Expr] = []
        if ctx.exprList():
            for arg_expr_ctx in ctx.exprList().expr():
                args_expr_list.append(self.visit(arg_expr_ctx))

        expr_id = self._next_id(ctx)

        if method_name in MACRO_DISPATCH_PB:
            macro_expander = MACRO_DISPATCH_PB[method_name]

            if method_name in ["all", "exists", "exists_one", "filter"]:  # ★ "filter" を追加
                expected_args = 2
                if len(args_expr_list) != expected_args:
                    raise ValueError(
                        f"Macro '{method_name}' on target expects {expected_args} arguments "
                        f"(iterator variable name, predicate/transform expression), "
                        f"got {len(args_expr_list)} for '{ctx.getText()}'"
                    )

                iter_var_arg = args_expr_list[0]
                second_arg_expr = args_expr_list[1]  # predicate or transform

                if not iter_var_arg.HasField("ident_expr"):
                    raise ValueError(
                        f"The first argument to '{method_name}' macro must be an identifier "
                        f"(iterator variable name), got {iter_var_arg.WhichOneof('expr_kind')}"
                    )
                iter_var_name_str = iter_var_arg.ident_expr.name

                # expand_filter_macro_pb など、対応する展開関数を呼び出す
                # expand_all, expand_exists, expand_exists_one は (target, iter_var, predicate, next_id)
                # expand_filter は (target, iter_var, filter_predicate, next_id)
                compre_expr_pb_part = macro_expander(
                    target_expr,
                    iter_var_name_str,
                    second_arg_expr,  # filterの場合は filter_predicate_expr
                    self._next_id
                )
                return syntax_pb2.Expr(id=expr_id, comprehension_expr=compre_expr_pb_part)

            elif method_name == "map":  # ★ "map" マクロの処理を追加
                if not (len(args_expr_list) == 2 or len(args_expr_list) == 3):
                    raise ValueError(
                        f"Macro '{method_name}' on target expects 2 or 3 arguments, "
                        f"got {len(args_expr_list)} for '{ctx.getText()}'"
                    )

                iter_var_arg = args_expr_list[0]
                if not iter_var_arg.HasField("ident_expr"):
                    raise ValueError(
                        f"The first argument to '{method_name}' macro must be an identifier "
                        f"(iterator variable name), got {iter_var_arg.WhichOneof('expr_kind')}"
                    )
                iter_var_name_str = iter_var_arg.ident_expr.name

                filter_predicate_expr_arg: Optional[syntax_pb2.Expr] = None
                transform_expr_arg: syntax_pb2.Expr

                if len(args_expr_list) == 2:  # map(x, t)
                    transform_expr_arg = args_expr_list[1]
                else:  # map(x, p, t)
                    filter_predicate_expr_arg = args_expr_list[1]
                    transform_expr_arg = args_expr_list[2]

                # expand_map_macro_pb を呼び出す
                compre_expr_pb_part = macro_expander(  # expand_map_macro_pb のこと
                    target_expr,
                    iter_var_name_str,
                    transform_expr_arg,  # transform_expr は必須
                    self._next_id,
                    filter_predicate_expr_arg  # filter_predicate_expr はオプショナル
                )
                return syntax_pb2.Expr(id=expr_id, comprehension_expr=compre_expr_pb_part)

        # 通常のメソッド呼び出し
        return syntax_pb2.Expr(
            id=expr_id,
            call_expr=syntax_pb2.Expr.Call(
                target=target_expr,
                function=method_name,
                args=args_expr_list
            )
        )

    def visitNested(self, ctx: CELParser.NestedContext): # primary #Nested
        # method_name = "visitNested"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: '(' e=expr ')'
        # 括弧はASTノードとしては通常表現されず、中の式の優先順位を変えるだけ。
        # よって、中の式をvisitした結果をそのまま返す。IDは中の式に依存。
        result = self.visit(ctx.e)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitStart(self, ctx: CELParser.StartContext):
        # method_name = "visitStart"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        result = self.visit(ctx.expr())
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitExpr(self, ctx: CELParser.ExprContext):  # expr #Conditional
        #method_name = "visitConditional"
        #print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: e=conditionalOr (op='?' thenBranch=conditionalOr ':' elseBranch=expr)?

        if ctx.op:  # 'op' ラベルが付いた '?' トークンが存在すれば、三項演算子
            expr_id = self._next_id(ctx)
            condition = self.visit(ctx.e)
            true_expr = self.visit(ctx.e1)
            false_expr = self.visit(ctx.e2)

            if condition is None or true_expr is None or false_expr is None:
                raise ValueError(f"One or more operands for ternary operator resulted in None for '{ctx.getText()}'")

            call_pb = syntax_pb2.Expr.Call(
                function="_?_:_",
                args=[condition, true_expr, false_expr]
            )
            result = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)
        else:  # 単なる conditionalOr
            result = self.visit(ctx.e)

        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitConditionalOr(self, ctx: CELParser.ConditionalOrContext):
        # method_name = "visitConditionalOr"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")

        current_left_expr = self.visit(ctx.e)
        if current_left_expr is None:
            raise ValueError(f"Visitor returned None for initial operand in ConditionalOr: {ctx.e.getText()}")

        if not ctx.ops:
            # print(f"LEAVING: {method_name} (no ops), returning type: {type(current_left_expr)}")
            return current_left_expr

        for i in range(len(ctx.ops)):
            right_operand_ctx = ctx.e1[i]
            right_expr = self.visit(right_operand_ctx)
            if right_expr is None:
                raise ValueError(
                    f"Visitor returned None for right operand in ConditionalOr: {right_operand_ctx.getText()}")

            expr_id = self._next_id(ctx)
            call_pb = syntax_pb2.Expr.Call(
                function="_||_",
                args=[current_left_expr, right_expr]
            )
            current_left_expr = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)

        # print(f"LEAVING: {method_name} (with ops), returning type: {type(current_left_expr)}")
        return current_left_expr


    def visitConditionalAnd(self, ctx: CELParser.ConditionalAndContext):
        # method_name = "visitConditionalAnd"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")

        current_left_expr = self.visit(ctx.e)
        if current_left_expr is None:
            raise ValueError(f"Visitor returned None for initial operand in ConditionalAnd: {ctx.e.getText()}")

        if not ctx.ops:
            # print(f"LEAVING: {method_name} (no ops), returning type: {type(current_left_expr)}")
            return current_left_expr

        for i in range(len(ctx.ops)):
            right_operand_ctx = ctx.e1[i]
            right_expr = self.visit(right_operand_ctx)
            if right_expr is None:
                raise ValueError(
                    f"Visitor returned None for right operand in ConditionalAnd: {right_operand_ctx.getText()}")

            expr_id = self._next_id(ctx)
            call_pb = syntax_pb2.Expr.Call(
                function="_&&_",
                args=[current_left_expr, right_expr]
            )
            current_left_expr = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)

        # print(f"LEAVING: {method_name} (with ops), returning type: {type(current_left_expr)}")
        return current_left_expr

    def visitCreateStruct(self, ctx: CELParser.CreateStructContext): # primary #CreateStruct
        # method_name = "visitCreateStruct (map)"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: op='{' entries=mapInitializerList? ','? '}'
        # これは型名なしの構造体リテラル、つまりマップ。
        expr_id = self._next_id(ctx)
        entries_pb = []
        if ctx.entries: # entries ラベルの mapInitializerList
            entries_pb = self.visit(ctx.entries) # visitMapInitializerList が Entry のリストを返す

        struct_pb = syntax_pb2.Expr.CreateStruct(
            message_name="",  # マップの場合は空
            entries=entries_pb
        )
        result = syntax_pb2.Expr(id=expr_id, struct_expr=struct_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result



    def visitMapInitializerList(self, ctx: CELParser.MapInitializerListContext):
        # method_name = "visitMapInitializerList"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: keys+=optExpr cols+=':' values+=expr (',' keys+=optExpr cols+=':' values+=expr)*
        # syntax_pb2.Expr.CreateStruct.Entry のリストを返す
        entries = []
        if ctx.keys: # keys リストが存在する場合
            for i in range(len(ctx.keys)):
                key_ctx = ctx.keys[i]   # optExpr
                value_ctx = ctx.values[i] # expr

                # optExpr: (opt='?')? e=expr
                # マップキーではオプショナル '?' は通常意味を持たない。e を visit。
                key_expr = self.visit(key_ctx.e)
                value_expr = self.visit(value_ctx)

                if key_expr is None or value_expr is None:
                    raise ValueError(f"Key or value in map initializer resulted in None for '{key_ctx.e.getText()}:{value_ctx.getText()}'")


                entry_id = self._next_id(key_ctx) # 各エントリにIDを振るか検討 (Entry PB にはidなし)
                entries.append(
                    syntax_pb2.Expr.CreateStruct.Entry(
                        # id = entry_id, # CreateStruct.Entry に id フィールドはない
                        map_key=key_expr,
                        value=value_expr
                    )
                )
        # print(f"LEAVING: {method_name}, returning {len(entries)} entries")
        return entries

    def visitFieldInitializerList(self, ctx: CELParser.FieldInitializerListContext):
        # method_name = "visitFieldInitializerList"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: fields+=optField cols+=':' values+=expr (',' fields+=optField cols+=':' values+=expr)*
        # syntax_pb2.Expr.CreateStruct.Entry のリストを返す
        entries = []
        if ctx.fields:  # fields リストが存在する場合
            for i in range(len(ctx.fields)):
                field_ctx = ctx.fields[i]  # optField
                value_ctx = ctx.values[i]  # expr

                # optField: (opt='?')? escapeIdent
                # フィールド初期化ではオプショナル '?' は通常意味を持たない。
                # escapeIdent からキー名を取得。
                key_node = field_ctx.escapeIdent()  # escapeIdentコンテキスト
                # escapeIdent: id=IDENTIFIER | id=ESC_IDENTIFIER
                field_key_name = key_node.id_.text  # IDENTIFIERまたはESC_IDENTIFIERのテキスト

                if field_key_name.startswith('`') and field_key_name.endswith('`'):
                    field_key_name = field_key_name[1:-1]

                value_expr = self.visit(value_ctx)
                if value_expr is None:
                    raise ValueError(
                        f"Value for field '{field_key_name}' in struct initializer resulted in None for '{value_ctx.getText()}'")

                entry_id = self._next_id(field_ctx)  # 各エントリにIDを振るか検討 (Entry PB にはidなし)
                entries.append(
                    syntax_pb2.Expr.CreateStruct.Entry(
                        # id = entry_id,
                        field_key=field_key_name,
                        value=value_expr
                    )
                )
        # print(f"LEAVING: {method_name}, returning {len(entries)} entries")
        return entries

    def visitGlobalCall(self, ctx: CELParser.GlobalCallContext):
        expr_id = self._next_id(ctx)
        func_name = ctx.id_.text

        args_expr_list = []
        if ctx.args:
            for arg_ctx in ctx.args.e:
                args_expr_list.append(self.visit(arg_ctx))

        if func_name in MACRO_DISPATCH_PB:
            macro_expander = MACRO_DISPATCH_PB[func_name]

            if func_name in ["all", "exists", "exists_one", "filter"]:  # ★ "filter" を追加
                expected_args = 3  # iterable, iter_var, predicate/transform
                if len(args_expr_list) != expected_args:
                    raise ValueError(
                        f"Global macro '{func_name}' expects {expected_args} arguments, got {len(args_expr_list)}")

                target_expr_for_global = args_expr_list[0]
                iter_var_arg_for_global = args_expr_list[1]
                second_arg_expr_for_global = args_expr_list[2]  # predicate or transform

                if not iter_var_arg_for_global.HasField("ident_expr"):
                    raise ValueError(f"The second argument to global '{func_name}' macro must be an identifier.")
                iter_var_name_str_for_global = iter_var_arg_for_global.ident_expr.name

                compre_expr_pb_part = macro_expander(
                    target_expr_for_global,
                    iter_var_name_str_for_global,
                    second_arg_expr_for_global,
                    self._next_id
                )
                return syntax_pb2.Expr(id=expr_id, comprehension_expr=compre_expr_pb_part)

            elif func_name == "map":  # ★ "map" マクロの処理を追加 (グローバル版)
                if not (len(args_expr_list) == 3 or len(args_expr_list) == 4):
                    raise ValueError(f"Global macro '{func_name}' expects 3 or 4 arguments, got {len(args_expr_list)}")

                target_expr_for_global = args_expr_list[0]
                iter_var_arg_for_global = args_expr_list[1]
                if not iter_var_arg_for_global.HasField("ident_expr"):
                    raise ValueError(f"The second argument to global '{func_name}' macro must be an identifier.")
                iter_var_name_str_for_global = iter_var_arg_for_global.ident_expr.name

                filter_predicate_expr_arg: Optional[syntax_pb2.Expr] = None
                transform_expr_arg: syntax_pb2.Expr

                if len(args_expr_list) == 3:  # map(e, x, t)
                    transform_expr_arg = args_expr_list[2]
                else:  # map(e, x, p, t)
                    filter_predicate_expr_arg = args_expr_list[2]
                    transform_expr_arg = args_expr_list[3]

                compre_expr_pb_part = macro_expander(  # expand_map_macro_pb のこと
                    target_expr_for_global,
                    iter_var_name_str_for_global,
                    transform_expr_arg,
                    self._next_id,
                    filter_predicate_expr_arg
                )
                return syntax_pb2.Expr(id=expr_id, comprehension_expr=compre_expr_pb_part)

            elif func_name == "len" or func_name == "has":
                # (既存のlen, hasの処理)
                if len(args_expr_list) != 1: raise ValueError(f"Macro '{func_name}' expects 1 argument")
                macro_target_arg = args_expr_list[0]
                expanded_part = macro_expander(macro_target_arg)
                if isinstance(expanded_part, syntax_pb2.Expr.Call):
                    return syntax_pb2.Expr(id=expr_id, call_expr=expanded_part)
                elif isinstance(expanded_part, syntax_pb2.Expr.Select):
                    return syntax_pb2.Expr(id=expr_id, select_expr=expanded_part)
                elif isinstance(expanded_part, syntax_pb2.Expr):
                    expanded_part.id = expr_id; return expanded_part
                else:
                    raise TypeError(f"Macro '{func_name}' returned an unexpected type: {type(expanded_part)}")

        elif func_name in LITERAL_CONSTRUCTORS_PB:
                    # "duration(...)" や "timestamp(...)" のようなリテラル風コンストラクタの場合
                    if len(args_expr_list) == 1:
                        arg_expr_node = args_expr_list[0]
                        # 引数が文字列リテラルの定数である場合のみ、特別扱いする
                        if arg_expr_node.HasField("const_expr") and \
                           arg_expr_node.const_expr.HasField("string_value"):

                            string_value_for_literal = arg_expr_node.const_expr.string_value
                            literal_constructor_func = LITERAL_CONSTRUCTORS_PB[func_name] # literal_registry_pb.make_literal_pb

                            try:
                                # make_literal_pb は内部で _lit_timestamp_ や _lit_duration_ の呼び出しExprを生成
                                constructed_expr_node = literal_constructor_func(func_name, string_value_for_literal)
                                constructed_expr_node.id = expr_id # 元の呼び出しIDを割り当てる
                                return constructed_expr_node
                            except ValueError as ve:
                                # parse_duration や parse_timestamp_pb でのバリデーションエラー
                                # (例: "timestamp('invalid-date')")
                                # このエラーはCELCompileErrorにラップされることを期待して再送出
                                raise ValueError(f"Invalid literal for {func_name}(): {ve}") from ve
                        else:
                            # 引数が文字列リテラルでない場合 (例: timestamp(0), timestamp(my_var))
                            # これはリテラル形式ではなく、通常の関数呼び出しとして扱う。
                            # このブロックでは何もしない (pass) ことで、後続の通常の関数呼び出しロジックにフォールスルーする。
                            pass
                    else:
                        # 引数が1つでない場合も、リテラル形式ではない。通常の関数呼び出しとして扱う。
                        pass

        # 通常のグローバル関数呼び出し
        return syntax_pb2.Expr(
            id=expr_id,
            call_expr=syntax_pb2.Expr.Call(function=func_name, args=args_expr_list)
        )

    def visitBytes(self, ctx: CELParser.BytesContext):
        expr_id = self._next_id(ctx)
        full_token_text = ctx.tok.text  # 例: b'ÿ', rb'\xff', B"foo\u00FFbar"

        # 1. Determine if RAW and extract content string
        is_raw = False
        content_str_with_quotes: str

        if full_token_text.lower().startswith("rb"):
            is_raw = True
            content_str_with_quotes = full_token_text[2:]
        elif full_token_text.lower().startswith("b"):
            is_raw = False
            content_str_with_quotes = full_token_text[1:]
        else:
            # Should be caught by lexer/parser, but defensive
            raise ValueError(f"Invalid bytes literal prefix: {full_token_text}")


        byte_value = unquote(content_str_with_quotes, True)
        const_pb = syntax_pb2.Constant(bytes_value=byte_value)
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        return result

    def visitDouble(self, ctx: CELParser.DoubleContext): # literal #Double
        # method_name = "visitDouble"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        sign = -1.0 if ctx.sign else 1.0
        const_pb = syntax_pb2.Constant(double_value=sign * float(ctx.tok.text))
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitCreateMessage(self, ctx: CELParser.CreateMessageContext):  # primary #CreateMessage
        # method_name = "visitCreateMessage"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: leadingDot='.'? ids+=IDENTIFIER (ops+='.' ids+=IDENTIFIER)* op='{' entries=fieldInitializerList? ','? '}'
        expr_id = self._next_id(ctx)

        # message_name の構築: ids リストを '.' で連結
        # ctx.ids は IDENTIFIER トークンのリスト
        message_name_parts = [id_token.text for id_token in ctx.ids]
        message_name = ".".join(message_name_parts)
        if ctx.leadingDot:  # 先頭のドットがある場合
            message_name = "." + message_name

        entries_pb = []
        if ctx.entries:  # entries ラベルの fieldInitializerList
            entries_pb = self.visit(ctx.entries)  # visitFieldInitializerList が Entry のリストを返す

        struct_pb = syntax_pb2.Expr.CreateStruct(
            message_name=message_name,
            entries=entries_pb
        )
        result = syntax_pb2.Expr(id=expr_id, struct_expr=struct_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitCreateList(self, ctx: CELParser.CreateListContext):  # primary #CreateList
        # method_name = "visitCreateList"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        elements = []
        if ctx.elems:  # elems ラベルの listInit
            # listInit: elems+=optExpr (',' elems+=optExpr)*
            for elem_ctx in ctx.elems.elems:  # listInit 内の elems ラベルの optExpr リスト
                # optExpr: (opt='?')? e=expr
                # ここでは opt ('?') は無視し、e (expr) を visit する。
                # オプショナル要素はCELのリストリテラルでは標準的ではない。
                # もしオプショナル要素のセマンティクスがあるなら、ここで考慮が必要。
                visited_elem = self.visit(elem_ctx.e)
                if visited_elem is None:
                    raise ValueError(f"Element in list literal resulted in None for '{elem_ctx.e.getText()}'")
                elements.append(visited_elem)

        list_pb = syntax_pb2.Expr.CreateList(elements=elements)
        result = syntax_pb2.Expr(id=expr_id, list_expr=list_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitRelation(self, ctx: CELParser.RelationContext):
        # method_name = "visitRelation"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # relation : calc | relation op=REL_OP relation ;

        if ctx.calc():  # Base case: relation -> calc
            # print(f"Relation base case: visiting calc: {ctx.calc().getText()}")
            result = self.visit(ctx.calc())
            if result is None:
                raise ValueError(f"Visiting calc base case for relation returned None: {ctx.calc().getText()}")
            # print(f"LEAVING: {method_name} (base case - calc), returning type: {type(result)}")
            return result
        # Recursive case: relation -> relation op relation
        # ctx.relation() はリスト [left_relation_ctx, right_relation_ctx] を返す
        # ctx.op は単一の演算子トークン (CommonToken)
        elif ctx.op and len(ctx.relation()) == 2:
            # print(f"Relation recursive case: {ctx.getText()}")
            left_expr = self.visit(ctx.relation(0))

            op_token = ctx.op
            if op_token is None:  # Should be caught by `ctx.op` check above, but defensive
                raise RuntimeError(f"Operator token is None in recursive relation rule: {ctx.getText()}")

            op_text = op_token.text  # Use .text for CommonToken

            right_expr = self.visit(ctx.relation(1))

            if left_expr is None:
                raise ValueError(
                    f"Left operand for '{op_text}' resulted in None in relation: {ctx.relation(0).getText()}")
            if right_expr is None:
                raise ValueError(
                    f"Right operand for '{op_text}' resulted in None in relation: {ctx.relation(1).getText()}")

            expr_id = self._next_id(ctx)
            call_pb = syntax_pb2.Expr.Call(
                function=f"_{op_text}_",
                args=[left_expr, right_expr]
            )
            result = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)
            # print(f"LEAVING: {method_name} (recursive), returning call to {op_text}")
            return result
        else:
            raise RuntimeError(f"Unexpected structure for RelationContext: {ctx.getText()}")

    def visitCalc(self, ctx: CELParser.CalcContext):
        # method_name = "visitCalc"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # calc : unary | calc op=CALC_OP calc ;

        if ctx.unary():  # Base case: calc -> unary
            # print(f"Calc base case: visiting unary: {ctx.unary().getText()}")
            result = self.visit(ctx.unary())
            if result is None:
                raise ValueError(f"Visiting unary base case for calc returned None: {ctx.unary().getText()}")
            # print(f"LEAVING: {method_name} (base case - unary), returning type: {type(result)}")
            return result
        # Recursive case: calc -> calc op calc
        elif ctx.op and len(ctx.calc()) == 2:
            # print(f"Calc recursive case: {ctx.getText()}")
            left_expr = self.visit(ctx.calc(0))

            op_token = ctx.op
            if op_token is None:
                raise RuntimeError(f"Operator token is None in recursive calc rule: {ctx.getText()}")

            op_text = op_token.text  # Use .text for CommonToken

            right_expr = self.visit(ctx.calc(1))

            if left_expr is None:
                raise ValueError(f"Left operand for '{op_text}' resulted in None in calc: {ctx.calc(0).getText()}")
            if right_expr is None:
                raise ValueError(f"Right operand for '{op_text}' resulted in None in calc: {ctx.calc(1).getText()}")

            expr_id = self._next_id(ctx)
            call_pb = syntax_pb2.Expr.Call(
                function=f"_{op_text}_",
                args=[left_expr, right_expr]
            )
            result = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)
            # print(f"LEAVING: {method_name} (recursive), returning call to {op_text}")
            return result
        else:
            raise RuntimeError(f"Unexpected structure for CalcContext: {ctx.getText()}")

    # member ルールに対応
    def visitPrimaryExpr(self, ctx: CELParser.PrimaryExprContext): # member #PrimaryExpr
        # method_name = "visitPrimaryExpr (member rule)"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: primary #PrimaryExpr (memberルールの一部)
        # ctx は PrimaryExprContext (MemberContextのサブクラス)
        result = self.visit(ctx.primary()) # primary()メソッドでprimaryコンテキストを取得
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitConstantLiteral(self, ctx: CELParser.ConstantLiteralContext): # primary #ConstantLiteral
        # method_name = "visitConstantLiteral"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # このメソッドは literal ルールのラッパーなので、literal を visit する。
        # ID は visitLiteral の各メソッド内で振られる。
        result = self.visit(ctx.literal())
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitString(self, ctx: CELParser.StringContext):  # literal #String
        expr_id = self._next_id(ctx)
        raw_text = ctx.tok.text
        unescaped_value = ""  # デフォルト値

        try:
            # RAW文字列の判定を優先度の高い（より具体的な、または長いプレフィックス/サフィックスを持つ）ものから行う
            # raw_text.lower() を使うことで R''' と r''' を同じように扱える

            # 1. RAWトリプルダブルクォート (例: r"""text""" or R"""text""")
            if raw_text.lower().startswith('r"""') and raw_text.endswith('"""'):
                if len(raw_text) < 6:  # r + """ + """ で最低6文字
                    raise ValueError(f"Malformed RAW triple double quoted string literal: {raw_text}")
                unescaped_value = raw_text[4:-3]  # r""" の4文字と末尾の """ 3文字を除去

            # 2. RAWトリプルシングルクォート (例: r'''text''' or R'''text''')
            elif raw_text.lower().startswith("r'''") and raw_text.endswith("'''"):
                if len(raw_text) < 6:  # r + ''' + ''' で最低6文字
                    raise ValueError(f"Malformed RAW triple single quoted string literal: {raw_text}")
                unescaped_value = raw_text[4:-3]  # r''' の4文字と末尾の ''' 3文字を除去

            # 3. RAWダブルクォート (例: r"text" or R"text")
            elif raw_text.lower().startswith('r"') and raw_text.endswith('"'):
                if len(raw_text) < 3:  # r + " + " で最低3文字
                    raise ValueError(f"Malformed RAW double quoted string literal: {raw_text}")
                unescaped_value = raw_text[2:-1]  # r" の2文字と末尾の " 1文字を除去

            # 4. RAWシングルクォート (例: r'text' or R'text')
            elif raw_text.lower().startswith("r'") and raw_text.endswith("'"):
                if len(raw_text) < 3:  # r + ' + ' で最低3文字
                    raise ValueError(f"Malformed RAW single quoted string literal: {raw_text}")
                unescaped_value = raw_text[2:-1]  # r' の2文字と末尾の ' 1文字を除去


            # 5. 通常の文字列リテラル (エスケープシーケンス処理が必要)
            else:
                # ast.literal_eval はPythonの文字列リテラルのエスケープを正しく処理する
                # また、不正なリテラル（例: クォートが閉じていない）の場合は ValueError を送出する
                unescaped_value = ast.literal_eval(raw_text)

            if not isinstance(unescaped_value, str):  # 通常発生しないはずだが念のため
                raise ValueError(f"Parsed string literal did not result in a Python string for: {raw_text}")

        except ValueError as e:  # ast.literal_eval や上記のカスタムチェックからのエラー
            # CELCompileError にラップするか、より詳細なエラーとして処理
            # ここでは CELCompileError が api.py で定義されていると仮定
            # from cel.api import CELCompileError # 必要に応じてインポート
            # raise CELCompileError(f"Invalid string literal: {raw_text}. Details: {e}",
            #                       line=ctx.tok.line, column=ctx.tok.column)
            # 簡単のため ValueError のまま再送出 (呼び出し側で処理)
            raise ValueError(f"Invalid string literal: {raw_text}. Details: {e}") from e
        except Exception as e:  # その他の予期しないエラー
            raise ValueError(f"Unexpected error parsing string literal '{raw_text}': {e}") from e

        const_pb = syntax_pb2.Constant(string_value=unescaped_value)
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        return result


    def visitIndex(self, ctx: CELParser.IndexContext): # member #Index
        # method_name = "visitIndex"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        operand = self.visit(ctx.member()) # 左辺のmember
        index_expr = self.visit(ctx.index)    # indexラベルのexpr

        if operand is None or index_expr is None:
            raise ValueError(f"Operand or index for '[]' operator resulted in None for '{ctx.getText()}'")

        call_pb = syntax_pb2.Expr.Call(
            function="_[_]",
            args=[operand, index_expr]
        )
        result = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitInt(self, ctx: CELParser.IntContext):  # literalルールの #Int ラベルに対応
        expr_id = self._next_id(ctx)

        # ctx.tok は NUM_INT トークン。そのテキストは符号なしの数値文字列。
        # 例: "123", "0xCAFE", "9223372036854775808"
        raw_numeric_text_abs = ctx.tok.text  # NUM_INT トークンのテキストを取得

        # ctx.sign は MINUS トークン、またはマイナス記号がない場合は None。
        has_minus_sign = ctx.sign is not None

        try:
            # まず、符号なしの数値部分をパースする。
            # int(string, 0) を使用して、プレフィックスに基づいて基数を自動判断。
            abs_value = int(raw_numeric_text_abs, 0)
        except ValueError as e:
            # NUM_INT トークンが int() でパースできない形式だった場合
            original_literal_for_error_msg = f"-{raw_numeric_text_abs}" if has_minus_sign else raw_numeric_text_abs
            raise ValueError(
                f"Invalid integer literal format for token part '{raw_numeric_text_abs}' "
                f"(from original literal '{original_literal_for_error_msg}'): {e}"
            ) from e

        # 符号を適用して最終的な数値 (numeric_value) を得る
        numeric_value: int
        if has_minus_sign:
            numeric_value = -abs_value
        else:
            numeric_value = abs_value

        # パースされた最終的な値が int64 の範囲内かチェック
        if not (INT64_MIN <= numeric_value <= INT64_MAX):
            original_literal_for_error_msg = f"-{raw_numeric_text_abs}" if has_minus_sign else raw_numeric_text_abs
            # このエラーがapi.pyまで伝播し、CELCompileErrorにラップされることを期待
            raise ValueError(
                f"Integer literal '{original_literal_for_error_msg}' (parsed as {numeric_value}) is out of int64 range "
                f"({INT64_MIN} to {INT64_MAX})."
            )

        # int64 の範囲内であれば、int64_value に設定
        const_pb = syntax_pb2.Constant(int64_value=numeric_value)
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        return result

    def visitUint(self, ctx: CELParser.UintContext):  # literalルール の #Uint ラベルに対応
        expr_id = self._next_id(ctx)
        raw_uint_text = ctx.tok.text

        numeric_text_part = raw_uint_text
        if raw_uint_text.lower().endswith('u'):
            numeric_text_part = raw_uint_text[:-1]

        try:
            numeric_value = int(numeric_text_part, 0)
        except ValueError as e:
            raise ValueError(f"Invalid unsigned integer literal format for token '{raw_uint_text}': {e}") from e

        UINT64_MAX = 2 ** 64 - 1
        if not (0 <= numeric_value <= UINT64_MAX):
            raise ValueError(
                f"Unsigned integer literal '{raw_uint_text}' (parsed as {numeric_value}) "
                f"is out of uint64 range (0 to {UINT64_MAX})."
            )

        if hasattr(syntax_pb2.Constant(), "uint64_value"):
            const_pb = syntax_pb2.Constant(uint64_value=numeric_value)
        else:
            if numeric_value > INT64_MAX:
                raise ValueError(
                    f"Unsigned integer {numeric_value} (from literal '{raw_uint_text}') cannot be represented as int64, "
                    "and uint64_value field is not available in Constant protobuf."
                )
            const_pb = syntax_pb2.Constant(int64_value=numeric_value)

        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        return result

    def visitBoolTrue(self, ctx: CELParser.BoolTrueContext): # literal #BoolTrue
        # method_name = "visitBoolTrue"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        const_pb = syntax_pb2.Constant(bool_value=True)
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitBoolFalse(self, ctx: CELParser.BoolFalseContext): # literal #BoolFalse
        # method_name = "visitBoolFalse"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        const_pb = syntax_pb2.Constant(bool_value=False)
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitNull(self, ctx: CELParser.NullContext): # literal #Null
        # method_name = "visitNull"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        const_pb = syntax_pb2.Constant(null_value=0) # google.protobuf.NullValue.NULL_VALUE
        result = syntax_pb2.Expr(id=expr_id, const_expr=const_pb)
        # print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result

    def visitSelect(self, ctx: CELParser.SelectContext):
        operand = self.visit(ctx.member())
        # ANTLRの文法で escapeIdent または simpleIdent が選択的に存在すると仮定
        ident_node = ctx.escapeIdent() or ctx.simpleIdent()

        ## TODO: これもっとちゃんと処理しないといけないのでは？
        ident_text = ident_node.getText()

        if ident_text.startswith('`') and ident_text.endswith('`'):
            ident_text = ident_text[1:-1]

        expr_id = self._next_id(ctx)

        # opt (?.演算子) の有無で test_only を設定する既存ロジックを維持。
        # 注意: CEL標準の Select.test_only は主に has() マクロの内部表現です。
        # `?.` (オプショナルセレクト) は評価時のnull伝播であり、test_onlyとは概念が異なります。
        # 評価器側でこの test_only フラグをどう解釈するかに依存します。
        is_test_only = ctx.opt is not None

        return syntax_pb2.Expr(
            id=expr_id,
            select_expr=syntax_pb2.Expr.Select(
                operand=operand,
                field=ident_text,
                test_only=is_test_only
            )
        )

    # def visitLetExpr(self, ctx: CELParser.LetExprContext): # expr #LetExpr
    #     # method_name = "visitLetExpr"
    #     # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
    #     expr_id = self._next_id(ctx)
    #     var_name = ctx.id_.text
    #     value_expr = self.visit(ctx.init)
    #     body_expr = self.visit(ctx.body)
    #
    #     let_pb = syntax_pb2.Expr.LetExpr(
    #         name=var_name,
    #         value=value_expr,
    #         body=body_expr
    #     )
    #     result = syntax_pb2.Expr(id=expr_id, let_expr=let_pb)
    #     # print(f"LEAVING: {method_name}, returning type: {type(result)}")
    #     return result

    def visitLogicalNot(self, ctx: CELParser.LogicalNotContext):  # unary #LogicalNot
        # method_name = "visitLogicalNot"
        # print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: (ops+='!')+ member
        member_ctx = ctx.member()
        if member_ctx is None:
            raise ValueError(f"No member context found in LogicalNot for '{ctx.getText()}'")

        operand_expr = self.visit(member_ctx)
        if operand_expr is None:
            raise ValueError(f"Visitor returned None for operand in LogicalNot: {member_ctx.getText()}")

        current_expr = operand_expr
        if ctx.ops:
            for _ in reversed(ctx.ops):
                expr_id = self._next_id(ctx)
                call_pb = syntax_pb2.Expr.Call(function="_!_", args=[current_expr])
                current_expr = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)

        # print(f"LEAVING: {method_name}, returning type: {type(current_expr)}")
        return current_expr


    def visitNegate(self, ctx: CELParser.NegateContext): # unary #Negate
        #method_name = "visitNegate"
        #print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        # 文法: (ops+='-')+ member

        member_ctx = ctx.member()
        if member_ctx is None:
            raise ValueError(f"No member context found in Negate for '{ctx.getText()}'")

        operand_expr = self.visit(member_ctx)
        if operand_expr is None:
            raise ValueError(f"Visitor returned None for operand in Negate: {member_ctx.getText()}")

        current_expr = operand_expr
        if ctx.ops: # ops は '-' トークンのリスト
            for _ in reversed(ctx.ops): # 複数の '-' がある場合、内側から適用
                expr_id = self._next_id(ctx)
                # 単項マイナスは "_-_" 関数として表現
                call_pb = syntax_pb2.Expr.Call(function="_-_", args=[current_expr])
                current_expr = syntax_pb2.Expr(id=expr_id, call_expr=call_pb)

        # print(f"LEAVING: {method_name}, returning type: {type(current_expr)}")
        return current_expr

    # primary ルールに対応
    def visitIdent(self, ctx: CELParser.IdentContext):  # primary #Ident
        #method_name = "visitIdent"
        #print(f"ENTERING: {method_name}, ctx text: {ctx.getText()}")
        expr_id = self._next_id(ctx)
        ident_name = ctx.id_.text  # IDENTIFIERにidラベル

        # leadingDot の存在はCELのセマンティクスで考慮される (例: .name はレシーバが暗黙的)
        # ここでは Ident Expr を作るだけなので、leadingDot の情報は直接使わない。
        # 評価器がコンテキストに応じて解釈する。

        ident_pb = syntax_pb2.Expr.Ident(name=ident_name)
        result = syntax_pb2.Expr(id=expr_id, ident_expr=ident_pb)
        #print(f"LEAVING: {method_name}, returning type: {type(result)}")
        return result
