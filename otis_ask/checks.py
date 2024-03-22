from dataclasses import dataclass
from pathlib import Path
import tomllib
import json
from typing import TypeAlias

from justdays import Day


class Check:
    def __init__(self, check_id: str, description: str, prompt: str, check_type: type, options: list[str],
                 required: bool=True, texts: dict=None, passed: bool=False, value: [str, float, int, Day]=None):
        self.id = check_id
        self.description = description
        self.prompt = prompt
        self.check_type = check_type
        self.options = options
        self.required = required
        self.texts = texts
        self.passed = passed
        self.value = value
        assert type(self.check_type) == type
        assert self.value is None or self.check_type != Day or type(self.value) == Day

    @classmethod
    def deserialize(cls, item):
        if item['check_type'] == 'date':
            value = Day(item['value'])
            check_type = Day
        elif item['check_type'] == 'float':
            value = float(item['value'])
            check_type = float
        elif item['check_type'] == int:
            value = int(item['value'])
            check_type = int
        else:
            value = item['value']
            check_type = str

        return cls(item['id'], item['description'], item['prompt'], check_type, item['options'],
                   item['required'], item['texts'], item['passed'], value)

    def serializable(self):
        if self.check_type == Day:
            check_type = 'date'
        elif self.check_type == float:
            check_type = 'float'
        elif self.check_type == int:
            check_type = 'int'
        else:
            check_type = 'str'
        return {'id': self.id, 'description': self.description, 'prompt': self.prompt,
                'check_type': check_type, 'options': self.options, 'required': self.required,
                'passed': self.passed, 'value': str(self.value), 'texts': self.texts}


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
            texts = {key[5:].replace('_', ' '): value for key, value in item.items() if key.startswith('text_')}
            self.checks += [Check(check_id, name, prompt, check_type, options, required, texts)]

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
        self.checks = [Check.deserialize(item) for item in data]
        return self.checks


# For type hints
ChecksDict: TypeAlias = dict[str, Checks]
