# Copyright (c) 2024 Patricio Cubillos
# Gen TSO is open-source software under the GPL-2.0 license (see LICENSE)

__all__ = [
    'find_target',
    'Catalog',
    'load_targets',
    'load_trexolist_table',
    'load_aliases',
]

from astropy.io import ascii
import numpy as np
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from ..utils import ROOT
from . import utils as u


def find_target(targets=None):
    """
    Interactive prompt with tab-completion to search for targets.
    """
    if targets is None:
        targets = load_targets('nea_data.txt')
    confirmed_planets = [target.planet for target in targets]

    completer = WordCompleter(
        confirmed_planets,
        sentence=True,
        match_middle=True,
    )
    planet = prompt(
        'Enter Planet name: ',
        completer=completer,
        complete_while_typing=False,
    )
    if planet in confirmed_planets:
        target = targets[confirmed_planets.index(planet)]

    return target


class Catalog():
    """
    Load the entire catalog.

    Examples
    --------
    >>> import gen_tso.catalogs as cat
    >>> catalog = cat.Catalog()
    """
    def __init__(self):
        # Confirmed planets and TESS candidates
        nea_data = load_targets_table('nea_data.txt')
        tess_data = load_targets_table('tess_data.txt')

        confirmed_planets = nea_data[0]
        tess_planets = tess_data[0]
        self.planets = confirmed_planets + tess_planets

        self.hosts = nea_data[1] + tess_data[1]
        self.ra = nea_data[2] + tess_data[2]
        self.dec = nea_data[3] + tess_data[3]
        self.ks_mag = nea_data[4] + tess_data[4]
        self.teff = nea_data[5] + tess_data[5]
        self.log_g = nea_data[6] + tess_data[6]
        self.tr_dur = nea_data[7] + tess_data[7]
        self.rprs = nea_data[8] + tess_data[8]
        self.teq = nea_data[9] + tess_data[9]

        # JWST targets
        jwst_targets, trexo_ra, trexo_dec = u.get_trexolists_targets(
            extract='coords',
        )
        njwst = len(jwst_targets)
        host_aliases = load_aliases(as_hosts=True)
        hosts_aka = u.invert_aliases(host_aliases)
        for i in range(njwst):
            if jwst_targets[i] in host_aliases:
                jwst_targets[i] = host_aliases[jwst_targets[i]]
            # if host NEA name != planet NEA name
            if jwst_targets[i] not in self.hosts:
                for host in hosts_aka[jwst_targets[i]]:
                    if host in self.hosts:
                        jwst_targets[i] = host

        self.planet_aliases = load_aliases()
        planets_aka = u.invert_aliases(self.planet_aliases)

        self.nplanets = nplanets = len(self.planets)
        self.is_transiting = np.zeros(nplanets, bool)
        self.is_jwst = np.zeros(nplanets, bool)
        self.is_confirmed = np.zeros(nplanets, bool)
        self.trexo_coords = [None for _ in self.planets]
        self.jwst_aliases = []
        self.transit_aliases = []
        self.non_transit_aliases = []
        self.confirmed_aliases = []
        self.candidate_aliases = []

        for i,target in enumerate(self.planets):
            self.is_transiting[i] = self.tr_dur[i] is not None
            self.is_confirmed[i] = target not in tess_planets
            self.is_jwst[i] = (
                self.hosts[i] in jwst_targets and
                self.is_transiting[i]
            )

            # Now get the aliases lists:
            if target not in planets_aka:
                continue
            aliases = planets_aka[target]

            if self.is_jwst[i]:
                self.jwst_aliases += aliases
                j = list(jwst_targets).index(self.hosts[i])
                self.trexo_coords[i] = (trexo_ra[j], trexo_dec[j])

            if self.is_transiting[i]:
                self.transit_aliases += aliases
            else:
                self.non_transit_aliases += aliases

            if self.is_confirmed[i]:
                self.confirmed_aliases += aliases
            else:
                self.candidate_aliases += aliases

    def show_target(self, target):
        target = u.normalize_name(target)
        # TBD


