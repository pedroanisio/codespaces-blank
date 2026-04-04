import unittest

import cv2
import numpy as np

from lib.extract import find_centered_square_crop


class ExtractCropTests(unittest.TestCase):
    def test_centered_square_crop_keeps_main_figure_and_excludes_edge_notes(self) -> None:
        binary = np.zeros((120, 120), dtype=np.uint8)

        cv2.rectangle(binary, (42, 20), (78, 92), 255, 2)
        cv2.rectangle(binary, (4, 6), (20, 16), 255, 2)
        cv2.rectangle(binary, (95, 10), (116, 22), 255, 2)

        (x_left, y_top, side, centerline_in_crop), crop = find_centered_square_crop(binary)

        self.assertGreater(x_left, 4)
        self.assertLess(x_left + side, 116)
        self.assertGreaterEqual(centerline_in_crop, 0)
        self.assertLessEqual(centerline_in_crop, side)

        self.assertEqual(crop.shape, (side, side))
        self.assertGreater(crop[:, centerline_in_crop].sum(), 0)

        left_note_x = 8 - x_left
        right_note_x = 100 - x_left
        if 0 <= left_note_x < side:
            self.assertEqual(int(crop[10 - y_top, left_note_x]), 0)
        if 0 <= right_note_x < side:
            self.assertEqual(int(crop[14 - y_top, right_note_x]), 0)

    def test_centered_square_crop_prefers_top_middle_closed_shape(self) -> None:
        binary = np.zeros((160, 120), dtype=np.uint8)

        cv2.rectangle(binary, (46, 12), (74, 48), 255, 2)
        cv2.rectangle(binary, (30, 70), (90, 145), 255, 2)

        (_, y_top, side, centerline_in_crop), crop = find_centered_square_crop(binary)

        self.assertLessEqual(y_top, 12)
        self.assertGreater(crop[:, centerline_in_crop].sum(), 0)
        lower_shape_y = 80 - y_top
        if 0 <= lower_shape_y < side:
            self.assertEqual(int(crop[lower_shape_y, 32]), 0)


if __name__ == "__main__":
    unittest.main()
