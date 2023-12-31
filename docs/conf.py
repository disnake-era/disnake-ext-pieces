# SPDX-License-Identifier: LGPL-3.0-only

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

from pathlib import Path
import re
import os
import sys

project = "disnake-ext-pieces"
copyright = "2022-2023, Chromosomologist, 2023-present, elenakrittik"
author = "elenakrittik"

version = ""
with open("../disnake/ext/pieces/__init__.py") as f:
    matches = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE)

    if not matches:
        raise RuntimeError( \
            "Could not find version string in disnake/ext/pieces/__init__.py" \
        )

    version = matches.group(1)

release = version

github_repo_url = "https://github.com/disnake-era/disnake-ext-pieces"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.towncrier.ext",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

sys.path.insert(0, os.path.abspath(".."))

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"

# sphinxcontrib-towncrier config
towncrier_draft_autoversion_mode = "draft"
towncrier_draft_include_empty = False
towncrier_draft_working_directory = Path(__file__).parent.parent

extlinks = {
    "issue": (f"{github_repo_url}/issues/%s", "#%s"),
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "disnake": ("https://docs.disnake.dev/en/stable/", None),
}
