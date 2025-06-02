from typing import Optional

from cel.expr import syntax_pb2


def expand_all_macro_pb(
    target_expr: syntax_pb2.Expr,
    iter_var_name_str: str,
    predicate_expr: syntax_pb2.Expr,
    next_id_func: callable
) -> syntax_pb2.Expr.Comprehension:
    accu_var_name = f"__all_accu_{next_id_func()}__"
    accu_init_expr = syntax_pb2.Expr(id=next_id_func(), const_expr=syntax_pb2.Constant(bool_value=True))
    loop_condition_expr = syntax_pb2.Expr(id=next_id_func(), const_expr=syntax_pb2.Constant(bool_value=True))
    accu_var_ident_for_step = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))
    loop_step_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(
            function="_&&_",
            args=[accu_var_ident_for_step, predicate_expr]
        )
    )
    result_expr = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))
    return syntax_pb2.Expr.Comprehension(
        iter_var=iter_var_name_str,
        iter_range=target_expr,
        accu_var=accu_var_name,
        accu_init=accu_init_expr,
        loop_condition=loop_condition_expr,
        loop_step=loop_step_expr,
        result=result_expr
    )


def expand_exists_macro_pb(
        target_expr: syntax_pb2.Expr,
        iter_var_name_str: str,
        predicate_expr: syntax_pb2.Expr,
        next_id_func: callable
) -> syntax_pb2.Expr.Comprehension:
    accu_var_name = f"__exists_accu_{next_id_func()}__"
    accu_init_expr = syntax_pb2.Expr(id=next_id_func(), const_expr=syntax_pb2.Constant(bool_value=False))
    loop_condition_expr = syntax_pb2.Expr(id=next_id_func(), const_expr=syntax_pb2.Constant(bool_value=True))
    accu_var_ident_for_step = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))
    loop_step_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(
            function="_||_",
            args=[accu_var_ident_for_step, predicate_expr]
        )
    )
    result_expr = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))
    return syntax_pb2.Expr.Comprehension(
        iter_var=iter_var_name_str,
        iter_range=target_expr,
        accu_var=accu_var_name,
        accu_init=accu_init_expr,
        loop_condition=loop_condition_expr,
        loop_step=loop_step_expr,
        result=result_expr
    )


def expand_exists_one_macro_pb(
        target_expr: syntax_pb2.Expr,
        iter_var_name_str: str,
        predicate_expr: syntax_pb2.Expr,
        next_id_func: callable
) -> syntax_pb2.Expr.Comprehension:
    """
    Expands e.exists_one(x, p) macro into a ComprehensionExpr.
    Counts how many times the predicate p is true.
    Result is true if the count is exactly 1.
    Errors in p are propagated.
    """
    # アキュムレータ変数名 (述語がtrueになった回数をカウント)
    count_accu_var_name = f"__e1_count_{next_id_func()}__"

    # アキュムレータの初期値: int(0)
    accu_init_expr = syntax_pb2.Expr(
        id=next_id_func(),
        const_expr=syntax_pb2.Constant(int64_value=0)
    )

    # ループ継続条件: 常にtrue (エラーはステップで処理)
    loop_condition_expr = syntax_pb2.Expr(
        id=next_id_func(),
        const_expr=syntax_pb2.Constant(bool_value=True)
    )

    # ループステップ: predicate(x) ? count_accu_var + 1 : count_accu_var
    # AST構造: _?_:_(predicate_expr, _+_(Ident(count_accu_var), Const(1)), Ident(count_accu_var))

    # count_accu_var の識別子ノード (複数回使用)
    count_accu_ident_expr = syntax_pb2.Expr(
        id=next_id_func(),
        ident_expr=syntax_pb2.Expr.Ident(name=count_accu_var_name)
    )

    # Const(1) ノード
    one_const_expr = syntax_pb2.Expr(
        id=next_id_func(),
        const_expr=syntax_pb2.Constant(int64_value=1)
    )

    # count_accu_var + 1 の部分
    incremented_accu_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(
            function="_+_",
            args=[count_accu_ident_expr, one_const_expr]
        )
    )

    # 三項演算子全体
    loop_step_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(
            function="_?_:_",
            args=[
                predicate_expr,  # 条件: p(x)
                incremented_accu_expr,  # trueの場合: count_accu_var + 1
                count_accu_ident_expr  # falseの場合: count_accu_var
            ]
        )
    )

    # 結果: count_accu_var == 1
    # AST構造: _==_(Ident(count_accu_var), Const(1))

    # count_accu_var の識別子ノード (結果比較用、IDは別にする)
    count_accu_ident_for_result_expr = syntax_pb2.Expr(
        id=next_id_func(),
        ident_expr=syntax_pb2.Expr.Ident(name=count_accu_var_name)
    )
    # Const(1) ノード (結果比較用、IDは別にする)
    one_const_for_result_expr = syntax_pb2.Expr(
        id=next_id_func(),
        const_expr=syntax_pb2.Constant(int64_value=1)
    )

    result_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(
            function="_==_",
            args=[count_accu_ident_for_result_expr, one_const_for_result_expr]
        )
    )

    return syntax_pb2.Expr.Comprehension(
        iter_var=iter_var_name_str,
        iter_range=target_expr,
        accu_var=count_accu_var_name,
        accu_init=accu_init_expr,
        loop_condition=loop_condition_expr,
        loop_step=loop_step_expr,
        result=result_expr
    )


