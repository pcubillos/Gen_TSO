# Copyright (c) 2024 Patricio Cubillos
# Gen TSO is open-source software under the GPL-2.0 license (see LICENSE)

__all__ = [
    'fetch_trexolits',
    'fetch_nea_confirmed_targets',
    'fetch_nea_tess_candidates',
    'fetch_nea_aliases',
    'fetch_simbad_aliases',
    'fetch_vizier_ks',
    'fetch_aliases',
    'fetch_tess_aliases',
]

import multiprocessing as mp
from datetime import date
import urllib
import pickle
import warnings
import re

import numpy as np
import requests
from astroquery.simbad import Simbad as simbad
from astroquery.vizier import Vizier
from astropy.table import Table
import astropy.units as u
from bs4 import BeautifulSoup
import pyratbay.constants as pc
import pyratbay.atmosphere as pa

# For developing
if False:
    from gen_tso.utils import ROOT
    from gen_tso.catalogs.source_catalog import (
        load_targets_table,
        load_trexolits_table,
        normalize_name,
    )

from .source_catalog import (
    load_targets_table,
    load_trexolits_table,
    normalize_name,
)
from ..utils import ROOT


def update_databases():
    # Update trexolist database
    fetch_trexolits()

    # Update NEA confirmed targets and their aliases
    fetch_nea_confirmed_targets()
    nea_data = load_targets_table()
    hosts = np.unique(nea_data[1])
    output_file = f'{ROOT}data/nea_aliases.pickle'
    fetch_aliases(hosts, output_file)

    # Update NEA TESS candidates and their aliases
    fetch_nea_tess_candidates()
    fetch_tess_aliases()

    # Update aliases list
    curate_aliases()


def is_letter(name):
    """
    Check if name ends with a blank + lower-case letter (it's a planet)
    """
    return name[-1].islower() and name[-2] == ' '


def curate_aliases():
    """
    Thin down all_aliases.pickle file to the essentials.
    Save as .txt, which is shipped with gen_tso.
    """
    with open(f'{ROOT}data/nea_aliases.pickle', 'rb') as handle:
        aliases = pickle.load(handle)
    #  718
    with open(f'{ROOT}data/tess_aliases.pickle', 'rb') as handle:
        tess_aliases = pickle.load(handle)
    aliases.update(tess_aliases)

    jwst_hosts, jwst_aliases, missing, og = load_trexolits_table(
        all_aliases=True,
    )

    prefixes = list(jwst_aliases.keys())
    prefixes += ['WASP', 'KELT', 'HAT', 'MASCARA', 'TOI', 'XO', 'TrES']
    kept_aliases = {}
    for alias,name in aliases.items():
        if alias == name:
            continue
        for prefix in prefixes:
            #if alias.startswith(prefix) and not name.startswith(prefix):
            if alias.startswith(prefix):
                #if name == 'HIP 45908':
                #    print(f'{name}: {alias}')
                if not is_letter(name):
                    #print(name, alias)
                    continue
                kept_aliases[alias] = name

    aka = {}
    for alias, name in kept_aliases.items():
        if name not in aka:
            aka[name] = []
        aka[name] += [alias]

    to_remove = []
    for name, aliases in aka.items():
        # remove .0N if letter exist:
        any_letter = np.any([is_letter(val) for val in aliases])
        if any_letter:
            aliases = [alias for alias in aliases if is_letter(alias)]
        # Remove TOI-XX.0N when name is TOI-XX letter:
        if name.startswith('TOI') and is_letter(name):
            aliases = [
                alias for alias in aliases
                if not (alias.startswith('TOI') and not is_letter(alias))
            ]
        aka[name] = aliases

        if len(aliases) == 0:
            to_remove.append(name)

    for name in to_remove:
        aka.pop(name)

    with open(f'{ROOT}/data/nea_aliases.txt', 'w') as f:
        for name,aliases in aka.items():
            str_aliases = ','.join(aliases)
            f.write(f'{name}:{str_aliases}\n')



