# apacheserverstatus
Scrapes Apache's optional `/server-status` endpoint to retrieve information in a more automation-friendly format.

## Requirements
* requests~=2.31.0
* beautifulsoup4~=4.12.2
* python-dateutil~=2.8.2

## Server-Side Config
You'll probably want something like this in `httpd.conf`:

```
<VirtualHost *:8008>
    <Location /server-status>
        SetHandler server-status
        Order deny,allow
        Deny from all
        Allow from localhost 10.1.1.1 10.1.1.2
    </Location>
</VirtualHost>
```

## Example
An example invocation is in `try.py` in this repository. It's pretty self-explanatory.

## Sample Result
Results are structured into a nested dict that looks something like this:

```
{'cpu_usage': 'u380.14 s46.79 cu4.5 cs2.39 - .0834% CPU load',
 'current_time_epoch': 1687819891,
 'current_time_raw': 'Monday, 26-Jun-2023 17:51:31 CDT',
 'current_time_utc': '2023-06-26T22:51:31+00:00',
 'parent_server_config_generation': '1',
 'parent_server_mpm_generation': '0',
 'restart_time_epoch': 1687819891,
 'restart_time_raw': 'Tuesday, 20-Jun-2023 17:17:08 CDT',
 'restart_time_utc': '2023-06-20T22:17:08+00:00',
 'server_built_epoch': 1687819891,
 'server_built_raw': 'Oct 29 2021 12:32:51',
 'server_built_utc': '2021-10-29T12:32:51+00:00',
 'server_load': {'L1': '0.11', 'L15': '0.44', 'L5': '0.28'},
 'server_mpm': 'prefork',
 'server_uptime': '6 days 34 minutes 23 seconds',
 'server_version': 'Apache/2.4.6 (Red Hat Enterprise Linux) '
                   'OpenSSL/1.0.2k-fips mod_fcgid/2.3.9',
 'total_accesses': '1077632',
 'total_traffic': '24.4 GB',
 'worker_slots': [{'acc': '0/40/85251',
                   'child': '0.67',
                   'client': '10.1.1.1',
                   'conn': '0.0',
                   'cpu': '6.15',
                   'm': '_',
                   'mode': 'waiting',
                   'pid': '19163',
                   'req': '15',
                   'request': 'GET /robots.txt HTTP/1.1',
                   'slot': '1939.56',
                   'srv': '0-0',
                   'ss': '11',
                   'vhost': 'somebox.somewhere.edu:80'},
                  {'acc': '0/36/84856',
                   'child': '0.50',
                   'client': '10.1.1.2',
                   'conn': '0.0',
                   'cpu': '3.97',
                   'm': '_',
                   'mode': 'waiting',
                   'pid': '19175',
                   'req': '13',
                   'request': 'GET /test.php HTTP/1.1',
                   'slot': '1907.96',
                   'srv': '1-0',
                   'ss': '2',
                   'vhost': 'somebox.somewhere.edu:8080'},
                   [ ... etc ... ]

```

## Challenges and Hacks
* Apache sends us the current time and last server restart time in a strange format, in the server's local time zone,
with a time zone abbreviation that Python can't figure out. Fortunately, RFC 2616 comes to our rescue by requiring the
`Date` header in nearly all HTTP responses and requiring that it be expressed in UTC. We can compare this to what the
server sends for "Current Time" to derive a UTC offset without having to decipher the time zone.
