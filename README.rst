.. _pydoit: https://pydoit.org
.. _git repository: https://github.com/hat-open/hat-doit.git
.. _PyPI project: https://pypi.org/project/hat-doit
.. _Hat Open: https://hat-open.com
.. _Končar Digital: https://www.koncar.hr/en


hat-doit - Hat build utility functions
======================================

Hat open projects uses `pydoit`_ as build automation tool. This repository
provides utility functions commonly used in definition of doit tasks.

For more information see `git repository`_.


Runtime requirements
--------------------

* python >=3.8


Install
-------

`hat-doit` is available as `PyPI project`_::

    $ pip install hat-doit


Build
-----

Build tool used for `hat-doit` is pydoit. It can be installed together with
other python dependencies by running::

    $ pip install -r requirements.pip.dev.txt

For listing available doit tasks, use::

    $ doit list

Default task::

    $ doit

creates wheel package inside `build` directory.


Hat Open
--------

`hat-doit` is part of `Hat Open`_ project - open-source framework of tools
and libraries for developing applications used for remote monitoring, control
and management of intelligent electronic devices such as IoT devices, PLCs,
industrial automation or home automation systems.

Development of Hat Open and associated repositories is sponsored by
`Končar Digital`_.


License
-------

Copyright 2020-2023 Hat Open AUTHORS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
