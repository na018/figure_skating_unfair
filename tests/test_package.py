import unittest

import figure_skating_bias


class PackageTests(unittest.TestCase):
    def test_package_has_version(self) -> None:
        self.assertEqual(figure_skating_bias.__version__, "0.1.0")
