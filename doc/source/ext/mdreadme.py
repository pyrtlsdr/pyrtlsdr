"""Override of myst_parser.docutils_ module to enable ``linkify`` extension

Currently only used for ``doc/source/Overview.rst`` to render ``README.md``.
Very hackish, but easier than sifting through docutils to find correct config
injection method.

https://github.com/executablebooks/MyST-Parser/blob/v0.15.2/myst_parser/docutils_.py
"""

from docutils import nodes
from markdown_it.token import Token
from markdown_it.utils import AttrDict
from myst_parser.main import MdParserConfig, default_parser
from myst_parser.docutils_ import Parser as _Parser


class Parser(_Parser):

    def parse(self, inputstring: str, document: nodes.document) -> None:
        """Parse source text.
        :param inputstring: The source string to parse
        :param document: The root docutils node to add AST elements to
        """
        config = MdParserConfig(renderer="docutils", enable_extensions=['linkify'])
        parser = default_parser(config)
        parser.options["document"] = document
        env = AttrDict()

        tokens = parser.parse(inputstring, env)
        if not tokens or tokens[0].type != "front_matter":
            # we always add front matter, so that we can merge it with global keys,
            # specified in the sphinx configuration
            tokens = [Token("front_matter", "", 0, content="{}", map=[0, 0])] + tokens
        parser.renderer.render(tokens, parser.options, env)