def expand_len_macro_pb(arg_expr: syntax_pb2.Expr) -> syntax_pb2.Expr.Call:
    """
    len(x) マクロを展開し、'size' 関数への呼び出し (CallExpr) を返します。
    'size' 関数は len() に相当する標準的なCEL関数です。

    Args:
        arg_expr: lenの引数を表すExprノード (例: リストや文字列)。

    Returns:
        'size' 関数呼び出しを表す syntax_pb2.Expr.Call ノード。
    """
    # CEL標準では len() に相当するのは size() 関数です。
    # 評価器側で 'size' (または内部的な '_size_' や '_len_') を解釈できるようにする必要があります。
    return syntax_pb2.Expr.Call(
        function="size",  # 標準的なCEL関数名
        args=[arg_expr]
    )

def expand_has_macro_pb(arg_expr: syntax_pb2.Expr) -> syntax_pb2.Expr.Select:
    """
    has(x.y) マクロを展開し、test_only=true の SelectExpr を返します。
    has(x) マクロを展開し、フィールド名が空で test_only=true の SelectExpr を返します。

    Args:
        arg_expr: hasの引数を表すExprノード。
                  これは select_expr (x.yの場合) または ident_expr (xの場合) であるべきです。

    Returns:
        syntax_pb2.Expr.Select ノード。

    Raises:
        ValueError: 引数が識別子またはフィールド選択でない場合。
    """
    if arg_expr.HasField("select_expr"):
        # has(x.y) の場合
        select_pb = arg_expr.select_expr
        return syntax_pb2.Expr.Select(
            operand=select_pb.operand,
            field=select_pb.field,
            test_only=True
        )
    elif arg_expr.HasField("ident_expr"):
        # has(x) の場合
        # オペランドには識別子xを表すExprノードそのものを渡します。
        return syntax_pb2.Expr.Select(
            operand=arg_expr, # ident_expr を持つ Expr ノードをオペランドとします。
            field="",         # フィールド名は空です。
            test_only=True
        )
    else:
        # has() マクロの引数は識別子かフィールド選択でなければなりません。
        raise ValueError(
            "has() macro argument must be an identifier or a field selection "
            f"(e.g., has(x) or has(x.y)), got {arg_expr.WhichOneof('expr_kind')}"
        )


