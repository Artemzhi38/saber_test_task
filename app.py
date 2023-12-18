import os

import networkx as nx
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()
BUILDS_FOLDER_NAME = os.getenv("BUILDS_FOLDER_NAME")
BUILDS_FILE_NAME = os.getenv("BUILDS_FILE_NAME")
TASKS_FILE_NAME = os.getenv("TASKS_FILE_NAME")


class SortedTasksForBuildRequest(BaseModel):
    build_name: str


def sorted_tasks_for_build(build_name):
    """Function that reads .yaml files with builds and tasks dependencies, forms
    Directed Acyclic Graph, and uses it to properly sort the dependencies for
    required build"""
    # graph creation
    try:
        with open(
            os.path.join(
                os.path.dirname(__file__),
                BUILDS_FOLDER_NAME,
                f"{BUILDS_FILE_NAME}.yaml",
            )
        ) as file:
            builds_data = yaml.load(file, Loader=yaml.loader.SafeLoader)
        builds_with_tasks = {
            build["name"]: build["tasks"] for build in builds_data["builds"]
        }
        with open(
            os.path.join(
                os.path.dirname(__file__),
                BUILDS_FOLDER_NAME,
                f"{TASKS_FILE_NAME}.yaml",
            )
        ) as file:
            tasks_data = yaml.load(file, Loader=yaml.loader.SafeLoader)
        tasks_with_dependencies = {
            task["name"]: task["dependencies"] for task in tasks_data["tasks"]
        }
    except (FileNotFoundError, KeyError, TypeError):
        raise HTTPException(
            status_code=500,
            detail="One or two of required .yaml files on server-side are invalid",
        )

    all_dependencies = []  # graph edges
    for build, base_tasks in builds_with_tasks.items():
        all_dependencies.extend([(task, build) for task in base_tasks])
    for task, dependencies in tasks_with_dependencies.items():
        if dependencies:
            all_dependencies.extend(
                [(dep_task, task) for dep_task in dependencies]
            )
    builds_graph = nx.DiGraph(directed=True)
    builds_graph.add_nodes_from(tasks_with_dependencies.keys())  # tasks nodes
    builds_graph.add_nodes_from(builds_with_tasks.keys())  # builds nodes
    builds_graph.add_edges_from(all_dependencies)  # graph edges

    # returning sorted ancestors for target build node
    try:
        tasks_for_build = nx.ancestors(builds_graph, build_name)
    except nx.exception.NetworkXError:
        raise HTTPException(
            status_code=422, detail="There is no such build in .yaml file"
        )
    try:
        res = [
            task
            for task in nx.topological_sort(builds_graph)
            if task in tasks_for_build
        ]
    except nx.exception.NetworkXUnfeasible:
        raise HTTPException(
            status_code=500, detail=".yaml file contains cycle dependencies"
        )
    return res


app = FastAPI()


@app.post("/get_tasks")
async def get_tasks_for_build(build: SortedTasksForBuildRequest):
    """Endpoint for getting ordered(by their dependencies) list of tasks for
    required build. Accepts body with 'build_name' value."""
    return sorted_tasks_for_build(build.build_name)
