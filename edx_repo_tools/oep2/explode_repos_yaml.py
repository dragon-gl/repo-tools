"""
``oep2 explode``: Split out edx/repo-tools-data:repos.yaml into individual
openedx.yaml files in specific repos.
"""

import click
from github3.exceptions import NotFoundError
import logging
import textwrap
import yaml

from edx_repo_tools.auth import pass_github
from edx_repo_tools.data import iter_openedx_yaml, OPEN_EDX_YAML
from edx_repo_tools.utils import dry_echo, dry


logging.basicConfig()
LOGGER = logging.getLogger(__name__)

BRANCH_NAME = 'add-openedx-yaml'


@click.command()
@pass_github
@dry
def explode(hub, dry):
    """
    Explode the repos.yaml file out into pull requests for all of the
    repositories specified in that file.
    """

    repo_tools_data = hub.repository('edx', 'repo-tools-data')
    repos_yaml = repo_tools_data.file_contents('repos.yaml').decoded

    repos = yaml.safe_load(repos_yaml)

    for repo, repo_data in repos.items():
        user, _, repo_name = repo.partition('/')

        if repo_data is None:
            repo_data = {}

        if 'owner' not in repo_data:
            repo_data['owner'] = 'MUST FILL IN OWNER'
        if 'area' in repo_data:
            repo_data.setdefault('tags', []).append(repo_data['area'])
            del repo_data['area']
        repo_data.setdefault('oeps', {})

        file_contents = yaml.safe_dump(repo_data, indent=4)

        file_contents = textwrap.dedent("""
            # This file describes this Open edX repo, as described in OEP-2:
            # http://open-edx-proposals.readthedocs.io/en/latest/oeps/oep-0002.html#specification

            {}
        """).format(file_contents).strip() + "\n"

        gh_repo = hub.repository(user, repo_name)

        if gh_repo.fork:
            LOGGER.info("Skipping %s because it is a fork", gh_repo.full_name)
            continue

        try:
            parent_commit = gh_repo.branch(gh_repo.default_branch).commit.sha
        except:
            LOGGER.warning(
                "No commit on default branch %s in repo %s",
                gh_repo.default_branch,
                gh_repo.full_name
            )
            continue

        if not dry:
            if gh_repo.branch(BRANCH_NAME) is None:
                gh_repo.create_ref(
                    'refs/heads/{}'.format(BRANCH_NAME),
                    parent_commit
                )

        try:
            contents = gh_repo.file_contents(OPEN_EDX_YAML, ref=BRANCH_NAME)
        except NotFoundError:
            contents = None

        if contents is None:
            dry_echo(
                dry,
                "Creating openedx.yaml file on branch {repo}:{branch}".format(
                    repo=gh_repo.full_name,
                    branch=BRANCH_NAME,
                ),
                fg='green',
            )
            click.secho(file_contents, fg='blue')
            if not dry:
                try:
                    gh_repo.create_file(
                        path=OPEN_EDX_YAML,
                        message='Add an OEP-2 compliant openedx.yaml file',
                        content=file_contents,
                        branch=BRANCH_NAME,
                    )
                except TypeError:
                    # Sadly, TypeError means there was a permissions issue...
                    LOGGER.exception("Unable to create openedx.yaml")
                    continue
        else:
            if contents.decoded != file_contents:
                dry_echo(
                    dry,
                    "Updated openedx.yaml file on branch {repo}:{branch}".format(
                        repo=gh_repo.full_name,
                        branch=BRANCH_NAME,
                    ),
                    fg='green',
                )
                click.secho(file_contents, fg='blue')
                if not dry:
                    gh_repo.update_file(
                        path=OPEN_EDX_YAML,
                        message='Update the OEP-2 openedx.yaml file',
                        content=file_contents,
                        branch=BRANCH_NAME,
                        sha=contents.sha if contents is not None else None,
                    )

        pr_body = textwrap.dedent("""
            This adds an `openedx.yaml` file, as described by OEP-2:
            http://open-edx-proposals.readthedocs.io/en/latest/oeps/oep-0002.html

            The data in this file was transformed from the contents of
            edx/repo-tools-data:repos.yaml
        """)
        pr_title = 'Add an OEP-2 compliant openedx.yaml file'

        existing_pr = [
            pr
            for pr
            in gh_repo.pull_requests(
                head='edx:{}'.format(BRANCH_NAME),
                state='open'
            )
        ]

        if existing_pr:
            pull = existing_pr[0]
            if pull.title != pr_title or pull.body != pr_body:
                dry_echo(
                    dry,
                    textwrap.dedent("""\
                        Updated pull request {repo}#{number}: {title}
                            URL: {url}
                    """).format(
                        url=pull.html_url,
                        repo=gh_repo.full_name,
                        number=pull.number,
                        title=pull.title,
                    ),
                    fg='green'
                )

                if not dry:
                    pull.update(
                        title=pr_title,
                        body=pr_body,
                    )
        else:
            dry_echo(
                dry,
                textwrap.dedent("""\
                    Created pull request {repo}#{number}: {title}
                        URL: {url}
                """).format(
                    url=pull.html_url if not dry else "N/A",
                    repo=gh_repo.full_name,
                    number=pull.number if not dry else "XXXX",
                    title=pull.title if not dry else pr_title,
                ),
                fg='green'
            )

            if not dry:
                pull = gh_repo.create_pull(
                    title=pr_title,
                    base=gh_repo.default_branch,
                    head=BRANCH_NAME,
                    body=pr_body
                )


@click.command()
@pass_github
@click.option('--org', multiple=True, default=['edx', 'edx-ops', 'edx-solutions',])
@click.option(
    '--branch',
    multiple=True,
    default=None,
    help="The branch(es) to examine for openedx.yaml files. If more than one, "
         "the first found will be used."
)
def implode(hub, org, branch):
    """
    Implode all openedx.yaml files, and print the results as formatted output.
    """
    data = {
        repo.full_name: openedx_yaml
        for repo, openedx_yaml
        in iter_openedx_yaml(hub, org, branch)
    }
    click.echo(yaml.safe_dump(data, encoding=None, indent=4))