def as_str(val, fmt):
    """
    Utility function
    """
    if val is None:
        return None
    return f'{val:{fmt}}'


def fetch_trexolits():
    url = 'https://www.stsci.edu/~nnikolov/TrExoLiSTS/JWST/trexolists.csv'
    query_parameters = {}
    response = requests.get(url, params=query_parameters)

    if not response.ok:
        raise ValueError('Could not download TrExoLiSTS database')

    trexolists_path = f'{ROOT}data/trexolists.csv'
    with open(trexolists_path, mode="wb") as file:
        file.write(response.content)

    today = date.today()
    with open(f'{ROOT}data/last_updated_trexolits.txt', 'w') as f:
        f.write(f'{today.year}_{today.month:02}_{today.day:02}')


def rank_planets(entries):
    """
    Rank entries with the most data
    """
    points = [
        (
            (entry['st_teff'] is None) +
            (entry['st_logg'] is None) +
            (entry['st_met'] is None) +
            (entry['pl_trandur'] is None) +
            (entry['pl_rade'] is None) +
            (entry['pl_orbsmax'] is None and entry['pl_ratdor'] is None) +
            (entry['st_rad'] is None and entry['pl_ratror'] is None)
        )
        for entry in entries
    ]
    rank = np.argsort(np.array(points))
    return rank


def solve_period_sma(period, sma, mstar):
    """
    Solve period-sma-mstar system values.
    """
    if mstar is None or mstar == 0:
        return period, sma
    if period is None and sma is not None:
        period = (
            2.0*np.pi * np.sqrt((sma*pc.au)**3.0/pc.G/(mstar*pc.msun)) / pc.day
        )
    elif sma is None and period is not None:
        sma = (
            ((period*pc.day/(2.0*np.pi))**2.0*pc.G*mstar*pc.msun)**(1/3) / pc.au
        )
    return period, sma


def solve_rp_rs(rp, rs, rprs):
    if rp is None and rs is not None and rprs is not None:
        rp = rprs * (rs*pc.rsun) / pc.rearth
    if rs is None and rp is not None and rprs is not None:
        rs = rp*pc.rearth / rprs / pc.rsun
    if rprs is None and rp is not None and rs is not None:
        rprs = rp*pc.rearth / (rs*pc.rsun)
    return rp, rs, rprs

def solve_a_rs(a, rs, ars):
    if a is None and rs is not None and ars is not None:
        a = ars * (rs*pc.rsun) / pc.au
    if rs is None and a is not None and ars is not None:
        rs = a*pc.au / ars / pc.rsun
    if ars is None and a is not None and rs is not None:
        ars = a*pc.au / (rs*pc.rsun)
    return a, rs, ars


def complete_entry(entry):
    entry['pl_rade'], entry['st_rad'], entry['pl_ratror'] = solve_rp_rs(
        entry['pl_rade'], entry['st_rad'], entry['pl_ratror'],
    )
    entry['pl_orbsmax'], entry['st_rad'], entry['pl_ratdor'] = solve_a_rs(
        entry['pl_orbsmax'], entry['st_rad'], entry['pl_ratdor'],
    )
    entry['pl_orbper'], entry['pl_orbsmax'] = solve_period_sma(
        entry['pl_orbper'], entry['pl_orbsmax'], entry['st_mass']
    )
    return entry