def expand_filter_macro_pb(
        target_expr: syntax_pb2.Expr,
        iter_var_name_str: str,
        filter_predicate_expr: syntax_pb2.Expr,  # フィルター述語 p(x)
        next_id_func: callable
) -> syntax_pb2.Expr.Comprehension:
    """
    Expands e.filter(x, p) macro into a ComprehensionExpr.
    Result is a new list containing elements for which p(x) is true.
    """
    accu_var_name = f"__filter_accu_{next_id_func()}__"

    # accu_init: [] (空リスト)
    accu_init_expr = syntax_pb2.Expr(
        id=next_id_func(),
        list_expr=syntax_pb2.Expr.CreateList(elements=[])
    )
    # loop_condition: true
    loop_condition_expr = syntax_pb2.Expr(
        id=next_id_func(),
        const_expr=syntax_pb2.Constant(bool_value=True)
    )
    # loop_step: p(x) ? accu_var + [x] : accu_var
    accu_var_ident = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))
    iter_var_ident = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=iter_var_name_str))

    # [x] (要素を一つだけ持つリスト)
    list_with_iter_var = syntax_pb2.Expr(
        id=next_id_func(),
        list_expr=syntax_pb2.Expr.CreateList(elements=[iter_var_ident])
    )
    # accu_var + [x]
    added_to_accu_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(function="_+_", args=[accu_var_ident, list_with_iter_var])
    )
    # 三項演算子全体
    loop_step_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(
            function="_?_:_",
            args=[filter_predicate_expr, added_to_accu_expr, accu_var_ident]
        )
    )
    # result: accu_var
    result_expr = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))

    return syntax_pb2.Expr.Comprehension(
        iter_var=iter_var_name_str,
        iter_range=target_expr,
        accu_var=accu_var_name,
        accu_init=accu_init_expr,
        loop_condition=loop_condition_expr,
        loop_step=loop_step_expr,
        result=result_expr
    )


def expand_map_macro_pb(
        target_expr: syntax_pb2.Expr,
        iter_var_name_str: str,
        transform_expr: syntax_pb2.Expr,  # 変換式 t(x)
        next_id_func: callable,
        filter_predicate_expr: Optional[syntax_pb2.Expr] = None  # オプショナルなフィルター述語 p(x)
) -> syntax_pb2.Expr.Comprehension:
    """
    Expands e.map(x, t) or e.map(x, p, t) macro into a ComprehensionExpr.
    Result is a new list containing t(x) for elements where p(x) (if provided) is true.
    """
    accu_var_name = f"__map_accu_{next_id_func()}__"

    # accu_init: [] (空リスト)
    accu_init_expr = syntax_pb2.Expr(
        id=next_id_func(),
        list_expr=syntax_pb2.Expr.CreateList(elements=[])
    )
    # loop_condition: true
    loop_condition_expr = syntax_pb2.Expr(
        id=next_id_func(),
        const_expr=syntax_pb2.Constant(bool_value=True)
    )

    # loop_step の構築
    accu_var_ident = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))

    # [t(x)] (変換後の要素を一つだけ持つリスト)
    list_with_transformed_expr = syntax_pb2.Expr(
        id=next_id_func(),
        list_expr=syntax_pb2.Expr.CreateList(elements=[transform_expr])  # transform_expr は t(x) のAST
    )
    # accu_var + [t(x)]
    added_to_accu_expr = syntax_pb2.Expr(
        id=next_id_func(),
        call_expr=syntax_pb2.Expr.Call(function="_+_", args=[accu_var_ident, list_with_transformed_expr])
    )

    if filter_predicate_expr:  # map(x, p, t) の場合
        # loop_step: p(x) ? accu_var + [t(x)] : accu_var
        loop_step_expr = syntax_pb2.Expr(
            id=next_id_func(),
            call_expr=syntax_pb2.Expr.Call(
                function="_?_:_",
                args=[filter_predicate_expr, added_to_accu_expr, accu_var_ident]
            )
        )
    else:  # map(x, t) の場合
        # loop_step: accu_var + [t(x)]
        loop_step_expr = added_to_accu_expr  # 上で作成したものをそのまま使用

    # result: accu_var
    result_expr = syntax_pb2.Expr(id=next_id_func(), ident_expr=syntax_pb2.Expr.Ident(name=accu_var_name))

    return syntax_pb2.Expr.Comprehension(
        iter_var=iter_var_name_str,
        iter_range=target_expr,
        accu_var=accu_var_name,
        accu_init=accu_init_expr,
        loop_condition=loop_condition_expr,
        loop_step=loop_step_expr,
        result=result_expr
    )

MACRO_DISPATCH_PB = {
    "len": expand_len_macro_pb,
    "has": expand_has_macro_pb,
    "all": expand_all_macro_pb,
    "exists": expand_exists_macro_pb,
    "exists_one": expand_exists_one_macro_pb,
    "filter": expand_filter_macro_pb,
    "map": expand_map_macro_pb,
}
