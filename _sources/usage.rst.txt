User Guide
==========

There are a few ways to use FolioFlex.

Jupyter Notebook
----------------
The followig notebook shows how to use FolioFlex interactively:

- `portfolio notebook <https://nbviewer.jupyter.org/github/jkoestner/folioflex/blob/main/notebook/portfolio_example.ipynb>`_

CLI
---

To use CLI you can see the help menu by running:

.. code-block:: bash

    ffx -h

To get module help you can run:

.. code-block:: bash

    ffx <module> -h

To run an example that outputs to an email the following can be run:

.. code-block:: bash

    ffx email -el "['yourname@outlook.com']" -md "{'config_path' : 'portfolio_personal.ini', 'lookbacks' : [1, 30, None]}" -hd {}

Website
-------

The website is built using plotly dash. To run the website locally you can 
run the following from the root directory:


.. code-block:: bash

    python app.py
