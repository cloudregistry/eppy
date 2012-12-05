eppy
====

Introduction
------------

eppy is a Python-based API for the `Extensible Provisioning Protocol`_ (EPP),
commonly used for communication between domain registries and registrars.


Features
--------

* EPP Client
* Uses standard python logging
* TLS/SSL support
* EPP Server stub
* Test suite
* Load testing support
* Optional gevent


Installation
------------

If you're using a virtualenv_ (almost always a good idea), activate it first.


Stable
^^^^^^

Stable versions are released onto `PyPI`_ and can be installed in the normal
way via ``easy_install`` or pip_.


::

   pip install eppy

or using distribute_::

   easy_install eppy


Bleeding Edge
^^^^^^^^^^^^^

Alternatively, you may track the development version by cloning the git
repository instead.

::

   pip install -e git+https://github.com/cloudregistry/eppy.git#egg=eppy



Usage
-----


Client
^^^^^^

::

   >>> from eppy.client import EppClient
   >>> client = EppClient(ssl_keyfile='client.key', ssl_certfile='client.pem')
   >>> client.connect('server.example.tld')
   >>> resp = client.login('userid', 'secretpassword')
   >>> 


Examples can be found in the ``examples`` directory.



.. _`Extensible Provisioning Protocol`: http://www.rfc-editor.org/rfc/rfc5730.txt
.. _`PyPI`: http://pypi.python.org/pypi
.. _pip: http://www.pip-installer.org/
.. _virtualenv: http://www.virtualenv.org/

.. rubric:: Footnotes

.. [#pip] http://www.pip-installer.org/

