from setuptools import setup

setup(
    name="hdns_cli",
    description="Hetzner DNS CLI Tool",
    author="Maximilian Thoma",
    author_email="dev@lanbugs.de",
    url="https://github.com/lanbugs/hdns_cli/",
    version="1.0.0",
    scripts=["hdns_cli.py"],
    install_requires=['loguru', 'fire', 'tabulate', 'requests', 'pyyaml'],
    license="GNU General Public License v3.0",
    entry_points=dict(console_scripts=['hdns=hdns_cli:main'])
)

