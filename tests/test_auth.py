import asyncio
import unittest

from telethon.errors import SessionPasswordNeededError

from saveit.auth import authorize_with_qr


class FakeQrLogin:
    def __init__(self, client, url, outcome):
        self.client = client
        self.url = url
        self.outcome = outcome

    async def wait(self):
        if self.outcome == "timeout":
            raise asyncio.TimeoutError
        if self.outcome == "2fa":
            raise SessionPasswordNeededError(request=None)
        self.client.authorized = True


class FakeClient:
    def __init__(self, outcomes):
        self.authorized = False
        self.outcomes = list(outcomes)
        self.qr_requests = 0
        self.passwords = []

    async def is_user_authorized(self):
        return self.authorized

    async def qr_login(self):
        self.qr_requests += 1
        outcome = self.outcomes.pop(0)
        if outcome == "2fa-on-create":
            raise SessionPasswordNeededError(request=None)
        return FakeQrLogin(
            self,
            f"tg://login?token=token-{self.qr_requests}",
            outcome,
        )

    async def sign_in(self, *, password):
        self.passwords.append(password)
        self.authorized = True


class QrAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorizes_after_scanning_displayed_qr(self):
        client = FakeClient(["success"])
        rendered_urls = []

        await authorize_with_qr(client, qr_renderer=rendered_urls.append)

        self.assertTrue(client.authorized)
        self.assertEqual(rendered_urls, ["tg://login?token=token-1"])

    async def test_replaces_expired_qr_until_scan_succeeds(self):
        client = FakeClient(["timeout", "success"])
        rendered_urls = []

        await authorize_with_qr(client, qr_renderer=rendered_urls.append)

        self.assertTrue(client.authorized)
        self.assertEqual(client.qr_requests, 2)
        self.assertEqual(
            rendered_urls,
            ["tg://login?token=token-1", "tg://login?token=token-2"],
        )

    async def test_finishes_qr_login_with_two_factor_password(self):
        client = FakeClient(["2fa"])

        await authorize_with_qr(
            client,
            qr_renderer=lambda url: None,
            password_callback=lambda prompt: "cloud-password",
        )

        self.assertTrue(client.authorized)
        self.assertEqual(client.passwords, ["cloud-password"])

    async def test_finishes_login_when_qr_creation_requests_two_factor_password(self):
        client = FakeClient(["2fa-on-create"])

        await authorize_with_qr(
            client,
            qr_renderer=lambda url: None,
            password_callback=lambda prompt: "cloud-password",
        )

        self.assertTrue(client.authorized)
        self.assertEqual(client.passwords, ["cloud-password"])


if __name__ == "__main__":
    unittest.main()
