import click


_PATH_NAME_HINTS = ("path", "file", "certificate", "sql", "clone_from")


def normalize_param_name(name: str) -> str:
	return name.lower().replace("-", "_")


def looks_like_path_name(name: str) -> bool:
	normalized = normalize_param_name(name)
	return any(hint in normalized for hint in _PATH_NAME_HINTS)


def looks_like_path_option(option: str) -> bool:
	return looks_like_path_name(option.lstrip("-"))


def param_expects_path(param) -> bool:
	if isinstance(param.type, click.Path):
		return True

	names = []
	if isinstance(param, click.Option):
		if param.name:
			names.append(param.name)
		names.extend(option.lstrip("-") for option in param.opts)
	elif isinstance(param, click.Argument) and param.name:
		names.append(param.name)

	return any(looks_like_path_name(name) for name in names)
