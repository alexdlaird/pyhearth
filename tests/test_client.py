__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import json

from pyhearth.client import DEFAULT_RETRY_AFTER, PROTOCOL, HearthClient
from pyhearth.exception import (
    HearthAuthError,
    HearthConnectionError,
    HearthDemoHomeError,
    HearthRateLimitedError,
    HearthRejectedError,
)
from tests.testcase import HearthTestCase

THERMOSTAT = {"entity_id": "climate.hallway", "hvac_mode": "heat", "current_temperature": 20.5}
DESIRED = {"hvac_mode": "heat", "temperature": 21.0}
READINGS = [{"id": "sensor.office", "temperature": 20.8}, {"id": "sensor.den", "temperature": 19.9}]


class TestCheckKey(HearthTestCase):
    async def test_check_key(self) -> None:
        # GIVEN
        client = self.given_client(source="home-assistant")

        # WHEN
        await client.check_key()

        # THEN
        self.assertEqual([{"source": "home-assistant", "sensors": []}], self.posted("readings"))
        self.assertEqual([f"Bearer {self.API_KEY}"], self.authorizations)

    async def test_check_key_refused(self) -> None:
        # GIVEN
        self.given_hearth_answers("readings", 401)
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthAuthError):
            await client.check_key()


class TestSyncThermostat(HearthTestCase):
    async def test_sync_thermostat_desired(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 200, json.dumps({"desired": DESIRED}))
        client = self.given_client()

        # WHEN
        desired = await client.sync_thermostat(THERMOSTAT)

        # THEN
        self.assertEqual(DESIRED, desired)
        self.assertEqual([{"protocol": PROTOCOL, "thermostat": THERMOSTAT}], self.posted("bridge"))

    async def test_sync_thermostat_refused_setting(self) -> None:
        # GIVEN
        refused = {"setting": DESIRED, "reason": "out of range", "by": "thermostat"}
        client = self.given_client()

        # WHEN
        await client.sync_thermostat(THERMOSTAT, refused)

        # THEN
        self.assertEqual(refused, self.posted("bridge")[0]["refused"])

    async def test_sync_thermostat_nothing_desired(self) -> None:
        # GIVEN
        client = self.given_client()

        # WHEN
        desired = await client.sync_thermostat(THERMOSTAT)

        # THEN
        self.assertIsNone(desired)

    async def test_sync_thermostat_desired_not_a_setting(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 200, json.dumps({"desired": "heat"}))
        client = self.given_client()

        # WHEN
        desired = await client.sync_thermostat(THERMOSTAT)

        # THEN
        self.assertIsNone(desired)

    async def test_sync_thermostat_unreadable_answer(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 200, "not json")
        client = self.given_client()

        # WHEN
        desired = await client.sync_thermostat(THERMOSTAT)

        # THEN
        self.assertIsNone(desired)


class TestPostReadings(HearthTestCase):
    async def test_post_readings(self) -> None:
        # GIVEN
        self.given_hearth_answers("readings", 200, json.dumps({"not_added": ["sensor.den"]}))
        client = self.given_client(source="home-assistant", source_name="Home Assistant")

        # WHEN
        result = await client.post_readings(READINGS)

        # THEN
        self.assertEqual(["sensor.den"], result.not_added)
        self.assertEqual([{"source": "home-assistant", "name": "Home Assistant", "sensors": READINGS}],
                         self.posted("readings"))

    async def test_post_readings_default_source(self) -> None:
        # GIVEN
        client = self.given_client()

        # WHEN
        result = await client.post_readings(READINGS)

        # THEN
        self.assertEqual([], result.not_added)
        self.assertEqual([{"sensors": READINGS}], self.posted("readings"), "Hearth's own default source applies")

    async def test_post_readings_none_added(self) -> None:
        # GIVEN
        self.given_hearth_answers("readings", 422, json.dumps({"error": "no sensor of this home"}))
        client = self.given_client()

        # WHEN
        result = await client.post_readings(READINGS)

        # THEN
        self.assertEqual(["sensor.office", "sensor.den"], result.not_added)


class TestErrors(HearthTestCase):
    async def test_demo_home(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 403, "This is a demo home.")
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthDemoHomeError) as raised:
            await client.sync_thermostat(THERMOSTAT)
        self.assertEqual("This is a demo home.", str(raised.exception))

    async def test_rate_limited(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 429, headers={"Retry-After": "30"})
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthRateLimitedError) as raised:
            await client.sync_thermostat(THERMOSTAT)
        self.assertEqual({"retry_after": 30}, raised.exception.meta)

    async def test_rate_limited_without_retry_after(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 429)
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthRateLimitedError) as raised:
            await client.sync_thermostat(THERMOSTAT)
        self.assertEqual({"retry_after": DEFAULT_RETRY_AFTER}, raised.exception.meta)

    async def test_rate_limited_unreadable_retry_after(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 429, headers={"Retry-After": "soon"})
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthRateLimitedError) as raised:
            await client.sync_thermostat(THERMOSTAT)
        self.assertEqual({"retry_after": DEFAULT_RETRY_AFTER}, raised.exception.meta)

    async def test_rejected(self) -> None:
        # GIVEN
        self.given_hearth_answers("readings", 400, "sensors must be a list")
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthRejectedError) as raised:
            await client.post_readings(READINGS)
        self.assertEqual("sensors must be a list", str(raised.exception))

    async def test_rejected_without_reason(self) -> None:
        # GIVEN
        self.given_hearth_answers("readings", 413)
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthRejectedError) as raised:
            await client.post_readings(READINGS)
        self.assertEqual("Hearth answered 413.", str(raised.exception))

    async def test_server_error(self) -> None:
        # GIVEN
        self.given_hearth_answers("bridge", 503)
        client = self.given_client()

        # WHEN / THEN
        with self.assertRaises(HearthConnectionError):
            await client.sync_thermostat(THERMOSTAT)

    async def test_unreachable(self) -> None:
        # GIVEN
        url = str(self.server.make_url("/"))
        await self.server.close()
        client = HearthClient(self.session, self.API_KEY, url)

        # WHEN / THEN
        with self.assertRaises(HearthConnectionError):
            await client.check_key()

    async def test_base_url_trailing_slash(self) -> None:
        # GIVEN
        client = HearthClient(self.session, self.API_KEY, f"{self.server.make_url('/')}/")

        # WHEN
        await client.check_key()

        # THEN
        self.assertEqual(str(self.server.make_url("")).rstrip("/"), client.base_url)
        self.assertEqual(1, len(self.posted("readings")))
