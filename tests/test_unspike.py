import unittest
import sys
import os
from shapely.geometry import Polygon, MultiPolygon

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unspike import calculate_angle, filter_polygon, filter_vertices

class TestUnspike(unittest.TestCase):

    def test_calculate_angle(self):
        p0 = (0, 0)
        p1 = (1, 1)
        p2 = (2, 0)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 90, places=5)

        # collinear points
        p0 = (0, 0)
        p1 = (1, 1)
        p2 = (2, 2)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 180, places=5)

        # very close points
        p0 = (0, 0)
        p1 = (1e-11, 1e-11)
        p2 = (2e-11, 0)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 180, places=5)

    def test_filter_polygon(self):
        # square with a spike
        poly = Polygon([(0, 0), (0, 1), (0.5, 1), (0.6, 10), (0.7, 1), (1, 1), (1, 0), (0, 0)])
        filtered_poly, spikes_removed = filter_polygon(poly, "dymmy_id", 15, False)

        self.assertEqual(spikes_removed, 1)
        self.assertEqual(len(filtered_poly.exterior.coords), 7)
        self.assertTrue(filtered_poly.is_valid)

        # Test with a polygon that shouldn't be changed
        square = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
        filtered_square, spikes_removed = filter_polygon(square, "dymmy_id", 15, False)

        self.assertEqual(spikes_removed, 0)
        self.assertEqual(len(filtered_square.exterior.coords), 5)  # 4 corners + closing point
        self.assertTrue(filtered_square.equals(square))

    def test_filter_vertices(self):
        # Test with a MultiPolygon
        poly1 = Polygon([(0, 0), (0, 1), (0.5, 1), (0.6, 10), (0.7, 1), (1, 1), (1, 0), (0, 0)])
        poly2 = Polygon([(2, 2), (2, 3), (3, 3), (3, 2), (2, 2)])
        multi_poly = MultiPolygon([poly1, poly2])

        filtered_multi_poly, total_spikes_removed = filter_vertices(multi_poly, "dummy_id", 15, False)

        self.assertEqual(total_spikes_removed, 1)
        self.assertIsInstance(filtered_multi_poly, MultiPolygon)
        self.assertEqual(len(filtered_multi_poly.geoms), 2)
        self.assertEqual(len(filtered_multi_poly.geoms[0].exterior.coords), 7)  # 4 corners + closing point
        self.assertEqual(len(filtered_multi_poly.geoms[1].exterior.coords), 5)  # 4 corners + closing point

        # Test with a single Polygon
        single_poly = Polygon([(0, 0), (0, 1), (0.5, 1), (0.6, 10), (0.7, 1), (1, 1), (1, 0), (0, 0)])
        filtered_single_poly, spikes_removed = filter_vertices(single_poly, "dummy_id", 15, False)

        self.assertEqual(spikes_removed, 1)
        self.assertIsInstance(filtered_single_poly, Polygon)
        self.assertEqual(len(filtered_single_poly.exterior.coords), 7)  # 4 corners + closing point

if __name__ == '__main__':
    unittest.main()