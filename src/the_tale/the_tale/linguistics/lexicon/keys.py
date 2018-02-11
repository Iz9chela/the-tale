
import os
import copy

import rels

from dext.common.utils import discovering

from . import relations


def get_key_records():
    CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
    GROUPS_DIR = os.path.join(CURRENT_DIR, 'groups')

    keys = []

    for module in discovering.discover_modules_in_directory(GROUPS_DIR, 'the_tale.linguistics.lexicon.groups'):

        for key in getattr(module, 'KEYS', ()):
            key = copy.deepcopy(key)

            additional_variables = []

            for variable in key[5]:
                for attribute in variable.type.attributes:
                    additional_variables.append(relations.VARIABLE('{}.{}'.format(variable.value, attribute)))

            key[5].extend(additional_variables)

            keys.append(key)

    return keys


class LEXICON_KEY(rels.Relation):
    name = rels.Column(primary=True, no_index=True)
    value = rels.Column(external=True, no_index=True)
    text = rels.Column(unique=False)
    group = rels.Column(unique=False)
    description = rels.Column(unique=False)
    variables = rels.Column(unique=False, no_index=True)
    ui_text = rels.Column(unique=False, no_index=True, single_type=False)

    records = get_key_records()