def load_targets(database='nea_data.txt'):
    """
    Unpack star and planet properties from plain text file.

    Parameters
    ----------
    databases: String
        nea_data.txt or tess_data.txt

    Returns
    -------
    targets: List of Target

    Examples
    --------
    >>> import gen_tso.catalogs as cat
    >>> nea_data = cat.load_nea_targets_table()
    """
    # database = 'new_nea_data.txt'
    with open(f'{ROOT}data/{database}', 'r') as f:
        lines = f.readlines()

    lines = [
        line for line in lines
        if not line.strip().startswith('#')
    ]
    targets = []
    for line in lines:
        if line.startswith('>'):
            name_len = line.find(':')
            host = line[1:name_len]
            star_vals = np.array(line[name_len+1:].split(), float)
            ra, dec, ks_mag, rstar, mstar, teff, logg, metal = star_vals
        elif line.startswith(' '):
            name_len = line.find(':')
            planet = line[1:name_len].strip()
            planet_vals = np.array(line[name_len+1:].split(), float)
            transit_dur, rplanet, mplanet, sma, period, teq = planet_vals

            target = Target(
                host=host,
                mstar=mstar, rstar=rstar, teff=teff, logg_star=logg,
                metal_star=metal,
                ks_mag=ks_mag, ra=ra, dec=dec,
                planet=planet,
                mplanet=mplanet, rplanet=rplanet,
                period=period, sma=sma, transit_dur=transit_dur,
            )
            targets.append(target)

    return targets


def load_trexolist_table():
    """
    Get the list of targets in trexolists (as named at the NEA).
    A dictionary of name aliases contains alternative names found.

    Returns
    -------
    jwst_targets: List
        trexolists host names as found in the NEA database.
    aliases: Dict
        An aliases dict that takes trexolists name to NEA name.
    missing: List
        trexolists hosts not found in the NEA database.
    original_names: Dict
        Names of targets as listed in the trexolists database.

    Examples
    --------
    >>> import gen_tso.catalogs as cat
    >>> targets, aliases, missing, og = cat.load_trexolist_table()
    """
    trexolist_data = ascii.read(
        f'{ROOT}data/trexolists.csv',
        format='csv', guess=False, fast_reader=False, comment='#',
    )
    targets = np.unique(trexolist_data['Target'].data)

    original_names = {}
    norm_targets = []
    for target in targets:
        name = u.normalize_name(target)
        norm_targets.append(name)
        if name not in original_names:
            original_names[name] = []
        original_names[name] += [target]
    norm_targets = np.unique(norm_targets)

    # jwst targets that are in NEA catalog:
    nea_targets = load_targets_table('nea_data.txt')
    tess_targets = load_targets_table('tess_data.txt')
    hosts = list(nea_data[1]) + list(tess_data[1])

    aliases = load_aliases(as_hosts=True)
    for host in hosts:
        aliases[host] = host

    # As named in NEA catalogs:
    jwst_aliases = {}
    missing = []
    for target in norm_targets:
        if target in aliases:
            jwst_aliases[target] = aliases[target]
        elif target.endswith(' A') and target[:-2] in aliases:
            jwst_aliases[target] = aliases[target[:-2]]
        else:
            missing.append(target)
    for name in list(jwst_aliases.values()):
        jwst_aliases[name] = name

    # TBD: Check this does not break for incomplete lists
    trexo_names = {}
    for name in original_names:
        alias = jwst_aliases[name]
        if alias not in trexo_names:
            trexo_names[alias] = []
        trexo_names[alias] += original_names[name]

    jwst_targets = np.unique(list(jwst_aliases.values()))
    return jwst_targets, jwst_aliases, np.unique(missing), trexo_names


def load_aliases(as_hosts=False):
    """
    Load file with known aliases of NEA targets.
    """
    with open(f'{ROOT}data/nea_aliases.txt', 'r') as f:
        lines = f.readlines()

    def parse(name):
        if not as_hosts:
            return name
        if u.is_letter(name):
            return name[:-2]
        end = name.rindex('.')
        return name[:end]

    aliases = {}
    for line in lines:
        loc = line.index(':')
        name = parse(line[:loc])
        for alias in line[loc+1:].strip().split(','):
            if parse(alias) != name:
                aliases[parse(alias)] = name
    return aliases
