import sys
import os


def get_project_dir() -> str:

    """Get the absolute path to the project root directory.

    Returns:
        Absolute path to the TeachingMonster repository root.
    """

    platform = sys.platform

    if platform == 'linux':
        dir_as_list = os.path.dirname(__file__).split("/")
    else:
        dir_as_list = os.path.dirname(__file__).split("\\")
    index = dir_as_list.index("src")
    project_directory = "/".join(dir_as_list[:index])

    return project_directory


def get_file(relative_path: str) -> str:

    """Resolve a project-relative path to an absolute path.

    Args:
        relative_path: Path relative to the project root directory.

    Returns:
        Absolute path resolved from the project root.
    """

    return os.path.join(get_project_dir(), relative_path)