def fetch_nea_confirmed_targets():
    """
    Fetch (web request) the entire NASA Exoplanet Archive database
    """
    # Fetch all planetary system entries
    r = requests.get(
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
        "select+hostname,pl_name,default_flag,sy_kmag,sy_pnum,disc_facility,"
        "ra,dec,st_teff,st_logg,st_met,st_rad,st_mass,st_age,"
        "pl_trandur,pl_orbper,pl_orbsmax,pl_rade,pl_masse,pl_ratdor,pl_ratror+"
        "from+ps+"
        "&format=json"
    )
    if not r.ok:
        raise ValueError("Something's not OK")

    resp = r.json()
    host_entries = [entry['hostname'] for entry in resp]
    hosts, counts = np.unique(host_entries, return_counts=True)

    planet_entries = np.array([entry['pl_name'] for entry in resp])
    planet_names, idx, counts = np.unique(
        planet_entries,
        return_index=True,
        return_counts=True,
    )
    nplanets = len(planet_names)

    # Make list of unique entries
    planets = [resp[i].copy() for i in idx]
    for i in range(nplanets):
        planet = planets[i]
        name = planet['pl_name']
        idx_duplicates = np.where(planet_entries==name)[0]
        # default_flag takes priority
        def_flags = [resp[j]['default_flag'] for j in idx_duplicates]
        j = idx_duplicates[def_flags.index(1)]
        planets[i] = complete_entry(resp[j].copy())
        dups = [resp[k] for k in idx_duplicates if k!=j]
        rank = rank_planets(dups)
        # Fill the gaps if any
        for j in rank:
            entry = complete_entry(dups[j])
            for field in planet.keys():
                if planets[i][field] is None and entry[field] is not None:
                    planets[i][field] = entry[field]
        planets[i] = complete_entry(planets[i])

    # Save as plain text:
    with open(f'{ROOT}data/nea_data.txt', 'w') as f:
        host = ''
        for entry in planets:
            ra = entry['ra']
            dec = entry['dec']
            ks_mag = entry['sy_kmag']
            planet = entry['pl_name']
            tr_dur = entry['pl_trandur']
            teff = as_str(entry['st_teff'], '.1f')
            logg = as_str(entry['st_logg'], '.3f')
            rprs = as_str(entry['pl_ratror'], '.3f')
            missing_info = (
                entry['st_teff'] is None or
                entry['st_rad'] is None or
                entry['pl_orbsmax'] is None
            )
            if missing_info:
                teq = 'None'
            else:
                teq, _ = pa.equilibrium_temp(
                    entry['st_teff'],
                    entry['st_rad']*pc.rsun,
                    entry['pl_orbsmax']*pc.au,
                )
                teq = f'{teq:.1f}'

            if entry['hostname'] != host:
                host = entry['hostname']
                f.write(f">{host}: {ra} {dec} {ks_mag} {teff} {logg}\n")
            f.write(f" {planet}: {tr_dur} {rprs} {teq}\n")

    today = date.today()
    with open(f'{ROOT}data/last_updated_nea.txt', 'w') as f:
        f.write(f'{today.year}_{today.month:02}_{today.day:02}')



def fetch_nea_aliases(target):
    """
    Fetch target aliases as known by https://exoplanetarchive.ipac.caltech.edu/
    This one is quite slow, it would be great if one could do a batch search.

    Examples
    --------
    >>> from gen_tso.catalogs.update_catalogs import fetch_nea_aliases
    >>> aliases = fetch_nea_aliases('WASP-69b')
    """
    query = urllib.parse.quote(target)
    r = requests.get(
        'https://exoplanetarchive.ipac.caltech.edu/cgi-bin/Lookup/'
        f'nph-aliaslookup.py?objname={query}'
    )
    if not r.ok:
        #raise ValueError("Alias fetching for '{target}' failed")
        print(f"Alias fetching failed for '{target}'")
        return {}
    resp = r.json()

    if resp['manifest']['lookup_status'] == 'System Not Found':
        print(f"NEA alias not found for '{target}'")
        return {}

    aliases = {}
    star_set = resp['system']['objects']['stellar_set']['stars']
    for star in star_set.keys():
        if 'is_host' not in star_set[star]:
            continue
        for alias in star_set[star]['alias_set']['aliases']:
            aliases[alias] = star
        # Do not fetch Simbad aliases here because too many requests
        # break the code

    planet_set = resp['system']['objects']['planet_set']['planets']
    for planet in planet_set.keys():
        for alias in planet_set[planet]['alias_set']['aliases']:
            aliases[alias] = planet
    return aliases


