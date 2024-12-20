from collections.abc import Iterator, Sequence
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, is_undefined
from pydantic import DirectoryPath, FilePath, validate_call

from sereto.exceptions import SeretoValueError
from sereto.utils import replace_strings

MANUAL_EDIT_WARNING = (
    "WARNING: This file was generated from a Jinja2 template. Any manual edits made to this file may be overwritten "
    "without warning. To make changes, please edit the corresponding Jinja2 template file instead."
)


def tex_escape_filter(text: Any, default: str = "n/a") -> str:
    """Escape special characters in text for use in TeX.

    This function serves as a Jinja2 filter to escape special characters in `text` for use in TeX. It replaces each
    special character with its corresponding TeX escape sequence. The `default` argument can be used to specify a
    default value to return if `text` is undefined or empty.

    Args:
        text: The text to be escaped.
        default: The default value to return if `text` is undefined or empty. Defaults to 'n/a'.

    Returns:
        The escaped text.
    """
    if is_undefined(text) or not text:
        text = default

    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\^{}",
        "\\": r"\textbackslash{}",
        "<": r"\textless{}",
        ">": r"\textgreater{}",
    }
    return replace_strings(str(text), replacements=replacements)


def yesno_filter(value: str | None, arg: str = "yes,no,maybe") -> str:
    """Tex filter for converting boolean values to strings.

    Given a string mapping values for true, false, and (optionally) None,
    return one of those strings according to the value:
    ==========  ======================  ==================================
    Value       Argument                Outputs
    ==========  ======================  ==================================
    ``True``    ``"yeah,no,maybe"``     ``yeah``
    ``False``   ``"yeah,no,maybe"``     ``no``
    ``None``    ``"yeah,no,maybe"``     ``maybe``
    ``None``    ``"yeah,no"``           ``"no"`` (converts None to False
                                        if no mapping for None is given.
    ==========  ======================  ==================================
    """
    bits = arg.split(",")
    if len(bits) < 2 or len(bits) > 3:
        raise SeretoValueError("invalid argument")
    try:
        yes, no, maybe = bits
    except ValueError:
        # Unpack list of wrong size (no "maybe" value provided).
        yes, no, maybe = bits[0], bits[1], bits[1]
    if value is None:
        return maybe
    if value:
        return yes
    return no


@validate_call
def get_generic_jinja_env(templates: DirectoryPath | Sequence[DirectoryPath]) -> Environment:
    """Creates a generic Jinja2 environment object.

    Args:
        templates: The directory/directories containing template files.

    Returns:
        A Jinja2 environment object.
    """
    env: Environment = Environment(autoescape=False, loader=FileSystemLoader(templates))
    env.globals["MANUAL_EDIT_WARNING"] = MANUAL_EDIT_WARNING
    env.add_extension("jinja2.ext.debug")
    return env


@validate_call
def get_tex_jinja_env(templates: DirectoryPath | Sequence[DirectoryPath]) -> Environment:
    """Creates a Jinja2 environment object for rendering TeX templates.

    Args:
        templates: The directory/directories containing the TeX template files.

    Returns:
        A Jinja2 environment object that is configured for rendering TeX templates.
    """
    env: Environment = Environment(
        block_start_string="((*",
        block_end_string="*))",
        variable_start_string="(((",
        variable_end_string=")))",
        comment_start_string="((=",
        comment_end_string="=))",
        autoescape=False,
        loader=FileSystemLoader(templates),
    )

    # TODO: Once Jinja2 allows custom escape functions, we might use autoescape of special TeX characters.
    env.filters["tex"] = tex_escape_filter
    env.filters["yesno"] = yesno_filter
    env.globals["MANUAL_EDIT_WARNING"] = MANUAL_EDIT_WARNING
    env.add_extension("jinja2.ext.debug")

    return env


@validate_call
def render_jinja2(
    file: FilePath, templates: DirectoryPath | Sequence[DirectoryPath], vars: dict[str, Any]
) -> Iterator[str]:
    """Renders a Jinja2 template.

    Args:
        file: The path to the template file to be rendered.
        templates: The directory/directories containing the template files.
        vars: A dictionary of variables to be passed to the Jinja2 template engine.

    Returns:
        A generator that yields the rendered template as a string.
    """
    if file.name.endswith(".tex.j2"):
        env: Environment = get_tex_jinja_env(templates=templates)
    elif file.name.endswith(".j2"):
        env = get_generic_jinja_env(templates=templates)
    else:
        raise SeretoValueError("unsupported file type")

    template: Template = env.get_template(name=file.name)

    return template.generate(vars)
