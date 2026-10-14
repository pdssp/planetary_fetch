.. highlight:: shell

===============================
Planetary Fetch
===============================

.. image:: https://img.shields.io/github/v/tag/pole-surfaces-planetaires/planetary_fetch
.. image:: https://img.shields.io/github/v/release/pole-surfaces-planetaires/planetary_fetch?include_prereleases

.. image:: https://img.shields.io/pypi/v/planetary_fetch

.. image https://img.shields.io/github/downloads/pole-surfaces-planetaires/planetary_fetch/total
.. image https://img.shields.io/github/issues-raw/pole-surfaces-planetaires/planetary_fetch
.. image https://img.shields.io/github/issues-pr-raw/pole-surfaces-planetaires/planetary_fetch
.. image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
   :target: https://github.com/pole-surfaces-planetaires/planetary_fetch/graphs/commit-activity
.. image https://img.shields.io/github/license/pole-surfaces-planetaires/planetary_fetch
.. image https://img.shields.io/github/forks/pole-surfaces-planetaires/planetary_fetch?style=social


The aim of Planetary Fetch is to dowload data from PDS based on a part of the PDS ID.


Stable release
--------------

To install Planetary Fetch, run this command in your terminal:

.. code-block:: console

    $ pip install git+https://github.com/pdssp/planetary_fetch

This is the preferred method to install Planetary Fetch, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for Planetary Fetch can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/pole-surfaces-planetaires/planetary_fetch

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/pole-surfaces-planetaires/planetary_fetch/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ make  # install in the system root
    $ make user # or Install for non-root usage


.. _Github repo: https://github.com/pole-surfaces-planetaires/planetary_fetch
.. _tarball: https://github.com/pole-surfaces-planetaires/planetary_fetch/tarball/master



Development
-----------

.. code-block:: console

        $ git clone https://github.com/pole-surfaces-planetaires/planetary_fetch
        $ cd planetary_fetch
        $ make prepare-dev
        $ source .planetary_fetch
        $ make install-dev


Usage
-----

To get help:

.. code-block:: console

        $ planetary_fetch -h

Basic download :

 .. code-block:: console

        $ planetary_fetch --ids HRL0000CA5C* --output_dir /tmp

Basic download with silent mode

 .. code-block:: console

        $ planetary_fetch --ids HRL0000CA5C* --output_dir /tmp --level CRITICAL

Basic download with silent mode without progress bar

 .. code-block:: console

        $ planetary_fetch --ids HRL0000CA5C* --output_dir /tmp --level CRITICAL --disable_tqdm

CRISM EPF observations
----------------------

For a complete CRISM targeted observation, use the observation ID followed by a
wildcard. ODE product queries return 100 products by default. Planetary Fetch
retrieves all result pages before downloading. For example::

    planetary_fetch --ids 'HRL000040FF*' --output_dir /tmp/crism

After downloading, the program prints a view-by-view DATA/DDR table. A cell is
``OK`` only when both the IMG and LBL files are present. The final status is
``INCOMPLETE`` if any expected view/channel pair is missing. Views are inferred
from the observation's CRISM science products; the report does not assume that
every observation has the same view numbers. The CLI exits with code 2 for an
incomplete observation.

To add one UB calibration pair for each S and L channel::

    planetary_fetch --ids 'HRL000040FF*' --output_dir /tmp/crism --with_ub

The UB selection uses the view 07 IF/TRR3 label (or the earliest IF/TRR3 view
when 07 is absent). It considers the UB IDs listed in ``SOURCE_PRODUCT_ID``
and chooses the closest spacecraft clock count for each channel. The selected
UB must also match the label's frame rate, pixel binning, exposure parameter,
and wavelength filter when those fields are present. The IMG/LBL pairs are
stored in ``HRL40/HRL40FF/UB``. ``--with_ub`` requires a
single complete CRISM observation ID. A failed download or missing UB reference
causes an error instead of reporting success.

The numeric fields in CDR4 UB names (frame rate, pixel binning, exposure and
wavelength filter) follow the `ODE CRISM CDR product description`_, which links
to the `CRISM Data Product SIS`_.

.. _ODE CRISM CDR product description: https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/Mars%20Reconnaissance%20Orbiter/CRISM/CRISM%20Product%20Primer/CRISM%20EDR/CRISM%20CDR.htm
.. _CRISM Data Product SIS: https://pds-geosciences.wustl.edu/mro/mro-m-crism-2-edr-v1/mrocr_0001/document/crism_dpsis.pdf



Run tests
---------

.. code-block:: console

        $make tests



Author
------
👤 **Jean-Christophe Malapert**



🤝 Contributing
---------------
Contributions, issues and feature requests are welcome!<br />Feel free to check [issues page](https://github.com/pole-surfaces-planetaires/planetary_fetch/issues). You can also take a look at the [contributing guide](https://github.com/pole-surfaces-planetaires/planetary_fetch/blob/master/CONTRIBUTING.rst)


📝 License
----------
This project is [GNU General Public License v3](https://github.com/pole-surfaces-planetaires/planetary_fetch/blob/master/LICENSE) licensed.