def fetch_simbad_aliases(target, verbose=True):
    """
    Fetch target aliases and Ks magnitude as known by Simbad.

    Examples
    --------
    >>> from gen_tso.catalogs.update_catalogs import fetch_simbad_aliases
    >>> aliases, ks_mag = fetch_simbad_aliases('WASP-69b')
    """
    simbad.reset_votable_fields()
    simbad.remove_votable_fields('coordinates')
    simbad.add_votable_fields("otype", "otypes", "ids")
    simbad.add_votable_fields("flux(K)")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        simbad_info = simbad.query_object(target)
    if simbad_info is None:
        if verbose:
            print(f'no Simbad entry for target {repr(target)}')
        return [], None

    object_type = simbad_info['OTYPE'].value.data[0]
    if 'Planet' in object_type:
        if target[-1].isalpha():
            host = target[:-1]
        elif '.' in target:
            end = target.rindex('.')
            host = target[:end]
        else:
            target_id = simbad_info['MAIN_ID'].value.data[0]
            print(f'Wait, what?:  {repr(target)}  {repr(target_id)}')
            return [], None
        # go after star
        simbad_info = simbad.query_object(host)
        if simbad_info is None:
            if verbose:
                print(f'Simbad host {repr(host)} not found')
            return [], None

    host_info = simbad_info['IDS'].value.data[0]
    host_alias = host_info.split('|')
    kmag = simbad_info['FLUX_K'].value.data[0]
    if not np.isfinite(kmag):
        kmag = None
    return host_alias, kmag


def fetch_vizier_ks(target, verbose=True):
    """
    Query for a target in the 2MASS catalog via Vizier.

    Returns
    -------
    Ks_mag: Float
        The target's Ks magnitude.
        Return None if the target was not found in the catalog or
        could not be uniquely identified.

    Examples
    --------
    >>> fetch_vizier_ks('TOI-6927')
    >>> fetch_vizier_ks('2MASS J08024565+2139348')
    >>> fetch_vizier_ks('Gaia DR2 671023360793596672')
    """
    # 2mass catalog
    catalog = 'II/246/out'
    vizier = Vizier(
        catalog=catalog,
        columns=['RAJ2000', 'DEJ2000', '2MASS', 'Kmag'],
        keywords=['Stars'],
    )

    result = vizier.query_object(target, radius=0.5*u.arcsec)
    n_entries = np.size(result)
    if n_entries == 0:
        print(f"Target not found: '{target}'")
        return None

    data = result[catalog].as_array().data
    if n_entries == 1:
        return data[0][3]
    elif n_entries > 1 and target.startswith('2MASS'):
        # find by name
       for row in data:
           if row[2] == target[-16:]:
               return row[3]
    elif n_entries > 1:
        print(f"Target could not be uniquely identified: '{target}'")
        return None
    return None


