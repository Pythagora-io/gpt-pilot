import os
import time
from datetime import datetime, timedelta
from typing import cast
from git import Repo
from github import Github, Auth, AuthenticatedUser
from dotenv import load_dotenv
from utils.llm_connection import create_embedding
from helpers.embeddings import save_embeddings_to_file, load_embeddings_from_file, closest_items

load_dotenv()

EMBEDDING_FILE_NAME = os.path.join(os.path.dirname(__file__), 'template_repo_embeddings.pkl')
PRIVATE_EMBEDDING_FILE_NAME = os.path.join(os.path.dirname(__file__), 'template_repo_private_embeddings.pkl')


class GitHubTemplates:
    def __init__(self):
        self.access_token = os.getenv('GITHUB_TOKEN')
        # auth = None  # Auth.Token(project.args['github_token'])
        auth = Auth.Token(self.access_token)
        self.g = Github(auth=auth)

    def create_new_project(self, project, template_repo_full_name: str, organization: str = None):
        """
            Clones a GitHub template repo into the project workspace.
            Should call recommend_template_repositories() and set template_repo_full_name to the preferred repo.
            See: https://github.com/topics/template-repository

            Args:
            - template_repo_full_name: The full name of the template repository (e.g., "owner/repo_name").
            - organization: The organization where the new repo will be created. If None, the repo will be created in the user's account.
            """
        auth = Auth.Token(self.access_token)
        self.g = Github(auth=auth)
        template_repo = self.g.get_repo(template_repo_full_name)

        if organization is None:
            owner = cast(AuthenticatedUser, self.g.get_user())
        else:
            owner = self.g.get_organization(organization)

        new_repo = owner.create_repo_from_template(
            name=project.name,
            repo=template_repo,
            description=project.description,
            private=True,
        )

        Repo.clone_from(new_repo.clone_url, f"{project.root_path}")

    # technologies: list[str] = None,
    def recommend_template_repositories(self, user_description, repo_embeddings=None):
        # TODO: Use a vector DB such as Pinecone, Chroma, Milvus, Qdrant, Redis, Typesense, Weaviate or Zilliz
        if repo_embeddings is None:
            repo_embeddings = load_embeddings_from_file(EMBEDDING_FILE_NAME)

        user_embedding = create_embedding(user_description)

        # if (technologies is not None):
        #     lower_technologies = [tech.lower() for tech in technologies]
        #     repo_embeddings = [repo for repo in repo_embeddings if
        #                       any(tech in repo['data']['topics'] for tech in lower_technologies)]

        return sorted(closest_items(user_embedding, repo_embeddings, top_n=5), key=lambda x: -x['stars'])

    def get_template_repos(self, page_delay_seconds: float | None = 1):
        one_year_ago = datetime.now() - timedelta(days=365)
        # See https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories
        # No disrespect to cirosantilli or his cause, but his templates are not useful for project generation
        # leisurelicht/wtfpython-cn is also not a good template.
        query = f'template:true -user:cirosantilli -user:leisurelicht ' \
                f'stars:>100 pushed:>{one_year_ago.strftime("%Y-%m-%d")}'

        paged_repos = self.g.search_repositories(query, sort='stars', order='desc')

        if page_delay_seconds is None:
            return paged_repos

        loaded_repos = []
        for repo in paged_repos:
            loaded_repos.append(repo)
            if len(loaded_repos) % 30 == 0:
                time.sleep(page_delay_seconds)

        return loaded_repos

    def get_private_template_repos(self, organization: str = None):
        query = f'template:true is:private'
        user = self.g.get_user().login

        if organization is not None:
            query += f' (user:{user} OR org:{organization})'
        else:
            query += f' user:{user}'

        return self.g.search_repositories(query, sort='stars', order='desc')

    def get_embeddings(self, organization: str = None):
        # Generating embeddings for public template repos takes a long time, so we save them to a file
        if os.path.exists(EMBEDDING_FILE_NAME):
            embeddings = load_embeddings_from_file(EMBEDDING_FILE_NAME)
        else:
            repos = self.get_template_repos()
            embeddings = self._generate_embeddings_for_repos(repos, EMBEDDING_FILE_NAME)

        # Update the embeddings for private template repos only if the number of repos has changed
        if os.path.exists(PRIVATE_EMBEDDING_FILE_NAME):
            private_embeddings = load_embeddings_from_file(PRIVATE_EMBEDDING_FILE_NAME)
        else:
            private_embeddings = []

        private_repos = self.get_private_template_repos(organization)
        if private_repos.totalCount != len(private_embeddings):
            private_embeddings = self._generate_embeddings_for_repos(private_repos, PRIVATE_EMBEDDING_FILE_NAME)

        if len(private_embeddings) > 0:
            embeddings.extend(private_embeddings)

        return embeddings

    def generate_embeddings_for_public_repos(self):
        repos = self.get_template_repos()
        return self._generate_embeddings_for_repos(repos, EMBEDDING_FILE_NAME)

    def _generate_embeddings_for_repos(self, repos, file_name):
        repo_embeddings = []

        print('Generating embedding for template repositories...')
        for repo in repos:
            print(f'  {repo.full_name}')

            language = repo.language
            description = repo.description
            stars = repo.stargazers_count
            topics = repo.topics

            readme_content = self._get_readme_content(repo)
            text = repo.full_name
            if description is not None:
                description = description[:1000]
                text += '\n' + description
            if language is not None:
                text += '\n' + language
            if topics is not None:
                text += '\n' + ' '.join(topics)
            if readme_content is not None:
                text += '\n' + readme_content[:5000]

            embedding = create_embedding(text)

            repo_embeddings.append({
                "data": {
                    "repo": repo.full_name,
                    "description": description,
                    "stars": stars,
                    "language": language,
                    "topics": topics,
                },
                "embedding": embedding,
            })

            # TODO: If saving to the DB, probably better as { type, data, embedding }
            # save_template_repo(repo.full_name, language, description, embedding)

        save_embeddings_to_file(repo_embeddings, file_name)
        return repo_embeddings

    def _get_readme_content(self, repo):
        try:
            # Get the content of the README file
            readme = repo.get_readme()
            return readme.decoded_content.decode('utf-8')
        except:
            return ""
