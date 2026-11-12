"""Legibilidad de los estados de selección del acabado EVA-01."""
import configparser
from pathlib import Path
import unittest


class FinishContrastTests(unittest.TestCase):
    def test_selected_semantic_text_is_readable(self):
        palette = configparser.ConfigParser()
        palette.read(Path(__file__).resolve().parents[1] / 'assets/acabado/EVA01Finish.colors')
        selection = palette['Colors:Selection']
        def luminance(value):
            channels = [int(part) / 255 for part in value.split(',')]
            linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
            return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
        for background in ('BackgroundNormal', 'BackgroundAlternate'):
            for key, value in selection.items():
                if key.startswith('foreground'):
                    with self.subTest(background=background, foreground=key):
                        levels = sorted((luminance(selection[background]), luminance(value)))
                        self.assertGreaterEqual((levels[1] + 0.05) / (levels[0] + 0.05), 4.5)
