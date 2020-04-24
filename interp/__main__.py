import sys

from prompt_toolkit import PromptSession

from interp.interpreter import Interpreter
from interp.interpreter import InterpretableWrapper
import app.phrasebook
import app.nlp

interpreter = Interpreter({
    "phrasebook": lambda _: InterpretableWrapper(app.phrasebook.PhrasebookApp()),
    "nlp": lambda _: InterpretableWrapper(app.nlp.NLP())
})
prompt = PromptSession()

file_input = []
if len(sys.argv) == 2:
    with open(sys.argv[1], 'r') as f:
        file_input = f.readlines()
    print(f"loaded {len(file_input)} from {sys.argv[1]}...")

while True:
    statement = file_input.pop(0) if file_input else prompt.prompt("> ")
    if not statement.strip():
        continue
    try:
        print(f">> {statement}")
        interpreter(statement)
    except Exception as e:
        print(f"fatal error: {str(e)}")
        exit(1)
