
# Ansible deployment

## Initial setup

1. Setup virtual environment

    ```
    $ python3 -m venv env/
    $ source env/bin/activate
    $ pip install ansible

   WARNING: Sometimes, additional or updates packages are needed if they are not 
   installed by the Ansible setup installation. You can do that like this:

    ```
    $ python -m pip install -U pip
    $ pip install ordered_set packaging appdirs six
    ```

3. Install Ansible collections.

    ```
    $ ansible-galaxy collection install git+https://github.com/maykinmedia/commonground-ansible.git
    ```

   This collection might require explicit access.

4. Run the playbook.

    ```
    $ ansible-playbook app.yml --become --ask-become-pass
    ```


# TODO's

1. Private media volume
