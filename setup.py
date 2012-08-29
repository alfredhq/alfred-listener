from setuptools import setup, find_packages


setup(
    name='alfred-listener',
    version='0.1.dev',
    license='ISC',
    description='Alfred webhooks listener app',
    url='https://github.com/alfredhq/alfred-listener',
    author='Alfred Developers',
    author_email='team@alfredhq.com',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'SQLAlchemy',
        'argh',
        'PyYAML',
        'Flask-Alfred-DB',
        'simplejson'
    ],
    entry_points={
        'console_scripts': [
            'alfred-listener = alfred_listener.__main__:main'
        ],
    }
)
