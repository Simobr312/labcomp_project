import os
import json
import asyncio
import tempfile
from functools import lru_cache
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

# Import from our new geometric DSL modules
from src.parser import parse_ast
from src.core import eval_program
from src.export import serialize_environment, export_polylogica_json

app = FastAPI()

class ProgramInput(BaseModel):
    program: str

class QueryInput(BaseModel):
    program: str  # Added DSL program input
    query: str

# Cache for compiled environments to avoid redundant parsing and evaluation (I don't really know if it works, it's the first time I use lru_cache)
@lru_cache(maxsize=128)
def get_compiled_environment(program: str):
    """
    Caches the AST parsing and evaluation. 
    If the exact same program string is passed, it skips recompilation.
    """
    ast = parse_ast(program)
    return eval_program(ast)

@app.post("/run_program")
async def run_program(data: ProgramInput):
    """Executes the provided DSL program and returns the environment as JSON."""
    try:
        # Fetch from cache or compile if new
        env = get_compiled_environment(data.program)
        return serialize_environment(env)
    except Exception as e:
        return {"success": False, "error": str(e)}
    
@app.post("/run_polylogica")
async def run_polylogica(data: QueryInput):
    """Executes the DSL program, exports it to PolyLogicA format, runs the provided query, and returns the results."""
    try:
        try:
            env = get_compiled_environment(data.program)
        except Exception as dsl_error:
            return {"success": False, "error": f"DSL Compilation Error: {str(dsl_error)}"}

        # Isolate file generation using a temporary directory
        # To use PolyLogicA, we need to create a temporary JSON file for the mesh and a temporary query file for the query, then run the PolyLogicA executable in that context.
        # This strategy is ok for now, but in the future, we might want to consider to store the mesh in a database or find other ways to avoid writing to disk, especially if we want to make this a web service and not a local executable.
        with tempfile.TemporaryDirectory() as tmpdir:
            mesh_filename = os.path.join(tmpdir, "temp_mesh.json")
            query_filename = os.path.join(tmpdir, "query.imgql")
            result_filename = os.path.join(tmpdir, "result.json")

            # Export the geometric mesh context to JSON
            export_polylogica_json(env, mesh_filename)

            # Build the modified query text
            modified_query = f'load mesh = "{mesh_filename}"\n' + data.query
            with open(query_filename, "w", encoding="utf-8") as f:
                f.write(modified_query)

            # 5. Execute your functioning terminal configuration asynchronously
            # Note: We pass absolute path for the executable, but run it *inside* the temp dir
            executable_path = os.path.abspath("./linux-x64/PolyLogicA")
            command = f"{executable_path} {query_filename}"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,  # Forces PolyLogicA to output 'result.json' into our isolated folder
                env=os.environ.copy(),
                executable="/bin/bash"
            )
            
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip() or f"Process exited with code {process.returncode}\nOutput: {stdout.decode().strip()}"
                return {"success": False, "error": error_msg}

            # 6. Read and parse the generated result.json file
            if os.path.exists(result_filename):
                with open(result_filename, "r", encoding="utf-8") as f:
                    properties = json.load(f)
            else:
                stdout_content = stdout.decode().strip()
                try:
                    properties = json.loads(stdout_content)
                except json.JSONDecodeError:
                    return {"success": False, "error": f"Could not find result.json or parse stdout."}

            # Deliver the structured properties dictionary
            return {
                "success": True,
                "properties": properties
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Server Core Error: {str(e)}"
        }
    
app.mount("/", StaticFiles(directory="web/frontend", html=True), name="frontend")