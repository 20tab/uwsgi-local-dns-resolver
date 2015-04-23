# uWSGI-local-DNS-resolver
uWSGI-local-DNS-resolver (from now on __uWSGI-DNS__) is a DNS server that resolves to `localhost` each request directed to a uWSGI-subscribed domain.

# Why?
Our main intent is to let users transparently connect to their local development instances handled through a uWSGI HTTP subscription server.

## Project status
uWSGI-DNS is still a work in progress. As a consequence, its APIs could be subject to changes.

## Features
- Python 2 & Python 3 compatibility.
- UNIX/Linux systems compatibility.
- Automatic domain refresh on new uWSGI subscriptions.

## Installation
Until uWSGI-DNS lands on PyPi you can install it as follows:
```bash
$ git clone https://github.com/20tab/uwsgi-local-dns-resolver.git
$ cd uwsgi-local-dns-resolver
$ python setup.py develop  # better use a virtualenv here
$ # uwsgi-http-stats-uri is of the form host:port
$ sudo uwsgi-dns uwsgi-http-stats-uri # we need sudo to bind on reserved port 53
```

Once started, you should have a DNS server running on `localhost:53`.
Pressing `CTRL-C` will let uWSGI-DNS reload the list of domains that must be resolved on your machine.

## Configuration
```bash
$ uwsgi-dns -h
    usage: uwsgi-dns [-h] [-l {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}] [-p]
                    [-u upstream DNS server URI]
                    uwsgi-http-stats-uri

    DNS server that resolves to localhost uWSGI's HTTP subscripted domains.

    positional arguments:
    uwsgi-http-stats-uri  the URI (remote:port) to the uWSGI HTTP subscription
                            stats server

    optional arguments:
    -h, --help            show this help message and exit
    -l {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}, --logging {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}
                            set the logging level
    -p, --proxy           proxy other requests to upstream DNS server
                            (--upstream)
    -u upstream DNS server URI, --upstream upstream DNS server URI
                            the URI to the upstream DNS server (with --proxy),
                            defaults to 8.8.8.8:53
```

### Non-local requests
uWSGI-DNS can act as a DNS proxy (`-p`), forwarding each non-local request to the upstream server specified with the `-u` flag;
otherwise, it simply drops such requests and let the OS fallback DNS server handle them.

## OS integration
TODO: better OS integration.

The OS integration largely varies with each platforms.
We provide here just a few examples, adapt them to your needs.

### OS X integration
On Apple's OS X you can edit your connection parameters and set a [custom DNS server](https://support.apple.com/kb/PH14159) pointing to `127.0.0.1`.
Make sure that this server is the first of the list.
If you want, you can specify other fallback servers (your network gateway could be a good candidate).

_Bonus_: before editing your network settings, you can create a new [Network Location](https://support.apple.com/en-us/HT202480) to be specifically used while developing and edit its DNS settings.

## Tests
TODO: add tests.
