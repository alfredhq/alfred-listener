import yaml


def configure(app, filename):
    with open(filename) as file:
        data = yaml.load(file)
    for key, value in data.items():
        app.config[key.upper()] = value
