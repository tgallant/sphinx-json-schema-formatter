# -*- coding: utf-8 -*-


import os.path

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.directives.code import container_wrapper

from .loader import JsonSchemaLoader


class JsonSchema(Directive):
    optional_arguments = 1
    has_content = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        assert self.name == 'jsonschema'

        try:
            file_or_url = self.arguments[0]
            if not file_or_url.startswith('http') and not os.path.isabs(file_or_url):
                # file relative to the path of the current rst file
                dname = os.path.dirname(self.state_machine.input_lines.source(0))
                path = os.path.join(dname, file_or_url)
                if os.path.exists(path):
                    file_or_url = path
                else:
                    root_dir = self.state.document.settings.env.config.jsonschema_root_dir
                    if root_dir is None:
                        raise IndexError
                    # no file at relative location, try loading from root directory
                    file_or_url = os.path.join(root_dir, file_or_url)
        except IndexError:
            file_or_url = None

        self.schema = JsonSchemaLoader(
            *(file_or_url,) or (self.content, self.state_machine.input_lines.source(0))
        )

    def run(self):
        code = self.schema.render()
        literal = nodes.literal_block(code, code)
        literal['language'] = 'json'
        # add a caption
        literal = container_wrapper(self, literal, 'JSON schema' + self.schema.version)
        return [literal]
