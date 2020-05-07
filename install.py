import zipfile
import platform
import sys
import subprocess
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from email.parser import BytesHeaderParser

import requests
from requests_html import HTMLSession
from packaging.version import parse as parse_ver
from packaging.specifiers import SpecifierSet
from pkg_resources import Requirement

from resolvelib.providers import AbstractProvider
from resolvelib.reporters import BaseReporter
from resolvelib.resolvers import Resolver

PYTHON_VERSION = platform.python_version()


@dataclass
class Candidate:
    name: str
    version: str
    link: str

    def get_dependencies(self):
        for req in self.metadata.get_all("Requires-Dist", []):
            r = Requirement(req)
            if not r.marker:
                yield r
            elif r.marker.evaluate({"extra": None}):  # We don't consider markers for this demo
                yield r

    @property
    def metadata(self):
        resp = requests.get(self.link)
        with zipfile.ZipFile(BytesIO(resp.content)) as zf:
            for n in zf.namelist():
                if n.endswith(".dist-info/METADATA"):
                    p = BytesHeaderParser()
                    return p.parse(zf.open(n))
        return None

    def install(self, target_path):
        args = [sys.executable, "-m", "pip", "install", "--no-deps", "--target", target_path, self.link]
        subprocess.check_call(args)


def get_all_candidates(requirement):
    session = HTMLSession()
    url = f"https://pypi.org/simple/{requirement.key}"
    resp = session.get(url)
    for a in resp.html.find('a'):
        link = a.attrs['href']
        python_requires = a.attrs.get('data-requires-python')
        filename = a.text

        if python_requires:
            spec = SpecifierSet(python_requires)
            if not spec.contains(PYTHON_VERSION):
                # Discard candidates that don't match the Python version.
                continue

        if not filename.endswith(".whl"):
            # Only parse wheels for this demo
            continue
        name, version = filename.split("-")[:2]
        if requirement.specifier.contains(version):
            yield Candidate(name, version, link)


class Provider(AbstractProvider):
    def identify(self, dependency):

        return dependency.key

    def get_preference(self, resolution, candidates, information):

        return len(candidates)

    def find_matches(self, requirement):
        # Most recent version is at the last of the list.
        return sorted(get_all_candidates(requirement), key=lambda r: parse_ver(r.version))

    def is_satisfied_by(self, requirement, candidate):

        return candidate.version in requirement.specifier

    def get_dependencies(self, candidate):

        return list(candidate.get_dependencies())


def main(requirements):
    reqs = [Requirement(r) for r in requirements]

    reporter = BaseReporter()
    provider = Provider()
    resolver = Resolver(provider, reporter)

    state = resolver.resolve(reqs)
    target_path = Path("__pypackages__") / PYTHON_VERSION[:3] / "lib"
    print("resolution result:")
    for k, c in state.mapping.items():
        print(c.name, c.version)

    for c in state.mapping.values():
        c.install(target_path)


if __name__ == "__main__":
    main(sys.argv[1:])