def fetch_aliases(hosts, output_file, ncpu=None):
    """
    Fetch known aliases from the NEA and Simbad databases for a list
    of host stars.  Store output dictionary of aliases to pickle file.

    Examples
    --------
    >>> import gen_tso.catalogs as cat

    >>> # Confirmed targets
    >>> nea_data = cat.load_targets_table()
    >>> hosts = np.unique(nea_data[1])
    >>> output_file = f'{ROOT}data/nea_aliases.pickle'
    >>> fetch_aliases(hosts, output_file)

    >>> # Tess candidates
    >>> with open(f'{ROOT}data/nea_tess_candidates_raw.pickle', 'rb') as handle:
    >>>     candidates = pickle.load(handle)
    >>> tess_hosts = np.unique(candidates['hosts'])
    >>> tess_aliases_file = f'{ROOT}data/tess_aliases.pickle'
    >>> fetch_aliases(unique_tess_hosts, tess_aliases_file)

    host = 'TOI-2076'
    host = 'TOI-741'
    n_aliases = fetch_nea_aliases(host)
    s_aliases,_ = fetch_simbad_aliases(host)
    """
    if ncpu is None:
        ncpu = mp.cpu_count()

    nhosts = len(hosts)
    aliases = {}
    chunksize = ncpu * 3
    nchunks = nhosts // chunksize
    k = 0
    for k in range(k, nchunks+1):
        first = k*chunksize
        last = np.clip((k+1) * chunksize, 0, nhosts)
        with mp.get_context('fork').Pool(ncpu) as pool:
            new_aliases = pool.map(fetch_nea_aliases, hosts[first:last])

        for new_alias in new_aliases:
            aliases.update(new_alias)
        print(f'{last} / {nhosts}  ({k}/{nchunks+1})')

    # Keep track of trexolists aliases:
    targets, aliases, missing, og = load_trexolits_table()

    jwst_names = []
    for star, j_aliases in og.items():
        jwst_names.append(star)
        for alias in j_aliases:
            jwst_names.append(normalize_name(alias))
    jwst_names = np.unique(jwst_names)

    # Complement with Simbad aliases:
    unique_names = np.unique(list(aliases.values()))
    for i,target in enumerate(hosts):
        s_aliases, kmag = fetch_simbad_aliases(target)
        new_aliases = []
        for alias in s_aliases:
            alias = re.sub(r'\s+', ' ', alias)
            is_new = (
                alias in jwst_names or
                alias.startswith('G ') or
                alias.startswith('GJ ') or
                alias.startswith('CD-') or
                alias.startswith('Wolf ') or
                alias.startswith('2MASS ')
            )
            if is_new and alias not in aliases:
                new_aliases.append(alias)
        if len(new_aliases) == 0:
            continue
        print(f'[{i}] Target {repr(target)} has new aliases:  {new_aliases}')
        # Add the star aliases
        for alias in new_aliases:
            aliases[alias] = target
            #print(f'    {repr(alias)}: {repr(target)}')
            # Add the planet aliases
            for name in unique_names:
                is_child = (
                    name not in hosts and
                    name.startswith(target) and
                    len(name) > len(target) and
                    name[len(target)] in ['.', ' ']
                )
                if is_child:
                    letter = name[len(target):]
                    aliases[alias+letter] = name
                    print(f'    {repr(alias+letter)}: {repr(name)}')

        # Ensure trexolists aliases are in
        #if aliases[target] in jwst_names:

    with open(output_file, 'wb') as handle:
        pickle.dump(aliases, handle, protocol=4)


