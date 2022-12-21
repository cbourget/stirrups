def param_is_positionnal(param) -> bool:
    return (
        param.kind == param.POSITIONAL_OR_KEYWORD and
        param.default is param.empty
    )


def param_is_keyword(param) -> bool:
    return (
        param.kind == param.POSITIONAL_OR_KEYWORD and
        param.default is not param.empty
    ) or param.kind == param.KEYWORD_ONLY


def param_is_variable(param) -> bool:
    return param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD)
