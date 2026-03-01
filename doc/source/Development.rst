Development
===========


Installation
------------

Clone the repository and navigate to the project directory:

.. code-block:: bash

  git clone https://github.com/pyrtlsdr/pyrtlsdr.git
  cd pyrtlsdr

Then install the package in one of two ways:

Using `uv`_ (recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^

Install ``uv``
""""""""""""""

Install `uv`_ (if you don't have it already) by following the instructions on the `uv installation page`_.

.. tab-set::
  :sync-group: operating-systems

  .. tab-item:: Linux/macOS
    :sync: nix

    Use ``curl`` to download the installation script and run it with ``sh``:

    .. code-block:: bash

      curl -LsSf https://astral.sh/uv/install.sh | sh

    If your system doesn't have ``curl``, you can use ``wget`` instead:

    .. code-block:: bash

      wget -qO- https://astral.sh/uv/install.sh | sh

  .. tab-item:: Windows
    :sync: windows

    Use ``irm`` to download the script and execute it with ``iex``:

    .. code-block:: powershell

      powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

    Changing the `execution policy`_ allows running a script from the internet.


.. tip::

  The installation script may be inspected before running:

  .. tab-set::
    :sync-group: operating-systems

    .. tab-item:: Linux/macOS
      :sync: nix

      .. code-block:: bash

        curl -LsSf https://astral.sh/uv/install.sh | less

    .. tab-item:: Windows
      :sync: windows

      .. code-block:: powershell

        powershell -c "irm https://astral.sh/uv/install.ps1 | more"

  Alternatively, the installer or binaries can be downloaded directly from
  `GitHub <https://docs.astral.sh/uv/getting-started/installation/#github-releases>`_.


Install project
"""""""""""""""

Choose the Python version you want to use (optional):

.. code-block:: bash

  uv python pin 3.14


Then install the package (including development dependencies):

.. code-block:: bash

  uv sync


.. note::

  ``uv`` will handle virtual environment creation and management, as well as Python version management,
  and will install the package in editable mode by default.

  You can also use ``uv`` to run tests and other commands (see the `uv cli documentation`_ for more details).


Using ``pip``
^^^^^^^^^^^^^


.. note::

  The instructions below assume you have already set up a virtual environment,
  and have activated it before running the commands.


Install the project
"""""""""""""""""""

Install with ``pip`` in editable mode:

.. code-block:: bash

  pip install -e .


or to include the optional `pyrtlsdrlib` dependency:

.. code-block:: bash

  pip install -e '.[lib]'


Install development dependencies
""""""""""""""""""""""""""""""""

The development dependencies are listed in the ``dependency-groups`` sections of the ``pyproject.toml`` file.
Installation of these dependencies is optional, but may be required for running tests and building documentation.



.. _uv: https://docs.astral.sh/uv/
.. _uv installation page: https://docs.astral.sh/uv/getting-started/installation/
.. _uv cli documentation: https://docs.astral.sh/uv/reference/cli/
.. _execution policy: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.4#powershell-execution-policies
