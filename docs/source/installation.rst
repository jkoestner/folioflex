Installation
============

Quick Start
-----------

To install, this repository can be installed by running the following command in 
the python environment of choice.

.. code-block:: bash

   pip install folioflex

Or could be done using GitHub.
   
.. code-block:: bash

   pip install git+https://github.com/jkoestner/folioflex.git

If wanting to do more and develop on the code, the following command can 
be run to install the packages in the requirements.txt file.
   
.. code-block:: bash
   
   pip install -e .

Configuration
-------------

Basic
~~~~~

There are a number of credentials that are used in the ``configs\config.ini`` file.

- **credentials**

  - ``ffx_username``: The username for the personal portfolio dashboard
  - ``ffx_password``: The password for the personal portfolio dashboard

- **api**
  
  - ``fred_api``: The API key for the FRED API
  
- **other**

  - ``redis_url``: The URL for the Redis database
  - ``local_redis``: The URL for the local Redis database
  - ``smtp_username``: The username for the SMTP server
  - ``smtp_password``: The password for the SMTP server
  - ``smtp_server``: The SMTP server
  - ``smtp_port``: The SMTP port

Portfolio
~~~~~~~~~

There are also a number of portfolio specific configurations that are used in the
performance located in the ``configs\portfolio_demo.ini`` file.