def fetch_nea_tess_candidates():
    r = requests.get(
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
        "select+toi,toipfx,pl_trandurh,pl_trandep,pl_rade,pl_eqt,ra,dec,"
        "st_tmag,st_teff,st_logg,st_rad+"
        "from+toi+"
        "&format=json"
    )
    if not r.ok:
        raise ValueError("Something's not OK")

    resp = r.json()
    tess_hosts = [f"TOI-{entry['toipfx']}" for entry in resp]
    tess_planets = [f"TOI-{entry['toi']}" for entry in resp]
    ntess = len(tess_planets)

    # Discard confirmed planets:
    nea_data = load_targets_table()
    targets = nea_data[0]
    confirmed_hosts = nea_data[1]
    ks_mag = nea_data[4]
    with open(f'{ROOT}data/nea_aliases.pickle', 'rb') as handle:
        nea_aliases = pickle.load(handle)

    j, k = 0, 0
    is_candidate = np.ones(ntess, bool)
    tess_mag = np.zeros(ntess)
    for i, planet in enumerate(tess_planets):
        # Update names if possible:
        tess_host = tess_hosts[i]
        if tess_host in nea_aliases:
            tess_host = tess_hosts[i] = nea_aliases[tess_host]
        if planet in nea_aliases:
            planet = tess_planets[i] = nea_aliases[planet]

        if planet in targets:
            is_candidate[i] = False
            j += 1
            #print(f"[{j}] '{tess_planets[i]}' is confirmed target: '{planet}'")
            # 959 planets
            continue
        if tess_host in confirmed_hosts:
            k += 1
            target_idx = confirmed_hosts.index(tess_host)
            tess_mag[i] = ks_mag[target_idx]
            print(f"[{k}] '{tess_planets[i]}' orbits known star: '{tess_host}' (ks={tess_mag[i]})")
            # 20 hosts

    # Save raw data:
    tess_planets = np.array(tess_planets)
    tess_hosts = np.array(tess_hosts)
    ra = np.array([entry['ra'] for entry in resp])
    dec = np.array([entry['dec'] for entry in resp])
    teff = np.array([entry['st_teff'] for entry in resp])
    logg = np.array([entry['st_logg'] for entry in resp])
    tr_dur = np.array([entry['pl_trandurh'] for entry in resp])
    rprs = np.array([np.sqrt(entry['pl_trandep']) for entry in resp])
    teq = np.array([entry['pl_eqt'] for entry in resp])

    candidates = dict(
        planets=tess_planets[is_candidate],
        hosts=tess_hosts[is_candidate],
        ra=ra[is_candidate],
        dec=dec[is_candidate],
        teff=teff[is_candidate],
        logg=logg[is_candidate],
        tr_dur=tr_dur[is_candidate],
        rprs=rprs[is_candidate],
        teq=teq[is_candidate],
        ks_mag=tess_mag[is_candidate],
    )
    with open(f'{ROOT}data/nea_tess_candidates_raw.pickle', 'wb') as handle:
        pickle.dump(candidates, handle, protocol=4)



