from tests.base import Base


class SystemRoutesTest(Base):
    def test_health_identifies_cashflowpot_api(self):
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {
            'status': 'ok',
            'service': 'CashflowPot API',
        })

    def test_legacy_api_welcome_route_is_not_registered(self):
        response = self.client.get('/api')

        self.assertEqual(response.status_code, 404)
