# Backend

## How to start it up
### Startup database for local development
To spin up the database for local testing/development follow the following steps:
1. Install [docker](https://docs.docker.com/engine/install/)
2. install [uv](https://docs.astral.sh/uv/) (explanation down below)
    - fastest way for mac and linux is: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - for Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
3. Install pandoc in a way that works for you (on Mac typically using brew)
4. For Mac/Linux: run `chmod +x ./scripts/setup.sh && ./scripts/setup.sh`
5. For Windows: run `bash ./scripts/setup.sh` (This works in PowerShell with Docker WSL integration enabled)
   
<br>
If you want to also insert a few sample files to the database as well as the s3 storage, you can insted replace step three with the following: <br>

1. For Max/Linux: run `chmod +x ./setup_with_samples.sh && ./setup_with_samples.sh`
2. For Windows: run `bash ./setup_with_samples.sh` (This works in PowerShell with Docker WSL integration enabled)

If everthing worked as intended, the postgressql database and the s3 storage are now running and ready to be worked with

#### Delete database and volumes

Sometimes, maybe if something goes wrong, you want to test something, or for some other reason, you want to delete the database and start with a clean one, simply follow the following steps:

1. stop and delete the running docker containers (in the dashboard using docker desktop simply click on the bin for the aiforscience docker compose) 
2. Delete the volumes folder
3. Run one of the setup scripts and afterwards you are good to go again

### Start the backend
1. install [uv](https://docs.astral.sh/uv/) (explanation down below)
    - fastest way for mac and linux is: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - for Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. run `uv run run.py`


### How to use uv

We chose uv as our tool of choice because it’s lightweight, fast, and is a all in one tool for python projects and dependency management. It handles everything that needs to be taken care of in the background and this while being extremly fast. 

Here is a small guide on how to work with it:

To run a python file, e.g. to start the Flask app, simply run:

`uv run run.py`

This command not only uses uv to execute run.py, which starts your Flask backend, but also grabs the fitting python version, creates a virtual environment and installs everything it needs all by itself, according to the pyproject.toml and the uv.lock.

To add a dependency, where you would normally write a `pip install XYZ` you now run <br>

`uv add XYZ` <br>

This installs the package into your environment and adds it to the pyproject.toml

To delete a dependency, you can eiter delete it from the pyproject.toml or run <br>

`uv remove XYZ` 

To run ruff with uv, you can use <br>

 `uv run ruff check (--fix)` <br> 
 
 and <br>

 `uv run ruff format` <br>

 To run the tests in the tests folder simply run <br>

 `uv run pytest` <br>

 

For further information and advanced configuration options, you can refer to the uv documentation, or ask @Antim8
