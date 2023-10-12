# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "console"))

project = 'sigil-console'
copyright = '2023, ChenyangGao'
author = 'ChenyangGao <https://chenyanggao.github.io/>'
release = '0.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosectionlabel",
    # external
    "sphinx_copybutton",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
todo_include_todos = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_title = "sigil-console"
html_static_path = ['_static']

intersphinx_mapping = {
    "python": ("https://docs.python.org/", None),
}

copybutton_prompt_text = (
    r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
)
copybutton_prompt_is_regexp = True
autoclass_content = "both"
