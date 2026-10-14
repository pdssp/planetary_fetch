===============================
Planetary Fetch
===============================

.. image:: https://img.shields.io/github/v/release/pdssp/planetary_fetch
   :target: https://github.com/pdssp/planetary_fetch/releases
.. image:: https://img.shields.io/badge/python-%E2%89%A53.11-blue
.. image:: https://img.shields.io/github/license/pdssp/planetary_fetch
   :target: https://github.com/pdssp/planetary_fetch/blob/main/LICENSE
.. image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
   :target: https://github.com/pdssp/planetary_fetch/graphs/commit-activity


The aim of Planetary Fetch is to download data from PDS based on a part of the PDS ID.


Installation
------------

Planetary Fetch requires Python 3.11 or later.

The recommended way is to install the ``planetary_fetch`` command in its own
environment with `uv`_, from a release listed on the `releases page`_
(replace ``<version>`` with a release number, for example ``2.0.0``):

.. code-block:: console

    $ uv tool install git+https://github.com/pdssp/planetary_fetch@<version>

or with `pip`_:

.. code-block:: console

    $ pip install git+https://github.com/pdssp/planetary_fetch@<version>

Without ``@<version>``, the latest development version of the ``main`` branch
is installed.

.. _uv: https://docs.astral.sh/uv/
.. _pip: https://pip.pypa.io
.. _releases page: https://github.com/pdssp/planetary_fetch/releases


From sources
------------

The sources for Planetary Fetch can be downloaded from the `GitHub repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone https://github.com/pdssp/planetary_fetch

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/pdssp/planetary_fetch/tarball/main

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ uv tool install .

.. _GitHub repo: https://github.com/pdssp/planetary_fetch
.. _tarball: https://github.com/pdssp/planetary_fetch/tarball/main


Development
-----------

The development environment is managed with `uv`_:

.. code-block:: console

    $ git clone https://github.com/pdssp/planetary_fetch
    $ cd planetary_fetch
    $ make install-dev

``make install-dev`` installs the project and the development tools
(``uv sync``), the pre-commit hooks and the commit message template.
Commit messages follow `Conventional Commits`_: they decide the next release
version. See the `contributing guide`_ for details.

.. _Conventional Commits: https://www.conventionalcommits.org


Usage
-----

To get help:

.. code-block:: console

    $ planetary_fetch -h

Basic download (quote the IDs so that the shell does not expand ``*``):

.. code-block:: console

    $ planetary_fetch --ids 'HRL0000CA5C*' --output_dir /tmp

Basic download with silent mode:

.. code-block:: console

    $ planetary_fetch --ids 'HRL0000CA5C*' --output_dir /tmp --level CRITICAL

Basic download with silent mode without progress bar:

.. code-block:: console

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

    $ make tests


Author
------

👤 **Jean-Christophe Malapert**


🤝 Contributing
---------------

Contributions, issues and feature requests are welcome! Feel free to check the
`issues page`_. You can also take a look at the `contributing guide`_.

.. _issues page: https://github.com/pdssp/planetary_fetch/issues
.. _contributing guide: https://github.com/pdssp/planetary_fetch/blob/main/CONTRIBUTING.rst


📝 License
----------

This project is licensed under the `GNU General Public License v3`_.

.. _GNU General Public License v3: https://github.com/pdssp/planetary_fetch/blob/main/LICENSE
