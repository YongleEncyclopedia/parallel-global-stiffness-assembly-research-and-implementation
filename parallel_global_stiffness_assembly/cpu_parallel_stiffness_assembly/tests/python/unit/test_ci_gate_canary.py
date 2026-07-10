import unittest


class CiGateCanaryTests(unittest.TestCase):
    def test_required_checks_block_merge(self) -> None:
        self.fail("Intentional CI gate canary failure; never merge this commit")


if __name__ == "__main__":
    unittest.main()
