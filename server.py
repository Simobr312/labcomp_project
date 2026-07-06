from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles

# Import from our new geometric DSL modules
from parser import parse_ast
from core import eval_program, serialize_environment

app = FastAPI()

class ProgramInput(BaseModel):
    program: str

@app.post("/run_program")
def run_program(data: ProgramInput):
    try:
        # 1. Parse the code into an AST
        ast = parse_ast(data.program)
        
        # 2. Evaluate the program to populate the environment
        env = eval_program(ast)

        # 3. Use the helper function to format the output for the JS frontend
        # serialize_environment already returns {"success": True, "complexes": {...}}
        return serialize_environment(env)

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Mount the static files for the frontend
# Note: Added html=True so FastAPI automatically serves index.html at the root URL
app.mount("/", StaticFiles(directory="web/frontend", html=True), name="frontend") 