import os
from typing import cast
from git import Repo
from github import Github, Auth, AuthenticatedUser
from dotenv import load_dotenv
from utils.llm_connection import get_embedding
from database.database import save_template_repo
from helpers.embeddings import save_embeddings_to_file, load_embeddings_from_file, closest_items

load_dotenv()

EMBEDDING_FILE_NAME = 'embeddings.pkl'


class GitHubTemplate:
    def __init__(self):
        self.access_token = os.getenv('GITHUB_TOKEN')
        # auth = None  # Auth.Token(project.args['github_token'])
        auth = Auth.Token(self.access_token)
        self.g = Github(auth=auth)

    def get_template_repos(self):
        return self.g.search_repositories('topic:template-repository')
        # return self.g.search_topics('template-repository')

    def create_new_project(self, workspace: str, project_name: str, template_repo_full_name: str, organization: str = None):
        """
            Clones a GitHub template repo into a specified workspace.
            See: https://github.com/topics/template-repository

            Args:
            - workspace: The local directory where the repo will be cloned.
            - new_repo_name: The name (without the owner prefix) of the new repository to be created from the template.
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
            name=project_name,
            repo=template_repo,
            description='A new project created from the gpt-pilot template',
            private=False,
        )

        Repo.clone_from(new_repo.clone_url, f"{workspace}/{project_name}")

    def recommend_template_repositories(self, user_description, repo_embeddings=None):
        # TODO: Use a vector DB such as Pinecone, Chroma, Milvus, Qdrant, Redis, Typesense, Weaviate or Zilliz
        if repo_embeddings is None:
            repo_embeddings = load_embeddings_from_file(EMBEDDING_FILE_NAME)

        user_embedding = get_embedding(user_description)

        return closest_items(user_embedding, repo_embeddings, top_n=5)

    def generate_embeddings_for_repos(self):
        if os.path.exists(EMBEDDING_FILE_NAME):
            return load_embeddings_from_file(EMBEDDING_FILE_NAME)

        repos = self.get_template_repos()
        repo_embeddings = []

        print('Generating embedding for template repositories...')
        for repo in repos:
            print(f'  {repo.full_name}')

            language = repo.language
            description = repo.description
            stars = repo.stargazers_count
            labels = []
            for label in repo.get_labels():
                labels.append(label.name)

            readme_content = self._get_readme_content(repo)
            embedding = get_embedding(f''''
                Language: {language}
                Labels: {labels}
                Stars: {stars}
                {description}
            ''' + readme_content)

            repo_embeddings.append({
                "data": {
                    "repo": repo.full_name,
                    "description": description,
                    "stars": stars,
                    "language": language,
                    "labels": labels,
                },
                "embedding": embedding,
            })

            # TODO: If saving to the DB, probably better as { type, data, embedding }
            # save_template_repo(repo.full_name, language, description, embedding)

        save_embeddings_to_file(repo_embeddings, EMBEDDING_FILE_NAME)
        return repo_embeddings

    def _get_readme_content(self, repo):
        try:
            # Get the content of the README file
            readme = repo.get_readme()
            return readme.decoded_content.decode('utf-8')
        except:
            return ""
