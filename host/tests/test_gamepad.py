import unittest

from gamepad import (
    BUTTONS, Controller, build_report, normalize, packet, pack_stick,
)


class TestButtons(unittest.TestCase):
    def report(self, *names):
        return build_report(set(names))

    def test_action_buttons(self):
        self.assertEqual(self.report("A")[0] & 0x08, 0x08)
        self.assertEqual(self.report("B")[0] & 0x04, 0x04)
        self.assertEqual(self.report("X")[0] & 0x02, 0x02)
        self.assertEqual(self.report("Y")[0] & 0x01, 0x01)
        self.assertEqual(self.report("ZR")[0] & 0x80, 0x80)
        self.assertEqual(self.report("R")[0] & 0x40, 0x40)

    def test_menu_buttons(self):
        self.assertEqual(self.report("PLUS")[1] & 0x02, 0x02)
        self.assertEqual(self.report("MINUS")[1] & 0x01, 0x01)
        self.assertEqual(self.report("HOME")[1] & 0x10, 0x10)
        self.assertEqual(self.report("CAPTURE")[1] & 0x20, 0x20)
        self.assertEqual(self.report("THUMB_L")[1] & 0x08, 0x08)
        self.assertEqual(self.report("THUMB_R")[1] & 0x04, 0x04)

    def test_dpad_and_shoulders(self):
        self.assertEqual(self.report("DOWN")[2] & 0x01, 0x01)
        self.assertEqual(self.report("UP")[2] & 0x02, 0x02)
        self.assertEqual(self.report("RIGHT")[2] & 0x04, 0x04)
        self.assertEqual(self.report("LEFT")[2] & 0x08, 0x08)
        self.assertEqual(self.report("L")[2] & 0x40, 0x40)
        self.assertEqual(self.report("ZL")[2] & 0x80, 0x80)

    def test_combo(self):
        r = self.report("A", "B")
        self.assertEqual(r[0] & 0x0C, 0x0C)

    def test_unknown(self):
        with self.assertRaises(ValueError):
            self.report("NOPE")

    def test_base_bits(self):
        r = self.report()
        self.assertEqual(r[1] & 0x80, 0x80)  # chargingGrip
        self.assertEqual(r[2] & 0x30, 0x30)  # LeftSL / LeftSR


class TestStick(unittest.TestCase):
    def test_center(self):
        self.assertEqual(pack_stick(2048, 2048), bytes([0x00, 0x08, 0x80]))

    def test_min(self):
        self.assertEqual(pack_stick(0, 0), bytes([0x00, 0x00, 0x00]))

    def test_max(self):
        self.assertEqual(pack_stick(4095, 4095), bytes([0xFF, 0xFF, 0xFF]))

    def test_clamp(self):
        self.assertEqual(pack_stick(-10, 9999), bytes([0x00, 0xF0, 0xFF]))


class TestPacket(unittest.TestCase):
    def test_length_and_header(self):
        p = packet(build_report({"A"}))
        self.assertEqual(len(p), 49)
        self.assertEqual(p[:3], b"\xAA\x55\x00")
        chk = 0
        for b in p[2:-1]:
            chk ^= b
        self.assertEqual(chk, p[-1])

    def test_report_len(self):
        self.assertEqual(len(build_report(set())), 45)


class TestNormalize(unittest.TestCase):
    def test_string(self):
        self.assertEqual(normalize("a, b"), ["A", "B"])

    def test_list(self):
        self.assertEqual(normalize(["zr", "A"]), ["ZR", "A"])


class TestControllerState(unittest.TestCase):
    class Link:
        def __init__(self):
            self.sent = []

        def send(self, data):
            self.sent.append(data)

        def close(self):
            pass

    def test_press_release(self):
        link = self.Link()
        c = Controller(link)
        c.press("A")
        self.assertIn("A", c.pressed)
        c.release("A")
        self.assertNotIn("A", c.pressed)
        self.assertEqual(len(link.sent), 2)

    def test_reset(self):
        link = self.Link()
        c = Controller(link)
        c.press("ZR")
        c.stick(left=(0, 0))
        c.reset()
        self.assertEqual(c.left, (2048, 2048))
        self.assertFalse(c.pressed)


if __name__ == "__main__":
    unittest.main()
