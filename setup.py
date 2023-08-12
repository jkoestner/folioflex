from setuptools import setup, find_packages


def read_req_file():
    with open("requirements.txt") as fp:
        requires = (line.strip() for line in fp)
        return [req for req in requires if req and not req.startswith("#")]


def get_version():
    version = "unknown"
    with open("iex/version.py") as f:
        line = f.read().strip()
        version = line.replace("version = ", "").replace('"', "")
        return version


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="iex",
    version=get_version(),
    author="John Koestner",
    author_email="johnkoestner@outlook.com",
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    package_data={"iex": ["configs/*"]},
    license="MIT",
    description=("A collection of portfolio tracking capabilities"),
    long_description=readme(),
    long_description_content_type="text/markdown",
    install_requires=read_req_file(),
    python_requires=">=3.6",
    url="https://github.com/jkoestner/iex",
)
