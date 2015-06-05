"""Setup configuration file."""

from setuptools import setup


def readme():
    """Open the readme."""
    with open('README.md') as f:
        return f.read()

setup(
    name='uwsgidns',
    version='1.0.1',
    description='Dinamically route to localhost request for uWSGI locally subscribed domains.',
    long_description=readme(),
    url='https://github.com/20tab/uwsgi-local-dns-resolver',

    author='Adriano Di Luzio',
    author_email='adrianodl@hotmail.it',

    packages=['uwsgidns'],
    install_requires=[
        'dnslib',
    ],

    # test_suite='nose.collector',
    # tests_require=['nose'],

    scripts=['bin/uwsgidns'],

    keywords=["uwsgi", "dns", "uwsgidns", "localhost"],
    license='MIT',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 6 - Mature",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Topic :: System :: Operating System",
        "Topic :: Internet :: Name Service (DNS)",
        "Topic :: Utilities"
    ],

    zip_safe=False,
    include_package_data=True,
)
