import os

import pytest
import yaml
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app import app

load_dotenv()
BUILDS_FOLDER_NAME = os.getenv("BUILDS_FOLDER_NAME")
BUILDS_FILE_NAME = os.getenv("BUILDS_FILE_NAME")
TASKS_FILE_NAME = os.getenv("TASKS_FILE_NAME")
client = TestClient(app)


@pytest.fixture(scope="module")
def temporary_tasks_file():
    """Fixture for creating temporary tasks file for tests"""
    path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        BUILDS_FOLDER_NAME,
        f"{TASKS_FILE_NAME}.yaml",
    )
    open(path, "w+").close()
    yield path
    os.remove(path)


@pytest.fixture(scope="module")
def temporary_builds_file():
    """Fixture for creating temporary builds file for tests"""
    path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        BUILDS_FOLDER_NAME,
        f"{BUILDS_FILE_NAME}.yaml",
    )
    open(path, "w+").close()
    yield path
    os.remove(path)


def test_wrong_build_name_response(temporary_tasks_file, temporary_builds_file):
    """Test function that checks if response is correct when build name given to
    '/get_tasks' endpoint isnot listed in .yaml file"""
    tasks_dict = {
        "tasks": [
            {"name": "task1", "dependencies": []},
            {"name": "task2", "dependencies": []},
        ]
    }
    builds_dict = {"builds": [{"name": "build1", "tasks": ["task1", "task2"]}]}
    with open(temporary_tasks_file, "w") as testfile:
        yaml.dump(tasks_dict, testfile, allow_unicode=True)
    with open(temporary_builds_file, "w") as testfile:
        yaml.dump(builds_dict, testfile, allow_unicode=True)
    response = client.post("/get_tasks", json={"build_name": "not_real_build"})
    assert response.status_code == 422
    assert response.json()["detail"] == "There is no such build in .yaml file"


def test_cyclic_dependencies_response(
    temporary_tasks_file, temporary_builds_file
):
    """Test function that checks if response is correct when there is cyclic
    dependency in .yaml file"""
    tasks_dict = {
        "tasks": [
            {"name": "task1", "dependencies": ["task2"]},
            {"name": "task2", "dependencies": ["task1"]},
        ]
    }
    builds_dict = {
        "builds": [
            {
                "name": "build_with_cyclic_task_dependencies",
                "tasks": ["task1", "task2"],
            }
        ]
    }
    with open(temporary_tasks_file, "w") as testfile:
        yaml.dump(tasks_dict, testfile, allow_unicode=True)
    with open(temporary_builds_file, "w") as testfile:
        yaml.dump(builds_dict, testfile, allow_unicode=True)
    response = client.post(
        "/get_tasks", json={"build_name": "build_with_cyclic_task_dependencies"}
    )
    assert response.status_code == 500
    assert response.json()["detail"] == ".yaml file contains cycle dependencies"


def test_invalid_yaml_file_response(
    temporary_tasks_file, temporary_builds_file
):
    """Test function that checks if response is correct when .yaml files are
    invalid"""
    tasks_dict = {}
    builds_dict = {}
    with open(temporary_tasks_file, "w") as testfile:
        yaml.dump(tasks_dict, testfile, allow_unicode=True)
    with open(temporary_builds_file, "w") as testfile:
        yaml.dump(builds_dict, testfile, allow_unicode=True)
    response = client.post(
        "/get_tasks", json={"build_name": "invalid_files_build"}
    )
    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "One or two of required .yaml files on server-side are invalid"
    )


def test_missing_yaml_file_response():
    """Test function that checks if response is correct when .yaml files are
    missing"""
    response = client.post("/get_tasks", json={"build_name": "no_files_build"})
    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "One or two of required .yaml files on server-side are invalid"
    )


def test_empty_yaml_file_response(temporary_tasks_file, temporary_builds_file):
    """Test function that checks if response is correct when .yaml files are
    empty"""
    response = client.post("/get_tasks", json={"build_name": "no_files_build"})
    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "One or two of required .yaml files on server-side are invalid"
    )


def test_correct_task_sorting_algorythm_for_build_response(
    temporary_tasks_file, temporary_builds_file
):
    """Test function that checks if sorting algorythm for task dependencies is
    correct"""
    tasks_dict = {
        "tasks": [
            {"name": "task1", "dependencies": ["task4"]},
            {"name": "task2", "dependencies": ["task6"]},
            {"name": "task3", "dependencies": []},
            {"name": "task4", "dependencies": ["task5"]},
            {"name": "task5", "dependencies": []},
            {"name": "task6", "dependencies": []},
        ]
    }
    builds_dict = {
        "builds": [{"name": "build1", "tasks": ["task1", "task2", "task3"]}]
    }
    with open(temporary_tasks_file, "w") as testfile:
        yaml.dump(tasks_dict, testfile, allow_unicode=True)
    with open(temporary_builds_file, "w") as testfile:
        yaml.dump(builds_dict, testfile, allow_unicode=True)
    response = client.post("/get_tasks", json={"build_name": "build1"})
    assert response.status_code == 200
    sorted_tasks = response.json()
    assert (
        sorted_tasks.index("task1")
        > sorted_tasks.index("task4")
        > sorted_tasks.index("task5")
    )
    assert sorted_tasks.index("task2") > sorted_tasks.index("task6")
    assert sorted_tasks.index("task1") > sorted_tasks.index("task2")
    assert sorted_tasks.index("task2") > sorted_tasks.index("task3")
    assert sorted_tasks.index("task2") > sorted_tasks.index("task5")
    assert sorted_tasks.index("task4") > sorted_tasks.index("task6")
    assert sorted_tasks.index("task4") > sorted_tasks.index("task3")
