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

    $ planetary_fetch --ids 'HRL0000CA5C*' --output_dir /tmp --level CRITICAL --disable_tqdm


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
