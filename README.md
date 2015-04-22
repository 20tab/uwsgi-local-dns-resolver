# uwsgi-local-dns-resolver
uwsgi-local-dns-resolver (from now on __uwsgidns__) is a DNS server.
It resolves to `localhost` each request directed to a uWSGI-subscribed domain and proxies to an upstream DNS server all the others.
uwsgidns' main intent is to let users transparently connect to development remotes while forwarding all other requests to a specified upstream server.

## Project status
uwsgidns is still a work in progress. As a consequence, its APIs could be subject to changes.

## Features
- Python 2 & Python 3 compatibility.
- UNIX/Linux systems compatibility.
- Automatic domain refresh on new uWSGI subscriptions.

## Installation
Until uwsgidns will land on PyPi, you can install it as follows:
```bash
$ git clone https://github.com/20tab/uwsgi-local-dns-resolver.git
$ cd uwsgi-local-dns-resolver
$ python setup.py develop  # better use a virtualenv here
$ sudo uwsgidns  # we need sudo to bind on reserved port 53
```
From now on, you'll have a DNS server running on `localhost:53`.

Until this project will reach a stable status, pressing `CTRL-C` will let uwsgidns reload the list of domains to be resolved on localhost 
(_atm_ we assume your uwsgi susbscription server stats to run on `localhost:5004`).

## Configuration
TODO: add configuration command-line/file parameters.

## OS integration
TODO: better OS integration.
The OS integration largely varies with each platforms.

We'll provide here only a few examples, adapt them to your needs.
### OS X integration
On Apple's OS X you can edit your connection parameters and set a [custom DNS server](https://support.apple.com/kb/PH14159) pointing to `127.0.0.1`.
Make sure that this server is the first of the list.
If you want, you can specify other fallback servers (your network gateway could be a good candidate).

_Bonus_: before editing your network settings, you can create a new [Network Location](https://support.apple.com/en-us/HT202480) to be specifically used while developing and edit its DNS settings.

## Tests
TODO: add tests.
