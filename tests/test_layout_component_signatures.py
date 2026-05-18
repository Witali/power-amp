import unittest

from scripts import layout_component_signatures


@unittest.skipUnless(layout_component_signatures.OPENCV_AVAILABLE, "OpenCV dependencies are not installed")
class LayoutComponentSignaturesTests(unittest.TestCase):
    def test_detects_common_schematic_component_signatures(self) -> None:
        cv2 = layout_component_signatures.cv2
        np = layout_component_signatures.np

        mask = np.zeros((180, 260), dtype=np.uint8)
        cv2.rectangle(mask, (20, 30), (76, 48), 255, 2)
        cv2.line(mask, (112, 28), (112, 62), 255, 2)
        cv2.line(mask, (126, 28), (126, 62), 255, 2)
        triangle = np.array([[160, 35], [160, 70], [194, 52]], dtype=np.int32)
        cv2.polylines(mask, [triangle], True, 255, 2)
        cv2.line(mask, (198, 35), (198, 70), 255, 2)
        cv2.circle(mask, (220, 112), 24, 255, 2)
        edges = cv2.Canny(mask, 50, 150)

        features = layout_component_signatures.component_signature_features(mask, edges)

        self.assertGreater(features["component_signature_score"], 0.20)
        self.assertGreater(features["resistor_symbol_density"], 0.0)
        self.assertGreater(features["capacitor_symbol_density"], 0.0)
        self.assertGreater(features["diode_symbol_density"], 0.0)
        self.assertGreater(features["transistor_symbol_density"], 0.0)

    def test_waveform_diagram_has_low_component_signature(self) -> None:
        cv2 = layout_component_signatures.cv2
        np = layout_component_signatures.np

        mask = np.zeros((180, 260), dtype=np.uint8)
        for y in (40, 80, 120):
            points = np.array([[20, y], [60, y], [60, y - 18], [105, y - 18], [105, y], [160, y]], dtype=np.int32)
            cv2.polylines(mask, [points], False, 255, 2)
        edges = cv2.Canny(mask, 50, 150)

        features = layout_component_signatures.component_signature_features(mask, edges)

        self.assertLess(features["component_signature_score"], 0.20)


if __name__ == "__main__":
    unittest.main()
