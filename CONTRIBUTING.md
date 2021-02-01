# Contribution guidelines for Catalogi Importer

If you want to contribute to Catalogi Importer , we ask you to follow these guidelines.

## Reporting bugs
If you have encountered a bug in Catalogi Importer , please check if an issue already exists in the list of existing [issues](https://github.com/maykinmedai/catalogi-importer/issues), if such an issue does not exist, you can create one [here](https://github.com/maykinmedai/catalogi-importer/issues/new/choose). When writing the bug report, try to add a clear example that shows how to reproduce said bug.

## Adding new features
Before making making changes to the code, we advise you to first check the list of existing [issues](https://github.com/maykinmedai/catalogi-importer/issues) for Catalogi Importer  to see if an issue for the suggested changes already exists. If such an issue does not exist, you can create one [here](https://github.com/maykinmedai/catalogi-importer/issues/new/choose). Creating an issue gives an opportunity for other developers to give tips even before you start coding. If you are in the early idea phase, or if your feature requires larger changes, you can also discuss it on [the mailing list](https://lists.publiccode.net/mailman/postorius/lists/openzaak-discuss.lists.publiccode.net/) to make sure you are heading in the right direction.

### Code style
To keep the code clean and readable, Catalogi Importer  uses:
- [`isort`](https://github.com/timothycrosley/isort) to order the imports
- [`black`](https://github.com/psf/black) to format the code and keep diffs for pull requests small
- [`flake8`](https://github.com/PyCQA/flake8) to clean up code (removing unused imports, etc.)

Whenever a branch is pushed or a pull request is made, the code will be checked in CI by the tools mentioned above, so make sure to install these tools and run them locally before pushing branches/making PRs.

Catalogi Importer  aims to meet the criteria of the [Standard for Public Code](https://standard.publiccode.net). Please make sure that your pull requests are compliant, that will make the reviews quicker.

### Forking the repository
In order to implement changes to Catalogi Importer  when you do not have rights for the [Catalogi Importer  repository](https://github.com/maykinmedai/catalogi-importer), you must first fork the repository. Once the repository is forked, you can clone it to your local machine.

### Making the changes
On your local machine, create a new branch, and name it like:
- `feature/some-new-feature`, if the changes implement a new feature
- `issue/some-issue`, if the changes fix an issue

Once you have made changes or additions to the code, you can commit them (try to keep the commit message descriptive but short). If an issue exists in the [Catalogi Importer  issue list](https://github.com/maykinmedai/catalogi-importer/issues/) for the changes you made, be sure to format your commit message like `"Fixes #<issue_id> -- description of changes made`, where `<issue_id>"` corresponds to the number of the issue on GitHub. To demonstrate that the changes implement the new feature/fix the issue, make sure to also add tests to the existing Django testsuite.

### Making a pull request
If all changes have been committed, you can push the branch to your fork of the repository and create a pull request to the `master` branch of the Catalogi Importer  repository. Your pull request will be reviewed, if applicable feedback will be given and if everything is approved, it will be merged
