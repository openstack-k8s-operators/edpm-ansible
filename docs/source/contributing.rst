============
Contributing
============

Contributors to the collection should take their time to read these guidelines,
in order to avoid certain common pitfalls and needless frustration during code review.

These guidelines may change, depending on evolution of the project.
However, all changes should be performed with consideration for other developers
workflow and for projects using edpm-ansible collection.

General recommendation
++++++++++++++++++++++

Test your code locally, if it is at all possible, to shorten the development loop
and minimize unnecessary use of CI. Before committing your changes, run `pre-commit`_
check to avoid needless issues with style, such as indentation.

.. note::

   Pre-commit hooks should be installed in your local repo with: `pre-commit install`
   Alternatively, you can run all hooks on all files with: `pre-commit run -a`

.. toctree::

   contributing_roles
   contributing_plugins
   contributing_playbooks
   testing_roles
   testing_with_ansibleee

.. _`pre-commit`: https://pre-commit.com/
