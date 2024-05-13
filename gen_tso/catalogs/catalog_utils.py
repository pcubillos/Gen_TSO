# Copyright (c) 2024 Patricio Cubillos
# Gen TSO is open-source software under the GPL-2.0 license (see LICENSE)

"""
A collection of low-level routines to handle catalogs.
"""

__all__ = [
    'normalize_name',
    'get_trexolists_targets',
    'is_letter',
    'is_candidate',
    'get_letter',
    'to_float',
    'select_alias',
    'invert_aliases',
]

import re

from astropy.io import ascii
import numpy as np

from ..utils import ROOT


def normalize_name(target):
    """
    Normalize target names into a 'more standard' format.
    Mainly to resolve trexolists target names.
    """
    name = re.sub(r'\s+', ' ', target)
    # It's a case issue:
    name = name.replace('KEPLER', 'Kepler')
    name = name.replace('TRES', 'TrES')
    name = name.replace('WOLF-', 'Wolf ')
    name = name.replace('HATP', 'HAT-P-')
    name = name.replace('AU-MIC', 'AU Mic')
    # Prefixes
    name = name.replace('GL', 'GJ')
    prefixes = [
        'L', 'G', 'HD', 'GJ', 'LTT', 'LHS', 'HIP', 'WD', 'LP', '2MASS', 'PSR',
    ]
    for prefix in prefixes:
        prefix_len = len(prefix)
        if name.startswith(prefix) and not name[prefix_len].isalpha():
            name = name.replace(f'{prefix}-', f'{prefix} ')
            if name[prefix_len] != ' ':
                name = f'{prefix} ' + name[prefix_len:]

    prefixes = ['CD-', 'BD-', 'BD+']
    for prefix in prefixes:
        prefix_len = len(prefix)
        dash_loc = name.find('-', prefix_len)
        if name.startswith(prefix) and dash_loc > 0:
            name = name[0:dash_loc] + ' ' + name[dash_loc+1:]
    # Main star
    if name.endswith('A') and not name[-2].isspace():
        name = name[:-1] + ' A'
    # Custom corrections:
    if name in ['55CNC', 'RHO01-CNC']:
        name = '55 Cnc'
    name = name.replace('-offset', '')
    name = name.replace('-updated', '')
    if name.endswith('-'):
        name = name[:-1]
    if name == 'WD 1856':
        name = 'WD 1856+534'
    if 'V1298' in name:
        name = 'V1298 Tau'
    return name


def get_trexolists_targets(trexo_file=None, extract='Target'):
    """
    Get the target names from the trexolists.csv file.
    """
    if trexo_file is None:
        trexo_file = f'{ROOT}data/trexolists.csv'

    trexolist_data = ascii.read(
        trexo_file,
        format='csv', guess=False, fast_reader=False, comment='#',
    )

    targets = trexolist_data['Target'].data
    ra = trexolist_data['R.A. 2000'].data
    dec = trexolist_data['Dec. 2000'].data
    truncated_ra = [r[0:7] for r in ra]
    truncated_dec = [d[0:6] for d in dec]

    # Detect aliases for a same object
    ntargets = len(targets)
    taken = np.zeros(ntargets, bool)
    for i in range(ntargets):
        if taken[i]:
            continue
        ra = truncated_ra[i]
        dec = truncated_dec[i]
        taken[i] = True
        hosts = [targets[i]]
        for j in range(i,ntargets):
            if truncated_ra[j]==ra and truncated_dec[j]==dec and not taken[j]:
                hosts.append(targets[j])
                taken[j] = True
        # print(f'{ra}  {dec}   {np.unique(hosts)}')

    norm_targets = [
        normalize_name(target)
        for target in targets
    ]
    return np.unique(norm_targets)


def is_letter(name):
    """
    Check if name ends with a blank + lower-case letter (it's a planet)
    """
    return name[-1].islower() and name[-2] == ' '


def is_candidate(name):
    """
    Check if name ends with a blank + lower-case letter (it's a planet)
    """
    return name[-3] == '.' and name[-2:].isnumeric()


def get_letter(name):
    """
    Extract 'letter' identifier for a planet name.
    Valid confirmed planet names end with a lower-case letter preceded
    by a blank.  Valid planet candidate names end with a dot followed
    by two numbers.

    Examples
    --------
    >>> get_letter('TOI-741.01')
    >>> get_letter('WASP-69 b')
    """
    if is_letter(name):
        return name[-2:]
    if '.' in name:
        idx = name.rfind('.')
        return name[idx:]
    return ''


def select_alias(aka, catalogs, default_name=None):
    """
    Search alternative names take first one found in catalogs list.
    """
    for catalog in catalogs:
        for alias in aka:
            if alias.startswith(catalog):
                return alias
    return default_name


def invert_aliases(aliases):
    """
    Invert an {alias:name} dictionary into {name:aliases_list}
    """
    aka = {}
    for key,val in aliases.items():
        if val not in aka:
            aka[val] = []
        aka[val].append(key)
    return aka


def to_float(value):
    """
    Cast string to None or float type.
    """
    if value == 'None':
        return None
    return float(value)


