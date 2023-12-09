from dataclasses import dataclass
from pathlib import Path
import tomllib

from justdays import Day


@dataclass
class Check:
    id: str
    description: str
    prompt: str
    check_type: type
    options: list[str]
    required: bool = True
    passed: bool = False
    value: str = ""

    def serializable(self):
        if self.check_type == Day:
            check_type = 'date'
            value = str(self.value)
        else:
            check_type = 'str'
            value = self.value
        return {'id': self.id, 'description': self.description, 'prompt': self.prompt, 'check_type': check_type,
                'options': self.options, 'required':self.required, 'passed': self.passed, 'value': value}


class Checks:
    def __init__(self, toml_file_name:str=None):
        self.checks = []
        if toml_file_name:
            self.load(toml_file_name)

    def get(self, id):
        for check in self.checks:
            if check.id == id:
                return check
        raise ValueError(f"Check with id {id} not found")

    def load(self, toml_file_name:str):
        checks_file = Path(__file__).parent / toml_file_name
        with open(checks_file, 'rb') as f:
            data = tomllib.load(f)

        self.checks = []

        for id, item in data.items():
            name = item['description']
            prompt = item['prompt']
            check_type = Day if item.get('type') == 'datum' else str
            options = item.get('options', [])
            required = item.get('required', True)
            self.checks += [Check(id, name, prompt, check_type, options, required)]

        return self.checks

    def __getitem__(self, index):
        return self.checks[index]

    def __iter__(self):
        return iter(self.checks)

    def add(self, check):
        self.checks += [check]

    def serializable(self):
        return [check.serializable() for check in self.checks]

