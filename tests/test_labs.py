from __future__ import annotations

import socket
import threading
import unittest

from poi.errors import POIError
from poi.runtime.electronics import electronics
from poi.runtime import make_globals
from poi.runtime.security_lab import security
from poi.safemode import harden_globals


class ElectronicsTests(unittest.TestCase):
    def test_mock_board_and_conversions(self):
        board = electronics.mock({0: 512})
        self.assertEqual(board.analog_read(0), 512)
        self.assertAlmostEqual(electronics.voltage(512), 2.5024, places=3)
        self.assertEqual(electronics.adc(2.5), 512)
        self.assertEqual(electronics.ohm(voltage=5, resistance=1000), 0.005)
        self.assertAlmostEqual(electronics.parallel([100, 100]), 50)
        board.digital_write(13, True)
        board.pwm_write(9, 300)
        self.assertTrue(board.digital[13])
        self.assertEqual(board.pwm[9], 255)

    def test_sampling(self):
        board = electronics.mock({1: 42})
        self.assertEqual(electronics.sample(board, 1, 3, 0), [42, 42, 42])


class SecurityLabTests(unittest.TestCase):
    def test_offline_tools(self):
        self.assertEqual(len(security.sha256("poi")), 64)
        self.assertTrue(security.constant_equal("same", "same"))
        self.assertFalse(security.constant_equal("same", "other"))
        self.assertGreater(security.entropy("abcdef012345"), 3)
        self.assertTrue(security.password_report("LongExample!42").strong)
        self.assertLess(security.analyze_headers({}).score, 50)

    def test_loopback_scan(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        thread = threading.Thread(target=lambda: server.accept()[0].close(), daemon=True)
        thread.start()
        try:
            result = security.scan_ports("127.0.0.1", [port], timeout=0.5)
            self.assertEqual(result.open, [port])
        finally:
            server.close()

    def test_limits(self):
        with self.assertRaises(POIError):
            security.scan_ports("127.0.0.1", list(range(1, 258)))

    def test_public_target_is_blocked_by_default(self):
        with self.assertRaises(POIError):
            security.port_open("8.8.8.8", 53)

    def test_safe_mode_blocks_device_and_network_modules(self):
        globals_ = harden_globals(make_globals())
        with self.assertRaises(POIError):
            globals_["electronics"].ports()
        with self.assertRaises(POIError):
            globals_["security"].scan_ports("127.0.0.1", [80])


if __name__ == "__main__":
    unittest.main()
