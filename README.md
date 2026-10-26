[![Version](https://img.shields.io/pypi/v/pyhearth)](https://pypi.org/project/pyhearth)
[![Python Versions](https://img.shields.io/pypi/pyversions/pyhearth.svg)](https://pypi.org/project/pyhearth)
[![Coverage](https://img.shields.io/codecov/c/github/alexdlaird/pyhearth)](https://codecov.io/gh/alexdlaird/pyhearth)
[![Build](https://img.shields.io/github/actions/workflow/status/alexdlaird/pyhearth/build.yml)](https://github.com/alexdlaird/pyhearth/actions/workflows/build.yml)
[![GitHub License](https://img.shields.io/github/license/alexdlaird/pyhearth)](https://github.com/alexdlaird/pyhearth/blob/main/LICENSE)

`pyhearth` is a Python client for [Hearth](https://www.meethearth.app)'s home API. It posts room sensor readings, and
optionally a thermostat, to a Hearth home with the home's API key, and returns the thermostat setting Hearth answers
with. It's what [`ha-hearth`](https://github.com/alexdlaird/ha-hearth), Hearth's Home Assistant integration, uses to
talk to Hearth.

## Installation

`pyhearth` is available on [PyPI](https://pypi.org/project/pyhearth/) and can be installed using `pip`:

```sh
pip install pyhearth
```

## Basic Usage

In the Hearth app, create the home's API key in Settings, then Manage home, then Sensors, then "Other sensors (Hearth
API)". Then post readings:

```python
import asyncio

import aiohttp

from pyhearth.client import HearthClient


async def main():
    async with aiohttp.ClientSession() as session:
        client = HearthClient(session, "<your API key>", source="my-hub", source_name="My hub")
        result = await client.post_readings([
            {"id": "office", "name": "Office", "temperature": 20.8, "humidity": 41}
        ])
        print(result.not_added)


asyncio.run(main())
```

A sensor's readings are kept once it's added to a room in the Hearth app; until then, it's listed in `not_added`. The
fields each endpoint takes are in [Hearth's API docs](https://www.meethearth.app/support.html#hearth-api).

Errors are raised as subclasses of `HearthError` (in `pyhearth.exception`): `HearthAuthError` when Hearth doesn't take
the key, `HearthRateLimitedError` when it asks for fewer posts (`meta["retry_after"]` says how many seconds to wait),
`HearthRejectedError` when it can't read a post, and `HearthConnectionError` when it can't be reached.

## Contributing

If you would like to get involved, be sure to review
the [Contribution Guide](https://github.com/alexdlaird/pyhearth/blob/main/CONTRIBUTING.rst).

Want to contribute financially? If you've found `pyhearth` useful, [sponsorship](https://github.com/sponsors/alexdlaird)
would also be greatly appreciated!
