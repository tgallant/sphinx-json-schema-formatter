"""
JSON schema loader helpers
"""

from collections import Mapping
from copy import deepcopy


def merge(base, to_merge, mode):
    if mode == 'allOf':
        merge_and(base, to_merge)
    elif mode in ['oneOf', 'anyOf']:
        merge_or(base, to_merge, exclusive=(mode == 'oneOf'))
    else:
        raise RuntimeError('Merging mode "%s" is not supported yet' % mode)

def merge_and(base, to_merge, neg=False):
    """
    Merge json schemas assuming an 'allOf' command
    """
    if not base:
        return to_merge

    to_pop = []
    for key, val in base.items():
        if key in ['$or', '$xor']:
            for v in val:
                merge_and(v, to_merge, neg)
        elif key == 'not':
            merge_and(to_merge, val, True)
        elif isinstance(val, Mapping):
            try:
                if neg and to_merge[key] == val:
                    to_pop.append(key)
                else:
                    merge_and(val, to_merge[key], neg)
            except KeyError:
                pass
        elif isinstance(val, list):
            try:
                other_val = to_merge[key]
                if not isinstance(other_val, list):
                    raise KeyError
                if key == 'enum':
                    if neg:
                        s = set(val).intersection(other_val)
                    else:
                        s = set(val).symmetric_difference(other_val)
                    for v in s:
                        val.remove(v)
                elif key == 'required':
                    if neg:
                        for v in other_val:
                            val.remove(v)
                    else:
                        for v in other_val:
                            if v not in val:
                                val.append(v)
            except KeyError:
                base[key] = val
        else:
            # normal update
            try:
                if neg and key not in ['type', 'description']:
                    base[key] = {
                        'not': to_merge[key]
                    }
                else:
                    base[key] = to_merge[key]
            except KeyError:
                pass

    for key in set(to_merge.keys()).difference(base.keys()):
        if key in ['$or', '$xor']:
            try:
                alternatives = base[key]
            except KeyError:
                alternatives = [{}]
                base[key] = alternatives
            for v in to_merge.pop(key):
                b = deepcopy(base)
                merge_and(b, v)
                alternatives.append(v)
        elif key == 'not':
            merge_and(base, to_merge[key], True)
        else:
            if neg and key not in ['type', 'description']:
                base[key] = {
                    'not': to_merge[key]
                }
            else:
                base[key] = to_merge[key]

    for key in to_pop:
        base.pop(key)

    return base


def merge_or(base, to_merge, exclusive):
    """
    Merge json schemas assuming a 'oneOf' or 'anyOf' command

    The idea is to find out the differences between 'base' and 'to_merge'.
    If a property is in 'base' and not in 'to_merge', it is added to all the alternative
    properties except 'to_merge'.
    If a property is in 'base' and in 'to_merge', it's removed from 'to_merge' and 'base' is left
    as is
    """

    operand = '$%sor' % ('x' if exclusive else '')

    if not base:
        return {
            operand: [
                {},
                to_merge
            ]
        }

    try:
        alternatives = base[operand]
    except KeyError:
        alternatives = [{}]
        base[operand] = alternatives


    for key in set(base.keys()).difference(to_merge.keys()):
        if key.startswith('$'):
            # do not process special keys
            continue
        # keys that are in base but not in to_merge
        val = base.pop(key)
        for a in alternatives:
            a[key] = val

    for key in set(to_merge.keys()).intersection(base.keys()):
        if key.startswith('%'):
            # do not process special keys
            continue
        # keys that are both in base and to_merge
        if key == 'properties':
            prop_base = base.get(key, {})
            prop_mrg = to_merge[key]
            for p in set(prop_mrg.keys()).intersection(prop_base.keys()):
                prop_mrg.pop(p)
        elif key == 'required':
            req_mrg = to_merge[key]
            for p in set(req_mrg).intersection(base.get(key, [])):
                req_mrg.remove(p)
        else:
            if to_merge[key] == base.get(key, None):
                to_merge.pop(key)

    alternatives.append(to_merge)

    return base