def fetch_tess_aliases(ncpu=None):
    """
    Get TESS aliases and Ks magnitudes
    """
    if ncpu is None:
        ncpu = mp.cpu_count()

    with open(f'{ROOT}data/nea_tess_candidates_raw.pickle', 'rb') as handle:
        candidates = pickle.load(handle)

    tess_planets = candidates['planets']
    tess_hosts = candidates['hosts']
    ks_mag = candidates['ks_mag']
    ntess = len(tess_planets)

    # tess candidates
    unique_tess_hosts = np.unique(tess_hosts)
    tess_aliases_file = f'{ROOT}data/tess_aliases.pickle'
    fetch_aliases(unique_tess_hosts, tess_aliases_file)

    with open(tess_aliases_file, 'rb') as handle:
        tess_aliases = pickle.load(handle)
    aka = invert_aliases(tess_aliases)

    # First idea, search in simbad using best known alias to get Ks magnitude
    catalogs = ['2MASS', 'Gaia DR3', 'Gaia DR2', 'TOI']
    k = 0
    for i,planet in enumerate(tess_planets):
        tess_host = tess_hosts[i]
        if tess_host in tess_aliases:
            tess_host = tess_hosts[i] = tess_aliases[tess_host]

        if ks_mag[i] > 0:
            continue

        name = select_alias(aka[tess_host], catalogs)
        if i%200 == 0:
            print(f"~~ [{i}] Searching for '{tess_host}' / '{name}' ~~")
        aliases, kmag = fetch_simbad_aliases(name, verbose=False)
        if kmag is not None:
            k += 1
            ks_mag[i] = kmag

    # Plan B, batch search in vizier catalog:
    two_mass_hosts = np.array([
        select_alias(aka[host], catalogs, host)
        for host in tess_hosts
    ])
    mask = [
        host.startswith('2M') and ks_mag[i]==0
        for i,host in enumerate(two_mass_hosts)
    ]
    two_mass_hosts = two_mass_hosts[mask]
    ra = candidates['ra'][mask]
    dec = candidates['dec'][mask]

    catalog = 'II/246/out'
    vizier = Vizier(
        catalog=catalog,
        columns=['RAJ2000', 'DEJ2000', '2MASS', 'Kmag'],
    )
    two_mass_targets = Table(
        [ra*u.deg, dec*u.deg],
        names=('_RAJ2000', '_DEJ2000'),
    )
    results = vizier.query_region(two_mass_targets, radius=5.0*u.arcsec)

    data = results[catalog].as_array().data
    vizier_names = [d[3] for d in data]
    for i, tess_host in enumerate(tess_hosts):
        host_alias = select_alias(aka[tess_host], catalogs)
        if host_alias in two_mass_hosts:
            idx = vizier_names.index(host_alias[-16:])
            ks_mag[i] = data[idx][4]


    # Plan C, search in vizier catalog one by one:
    missing_hosts = [host for host,ks in zip(tess_hosts,ks_mag) if ks==0.0]
    missing_hosts = np.unique(missing_hosts)
    missing_hosts = [
        select_alias(aka[host], catalogs)
        for host in missing_hosts
    ]
    with mp.get_context('fork').Pool(ncpu) as pool:
        vizier_ks = pool.map(fetch_vizier_ks, missing_hosts)

    for i, tess_host in enumerate(tess_hosts):
        alias_host = select_alias(aka[tess_host], catalogs)
        if alias_host in missing_hosts:
            idx = list(missing_hosts).index(alias_host)
            if vizier_ks[idx] is not None:
                ks_mag[i] = vizier_ks[idx]

    # Last resort, scrap from the NEA pages
    missing_hosts = [host for host,ks in zip(tess_hosts,ks_mag) if ks==0.0]
    missing_hosts = np.unique(missing_hosts)

    with mp.get_context('fork').Pool(ncpu) as pool:
        scrap_ks = pool.map(scrap_nea_kmag, missing_hosts)
    for i,planet in enumerate(tess_planets):
        tess_host = tess_hosts[i]
        if tess_host in missing_hosts:
            idx = list(missing_hosts).index(tess_host)
            if scrap_ks[idx] is not None:
                ks_mag[i] = scrap_ks[idx]


    # Save as plain text:
    with open(f'{ROOT}data/tess_data.txt', 'w') as f:
        host = ''
        for i in range(ntess):
            ra = candidates['ra'][i]
            dec = candidates['dec'][i]
            ksmag = f'{ks_mag[i]:.3f}' if ks_mag[i]>0.0 else 'None'
            planet = tess_planets[i]
            tr_dur = candidates['tr_dur'][i]
            teff = as_str(candidates['teff'][i], '.1f')
            logg = as_str(candidates['logg'][i], '.3f')
            depth = candidates['rprs'][i] **2.0 * pc.ppm
            rprs = as_str(np.sqrt(depth), '.3f')
            teq = as_str(candidates['teq'][i], '.1f')

            if tess_hosts[i] != host:
                host = tess_hosts[i]
                f.write(f">{host}: {ra} {dec} {ksmag} {teff} {logg}\n")
            f.write(f" {planet}: {tr_dur} {rprs} {teq}\n")

    today = date.today()
    with open(f'{ROOT}data/last_updated_tess.txt', 'w') as f:
        f.write(f'{today.year}_{today.month:02}_{today.day:02}')


def select_alias(aka, catalogs, default_name=None):
    for catalog in catalogs:
        for alias in aka:
            if alias.startswith(catalog):
                return alias
    return default_name


def invert_aliases(aliases):
    """
    aka = invert_aliases(nea_aliases)
    """
    aka = {}
    for key,val in aliases.items():
        if val not in aka:
            aka[val] = []
        aka[val].append(key)
    return aka


def scrap_nea_kmag(target):
    """
    >>> target = 'TOI-5290'
    >>> scrap_nea_kmag(target)
    """
    response = requests.get(
        url=f'https://exoplanetarchive.ipac.caltech.edu/overview/{target}',
    )
    if not response.ok:
        print(f'ERROR {target}')
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    pm = '±'

    kmag = None
    for dd in soup.find_all('dd'):
        texts = dd.get_text().split()
        if 'mKs' in texts:
            print(target, dd.text.split())
            kmag_err = texts[-1]
            kmag = float(kmag_err[0:kmag_err.find(pm)])
    return kmag


