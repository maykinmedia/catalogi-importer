.. _deployment:

==========
Deployment
==========

Deployment is done via `Ansible`_. Currently, only single server deployments
are described but you can just as easily deploy the application in a Kubernetes
environment.

.. warning:: The deployment configuration (called a "playbook") is very 
   simplistic and also contains sensitive values. This makes the playbook more 
   readable but is not following good practices!

Server preparation
==================

You can configure the Ansible playbook to install relevant services, do it
manually, or have these pre-installed. You will need:

    * PostgreSQL
    * Nginx
    * Docker
    * Python3
    * Python3 PIP

Apart from Docker, you can install all these with something like:

.. code:: shell

   $ sudo apt-get install postgresql nginx python3 python3-pip

For Docker, follow the instructions here: https://docs.docker.com/engine/install/

You will also need access to, or create, a database. You can create a database
with something like:

.. code:: shell

   $  sudo su postgres --command="createuser <db-username> -P"
   Enter password for new role:
   Enter it again:
   $ sudo su postgres --command="createdb <db-name> --owner=<db-username>"


Installation
============

1. Download the project from Github or just the `deployment files`_.

   .. code:: shell

      $ git clone git@github.com:maykinmedia/catalogi-importer.git

2. Setup virtual environment:

   .. code:: shell

      $ python3 -m venv env/
      $ source env/bin/activate
      $ pip install ansible

   .. note:: Sometimes, additional or updates packages are needed if they 
      are not installed by the Ansible setup installation. You can do so like 
      this:

      .. code:: shell

         $ python -m pip install -U pip
         $ pip install ordered_set packaging appdirs six

3. Install Ansible collections:

   .. code:: shell

      $ ansible-galaxy collection install community.docker
      $ ansible-galaxy collection install git+https://github.com/maykinmedia/commonground-ansible.git

   .. note:: The last collection might require explicit access.

4. Edit the playbook ``app.yml`` to match your setup. Take special note of all
   **TODO** settings and **read through all the comments and variables**.

5. Run the playbook:

   .. code:: shell

      $ ansible-playbook app.yml --become --ask-become-pass


.. _`Ansible`: https://www.ansible.com/
.. _`deployment files`: https://github.com/maykinmedia/catalogi-importer/tree/master/deployment
