# Contributing

Thanks for your interest in contributing to GPT-Pilot! Please take a moment to review this document **before submitting a pull request**.

## Pull requests

**Please ask first before starting work on any significant new features.**

It's never a fun experience to have your pull request declined after investing a lot of time and effort into a new feature. To avoid this from happening, we request that contributors create [a feature idea discussion](https://github.com/Pythagora-io/gpt-pilot/discussions/new?category=ideas) to first discuss any new ideas. Your ideas and suggestions are welcome!

Please ensure that the tests are passing when submitting a pull request. If you're adding new features to GPT-Pilot, please include tests.

## Where do I go from here?

- [Ask a question](https://github.com/Pythagora-io/gpt-pilot/discussions/new?category=q-a)
- [Submit a bug](https://github.com/Pythagora-io/gpt-pilot/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml&title=%5BBug%5D%3A+)
- [Submit a feature idea](https://github.com/Pythagora-io/gpt-pilot/discussions/new?category=ideas)
- [Share what you have built](https://github.com/Pythagora-io/gpt-pilot/discussions/new?category=show-and-tell)
- [Join our Discord Channel](https://discord.com/channels/1145718759550615582)

### Fork and create a branch

If there is something you think you can fix, then [fork GPT-Pilot] and create a branch with a descriptive name.

### Get the test suite running

TBD

### Implement your fix or feature

At this point, you're ready to make your changes. Feel free to ask for help.

### View your changes in a Rails application

TBD

### Create a Pull Request

At this point, if your changes look good and tests are passing, you are ready to create a pull request.

Github Actions will run our test suite against all supported versions. It's possible that your changes pass tests in one version but fail in another. In that case, you'll have to setup your development environment with the Gemfile for the problematic Rails version, and investigate what's going on.

## Merging a PR (maintainers only)

A PR can only be merged into master by a maintainer if: CI is passing, approved by another maintainer and is up to date with the default branch. Any maintainer is allowed to merge a PR if all of these conditions ae met.

## Shipping a release (maintainers only)

Maintainers need to do the following to push out a release:

* Create a feature branch from master and make sure it's up to date.
* Run `bin/prep-release [version]` and commit the changes. Use XYZ version format. NPM is handled automatically.
* Optional: To confirm the release contents, run TBD (extract contents) and `npm publish --dry-run`.
* Review and merge the PR.
* Run TBD from the default branch once the PR is merged.
* [Create a GitHub Release](https://github.com/Pythagora-io/gpt-pilot/releases/new) by selecting the tag and generating the release notes.
