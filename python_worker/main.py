from fastapi import FastAPI, Request
import uvicorn
import sys
from io import StringIO
import inspect

app = FastAPI()

@app.post("/execute")
async def execute(request: Request):
    data = await request.json()
    code = data.get("code")
    input_data = data.get("input")
    
    # Capture print outputs
    stdout = StringIO()
    sys.stdout = stdout
    
    try:
        # Create a clean globals dictionary
        exec_globals = {}
        
        # Execute the code
        exec(code, exec_globals)
        
        # Get the main function
        main_func = exec_globals.get("main")
        if not main_func:
            raise Exception("No 'main' function defined")
        
        # Call main function based on input type
        if input_data is None:
            result = main_func()
        elif isinstance(input_data, list):
            # If input is a list, pass as multiple arguments
            result = main_func(*input_data)
        elif isinstance(input_data, dict):
            # If input is a dict, pass as keyword arguments
            result = main_func(**input_data)
        else:
            # Single input
            result = main_func(input_data)
        
        # Get any printed output
        printed_output = stdout.getvalue()
        
        # Prepare response
        response = {
            "result": result,
            "printed": printed_output if printed_output else None,
            "error": None
        }
        
        return response
        
    except Exception as e:
        return {"error": str(e), "result": None, "printed": None}
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)