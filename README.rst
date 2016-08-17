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

To install ``eppy``:

::

   pip install EPP

or::

   easy_install EPP


NOTE: While the module name is ``eppy``, the package on PyPI is named EPP
because `eppy` was already taken by another unrelated project.


Bleeding Edge
^^^^^^^^^^^^^

Alternatively, you may track the development version by cloning the git
repository instead.

::

   pip install -e git+https://github.com/cloudregistry/eppy.git#egg=EPP



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



Working with EPP commands and responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

EPP documents can be sent as strings using the ``EppClient.write`` method.
Alternatively, use the provided ``EPPDoc`` subclasses.

::
   >>> from eppy.doc import EppInfoDomainCommand
   >>> cmd = EppInfoDomainCommand()
   >>> cmd.name = "example.org"
   >>> print cmd
   <epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
     <command>
       <info>
         <domain:info xmlns="urn:ietf:params:xml:ns:domain-1.0" xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
           <name>example.org</name>
         </domain:info>
       </info>
     </command>
   </epp>

   >>> repr(cmd)
   "{'epp': {'command': {'info': {'domain:info': {'name': 'example.org'}}}}}"



Using ``XmlDictObject``
^^^^^^^^^^^^^^^^^^^^^^^

``XmlDictObject`` is a convenience wrapper for generating and reading EPP
documents by translating to and from Python dictionary.

::

   >>> from eppy.xmldict import XmlDictObject
   >>> o = XmlDictObject({'x': {}})
   >>> print o.to_xml([])
   <x />


Creating a child element with an attribute and text node:

::

   >>> o['x'] = {'d': {'@a': 'true', '_text': '1'}}
   >>> print o.to_xml({})
   <x>
     <d a="true">1</d>
   </x>


As a shorthand for elements without attributes:

::

   >>> o['x'] = {'d': 1}
   >>> print o.to_xml({})
   <x>
     <d>1</d>
   </x>


Multiple elements?

::

   >>> o['x'] = {'d': ['1', '2', '3']}
   >>> print o.to_xml({})
   <x>
     <d>1</d>
     <d>2</d>
     <d>3</d>
   </x>



.. _`Extensible Provisioning Protocol`: http://www.rfc-editor.org/rfc/rfc5730.txt
.. _`PyPI`: http://pypi.python.org/pypi
.. _pip: http://www.pip-installer.org/
.. _virtualenv: http://www.virtualenv.org/
