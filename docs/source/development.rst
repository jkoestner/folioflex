Development
============

To run some of the development tools, you'll need to install the development dependencies:

.. code-block:: bash

    pip install .[dev]

Testing
-------

To run the tests, run the following command in the root directory:

.. code-block:: bash

    pytest

Coverage
--------

To see the test coverage the following command is run in the root directory. 
This is also documented in the `.coveragerc` file.

.. code-block:: bash

    pytest --cov=folioflex --cov-report=html

Documentation
-------------

To build the documentation, run the following command in the /docs directory:

.. code-block:: bash

    make html

Logging
-------

To change the level of logging when interactively running python, run 
the following commands and switch the level to the desired level:

.. code-block:: python

    from folioflex.utils import config_helper
    config_helper.set_log_level("DEBUG")




