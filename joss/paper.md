---
title: '`Gen TSO`: A graphical ETC interface for time-series observations of exoplanets'
tags:
  - Python
  - astronomy
  - exoplanets
  - JWST
authors:
  - name: Patricio E. Cubillos
    orcid: 0000-0002-1347-2600
    affiliation: "1, 2"
affiliations:
  - name: Space Research Institute, Austrian Academy of Sciences, Schmiedlstrasse 6, A-8042, Graz, Austria
    index: 1
  - name: INAF -- Osservatorio Astrofisico di Torino, Via Osservatorio 20, 10025 Pino Torinese, Italy
    index: 2
date: 01 April 2024
bibliography: paper.bib

--- 

# Summary

The James Webb Space Telescope (JWST) Exposure Time Calculator (ETC)
performs signal-to-noise ratio calculations for all JWST instruments
and observing modes.  As such, the ETC is a vital component to prepare
observing proposals.  Since the JWST was designed to cover a broad
spectrum of astronomy research fields, learning to configure the ETC
for exoplanet time-series observations (TSO) is not a trivial
endeavor.  There is a significant number of instrumental settings that
can be adjusted, and the user needs to gather planet and host-star
physical information from multiple sources.

`Gen TSO` streamlines the ETC use for time-series observations by
providing an dedicated graphical user interface designed for
transiting exoplanet observations.  Also, `Gen TSO` leverages the ETC
by providing instant access to the online available exoplanet
databases (the NASA Exoplanet Archive) to setup the observing scenes;
provides a direct visualization of the observing modes, stellar SEDs,
and planet spectra; and simulates transit or eclipse spectra and S/N
as expected from a JWST observations.


# Simulating JWST exoplanet TSO spectra with `Gen TSO`

TBD

![Gen TSO graphical user interface.  Components on the left hand-side
are user inputs to define the target properties and instrument
configuration.  Components on the right-hand side show the ouptuts,
including the target's FOV and spectra (stellar SED and
transit/eclipse depth), the instrumental throughput curves, and
time-series simulation. \label{fig:gen_tso_gui}]
(figures/gen_tso_screen.png){width=100%}


# Statement of Need

TBD

# Future Developments

`Gen TSO` provides support for the spectroscopic observing modes of
JWST.  Future releases will add the photometric observing modes.  The
current list of known targets includes only the confirmed planets from
the NASA Exoplanet Archive, future releases hope to include TESS
candidates. Further suggestions for new features are very much
welcomed.


# Documentation

Documentation for `Gen TSO` is available at
[http://pcubillos.github.io/gen_tso](http://pcubillos.github.io/gen_tso).


# Similar Tools

The following exoplanet retrieval codes are open source:
[`PandExo`](https://github.com/natashabatalha/PandExo) [@Batalha:2017]


# Acknowledgements


PEC acknowledges financial support by the Austrian Science Fund (FWF)
Erwin Schroedinger Fellowship, program J4595-N.

PEC thanks contributors to the Python Programming Language and the free
and open-source community, including developers of
`Pandeia` [@Pontoppidan2016], 
`Shiny` [@ShinyDevTeam],
`Plotly`,
`numpy` [@Harris2020], and
`Pyrat Bay` [@Cubillos2021].

# References
