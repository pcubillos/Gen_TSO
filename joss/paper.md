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
can be adjusted (not all relevant for exoplanet observations), and the
user needs to gather planet and host-star physical information from
multiple sources.

`Gen TSO` streamlines the ETC use for time-series observations by
providing an dedicated graphical user interface designed for
transiting exoplanet observations.  Also, `Gen TSO` leverages the ETC
by providing instant access to the online available exoplanet
databases (the NASA Exoplanet Archive) to setup the observing scenes;
provides a direct visualization of the observing modes, stellar SEDs,
and planet spectra; and simulates transit or eclipse spectra and
signal-to-noise ratio (S/N) as expected from a JWST observations.


# Statement of Need

The JWST ETC is a complex interface with many components and requiring
user inputs that need to be obtained from multiple sources.  Gen TSO
provides a familiar graphical user interface
(\autoref{fig:gen_tso_gui}), being similar to the JWST, but largely
simplified, containing only the components needed for exoplanet TSO
simulations.  The Gen TSO interface is structured to provide an
intuitive interface, placing all inputs on the left-hand side of the
screen and all outputs on the right hand side.  The input components
split into three main panels, on the top panel the use selects the
instrument and detector.

![Gen TSO graphical user interface.  Components on the left hand-side are user inputs to define the target properties and instrument configuration.  Components on the right-hand side show the ouptuts, including the target's FOV and spectra (stellar SED and transit/eclipse depth), the instrumental throughput curves, and time-series simulation. \label{fig:gen_tso_gui}](gen_tso_gui){width=100%}


On the bottom left panel (Target panel), the user sets the
astrophysical properties of the observing scene.  An input select menu
allows the user to search for known targets and automate setting the
system properties once a target is selected.  The target information
is taken from the [NASA Exoplanet
Archive](https://exoplanetarchive.ipac.caltech.edu).  Hyperlinks and
display notifications help the user to access the targets' NASA
Archive website, indicate whether it has previous JWST observations,
and list known aliases.  This info helps the user to select the most
appropriate host-star SED (PHOENIX, Kurucz, or blackbody models). At
the bottom the user can choose to simulate transit or eclipse
observations, set the observation duration, and upload the transit and
or eclipse model spectra to simulate as a JWST observation.  SEDs and
depth spectra can be displayed and compared on the right output panel.

The panel to the right, is where the user configures the observation
(Detector setup panel).  These include the dispersers, filters,
subarray, readout pattern, groups, and integration settings.  The
throughput curves of these settings are instantly displayed on the
right output panel.  More importantly, at any time, Gen TSO displays
the exposure time corresponding to the current detector settings.
With a button click the user can calculate the saturation level for
the given scene and detector, allowing one to set the right number of
groups.  Similarly, a switch automatically adjusts the number of
integrations to match the observation duration.

Once a user has defined the scene and instrument settings, the `Run
Pandeia` button will compute the full time-series observation S/N.
Executed runs will accumulate on the input-select component above.
Below, the TSO viewer will display the simulated transit or eclipse
observation, with option to set the number of observations and
resampling resolution.

The last two panels below display information with images and text
outputs, which are instantly updated as the user sets the scene and
detector.  A component of the image viewer panel not yet described is
the sky view of the target (provided by the
[ESASky](https://www.cosmos.esa.int/web/esdc/esasky-help)).  This is
an interactive viewer where the user can view the target's FOV, query
for previous observation footprints and search for cataloged target
around the TSO target.


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
[`PandExo`](https://github.com/natashabatalha/PandExo) [@Batalha2017]


# Acknowledgements


PEC acknowledges financial support by the Austrian Science Fund (FWF)
Erwin Schroedinger Fellowship, program J4595-N.  This research has
made use of ESASky, developed by the ESAC Science Data Centre (ESDC)
team and maintained alongside other ESA science mission's archives at
ESA's European Space Astronomy Centre (ESAC, Madrid, Spain).

PEC thanks contributors to the Python Programming Language and the free
and open-source community, including developers of
`Pandeia` [@Pontoppidan2016], 
`Shiny` [@ShinyDevTeam],
`Plotly`,
`numpy` [@Harris2020], and
`Pyrat Bay` [@Cubillos2021].

# References
