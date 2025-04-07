#!/usr/bin/env python3

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime

import requests
from github import Auth, Github
from tabulate import tabulate

logging.basicConfig(level=logging.INFO)

NEOVIM_AWESOME_README_URL = "https://raw.githubusercontent.com/rockerBOO/awesome-neovim/refs/heads/main/README.md"
README_H2_PATTERN = r"^## (.+)$"
README_PLUGIN_PATTERN = r"\[([^/]+)/([^/)]+)\]\(https://github.com/\1/\2\)( - (.+))?"

github = Github(auth=Auth.Token(os.environ["GITHUB_TOKEN"]))


@dataclass
class Plugin:
    owner: str
    name: str
    description: str | None
    stars: int = field(init=False)
    last_commit: datetime = field(init=False)

    def __post_init__(self):
        repo = github.get_repo(f"{self.owner}/{self.name}")
        self.stars = repo.stargazers_count
        self.last_commit = repo.pushed_at
        if repo.description:
            self.description = repo.description
        logging.info(
            f"Fetched info for {self.owner}/{self.name}: {self.stars} stars"
            + f", last commit {self.last_commit}"
        )

    def markdown_fields(self) -> list:
        return [
            f"[{self.owner}/{self.name}]"
            + f"(https://github.com/{self.owner}/{self.name})",
            self.stars,
            self.last_commit.strftime("%d-%m-%Y"),
            self.description or "",
        ]


def download_neovim_awesome_readme() -> str:
    response = requests.get(NEOVIM_AWESOME_README_URL)
    response.raise_for_status()
    return response.text


neovim_awesome_readme = download_neovim_awesome_readme()

category: str = "Unknown"
category_to_plugins: dict[str, list[Plugin]] = {}

for line in neovim_awesome_readme.splitlines():
    h2_match = re.match(README_H2_PATTERN, line)
    if h2_match:
        category = h2_match.group(1)
        continue

    plugin_match = re.search(README_PLUGIN_PATTERN, line)
    if plugin_match:
        # TODO: Support specific links, like the ones to mini.nvim
        author = plugin_match.group(1)
        name = plugin_match.group(2)
        description = plugin_match.group(4)
        plugin = Plugin(author, name, description)
        category_plugins = category_to_plugins.get(category, [])
        category_plugins.append(plugin)
        category_to_plugins[category] = category_plugins
        continue

    # TODO: Check plugins from sources other than GitHub

print("# Awesome Neovim Plugins")
print()
for category, plugins in category_to_plugins.items():
    plugins = sorted(plugins, key=lambda p: p.stars, reverse=True)
    markdown_table = tabulate(
        map(lambda p: p.markdown_fields(), plugins),
        headers=["URL", "Stars", "Last commit", "Description"],
        tablefmt="github",
    )

    print(f"## {category}")
    print()
    print(markdown_table)
    print()
