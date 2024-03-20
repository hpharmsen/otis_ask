from dataclasses import dataclass
from pathlib import Path
import tomllib
import json
from typing import TypeAlias

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
        elif self.check_type == float:
            check_type = 'float'
            value = self.value
        elif self.check_type == int:
            check_type = 'int'
            value = self.value
        else:
            check_type = 'str'
            value = self.value
        return {'id': self.id, 'description': self.description, 'prompt': self.prompt, 'check_type': check_type,
                'options': self.options, 'required': self.required, 'passed': self.passed, 'value': value}


class Checks:
    def __init__(self, toml_file_name: str = None):
        self.checks = []
        if toml_file_name:
            self.load(toml_file_name)

    def get(self, check_id):
        for check in self.checks:
            if check.id == check_id:
                return check
        raise ValueError(f"Check with id {check_id} not found")

    def load(self, toml_file_name: str):
        checks_file = Path(__file__).parent / toml_file_name
        print([f for f in Path('/').iterdir()])
        with open(checks_file, 'rb') as f:
            data = tomllib.load(f)

        self.checks = []

        for check_id, item in data.items():
            name = item['description']
            prompt = item['prompt']
            match item.get('type'):
                case 'day':
                    check_type = Day
                case 'float':
                    check_type = float
                case 'int':
                    check_type = int
                case _:
                    check_type = str
            options = item.get('options', [])
            required = item.get('required', True)
            self.checks += [Check(check_id, name, prompt, check_type, options, required)]

        return self.checks

    def __getitem__(self, index):
        return self.checks[index]

    def __iter__(self):
        return iter(self.checks)

    def __bool__(self):
        return len(self.checks) > 0

    def __len__(self):
        return len(self.checks)

    def add(self, check):
        self.checks += [check]

    def serializable(self):
        return [check.serializable() for check in self.checks]

    def deserialize(self, json_str):
        data = json.loads(json_str)
        self.checks = []
        for item in data:
            check = Check(item['id'], item['description'], item['prompt'], item['check_type'], item['options'],
                          item['required'], item['passed'], item['value'])
            self.checks += [check]
        return self.checks


# For type hints
ChecksDict: TypeAlias = dict[str, Checks]
