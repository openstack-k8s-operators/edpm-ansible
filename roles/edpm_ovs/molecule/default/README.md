********
edpm_ovs
********

The edpm_ovs default molecule scenario uses
the delegated driver to run against localhost.
As such this should only be executed on a disposable host.
For local development the vagrant is provided to create
a disposable env for you, that scenario should just be delegated
to the converge prepare and verify playbooks of this scenario.

The molecule prepare command will invoke several roles
to set the local timezone, configure users and
the correct repos for the current distro and otherwise
prepare the host to test the edpm_ovs role.

The molecule verify command will assert that ovs was deployed correctly
by asserting the service is running, permissions are as expected and
ovs is installed correctly.
