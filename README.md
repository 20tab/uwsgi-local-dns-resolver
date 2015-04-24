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
$ python setup.py install  # you could need sudo here
```

And if you want, you can test the server with:
```bash
$ # uwsgi-http-stats-uri is of the form host:port
$ sudo uwsgidns uwsgi-http-stats-uri # we need sudo to bind on reserved port 53
```

Once started, you should have a DNS server running on `localhost:53`.
Pressing `CTRL-C` will let uWSGI-DNS reload the list of domains that must be resolved on your machine.

Note: installing uWSGI-DNS inside a virtualenv is obviously possible, but you should use particular care while integrating it into uWSGI configuration files.

## Configuration
```bash
$ uwsgidns -h
usage: uwsgidns [-h] [-l {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}] [-p]
                [-u upstream DNS server URI] [-s uwsgi-HTTP-stats-URI]

DNS server that resolves to localhost uWSGI HTTP subscripted domains.

optional arguments:
  -h, --help            show this help message and exit
  -l {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}, --logging {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}
                        set the logging level
  -p, --proxy           proxy other requests to upstream DNS server
                        (--upstream)
  -u upstream DNS server URI, --upstream upstream DNS server URI
                        the URI to the upstream DNS server (with --proxy),
                        defaults to 8.8.8.8:53
  -s uwsgi-HTTP-stats-URI, --stats uwsgi-HTTP-stats-URI
                        the URI (remote:port) to the uWSGI HTTP subscription
                        stats server
```

### Non-local requests
uWSGI-DNS can act as a DNS proxy (`-p`), forwarding each non-local request to the upstream server specified with the `-u` flag;
otherwise, it simply drops such requests and let the OS fallback DNS server handle them.

## uWSGI integration
The integration with uWSGI is simple and straightforward.
We assume you use the uWSGI http subscription server.
To integrate uWSGI-DNS you can edit your emperor/subscription server as follows:

```ini
; uWSGI subscription server - ini configuration file
http = :80
http-subscription-server = 127.0.0.1:2626
http-stats-server = 127.0.0.1:5004

; resubscribe let uWSGI-DNS know about new HTTP nodes
http-resubscribe = 127.0.0.1:9696

; launch the uWSGI-DNS with the HTTP subscription server
; you can tweak the command line arguments and the path here
attach-daemon = uwsgidns
```
Anytime you'll launch the subscription system, the uWSGI-DNS server will launch whit it.

## OS integration
TODO: other OSs integration.

The OS integration largely varies with each platforms.
We provide here just a few examples, adapt them to your needs.

### OS X integration
You can use LaunchD to automatically launch a uWSGI emperor instance on startup.
To do so, create the file `it.unbit.uwsgi.emperor.plist` in the `/Library/LaunchDaemons/` directory and make sure it has the following content:
```plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
        <key>RunAtLoad</key>
        <true/>
        <key>Disabled</key>
        <false/>
        <key>KeepAlive</key>
    	<dict>
         	<key>SuccessfulExit</key>
         	<false/>
   	 </dict>
        <key>Label</key>
        <string>it.unbit.uwsgi.emperor</string>
        <key>ProgramArguments</key>
        <array>
                <string>/usr/local/bin/uwsgi</string>
                <string>--master</string>
                <string>--die-on-term</string>
                <string>--plugin</string>
                <string>syslog</string>
                <string>--logger</string>
                <string>syslog:</string>
                <string>--emperor</string>
                <string>/Users/*/*/vassals/*.ini</string>
                <string>--emperor</string>
                <string>/Users/*/vassals/*.ini</string>
                <string>--emperor-tyrant</string>
                <string>--http</string>
                <string>:80</string>
                <string>--http-subscription-server</string>
                <string>127.0.0.1:5005</string>
                <string>--http-resubscribe</string>
                <string>127.0.0.1:9696</string>
                <string>--http-stats-server</string>
                <string>127.0.0.1:5004</string>
                <string>--emperor-stats-server</string>
                <string>127.0.0.1:5000</string>
                <string>--attach-daemon</string>
                <string>/usr/local/bin/uwsgidns</string>
        </array>
</dict>
</plist>
```
Create the vassals ini in your home folder and then start the uWSGI emperor with the command:
```bash
$ sudo launchctl load /Library/LaunchDaemons/it.unbit.uwsgi.emperor.plist
```

You can finally edit your connection parameters and set a [custom DNS server](https://support.apple.com/kb/PH14159) pointing to `127.0.0.1`.
Make sure that this server is the first of the list and if you don't use uWSGI-DNS as a proxy make sure to specify other fallback servers (your network gateway could be a good candidate).

_Bonus_: before editing your network settings, you can create a new [Network Location](https://support.apple.com/en-us/HT202480) to be specifically used while developing and edit its DNS settings.

## Tests
TODO: add tests.
